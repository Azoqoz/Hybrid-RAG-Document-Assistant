import os
import unittest
from unittest.mock import patch

import numpy as np

from src.services import (
    Citation,
    CorpusNotFoundError,
    DocumentIngestionService,
    InMemoryCorpusStore,
    QueryService,
    RetrievalResult,
    RetrievalService,
    SharedModelRegistry,
    UnsupportedFileTypeError,
    UploadPayload,
)


class StubEmbeddingModel:
    def __init__(self):
        self.document_encode_calls = 0
        self.query_encode_calls = 0

    def get_sentence_embedding_dimension(self):
        return 3

    def encode(self, texts, convert_to_numpy=True, show_progress_bar=False):
        if len(texts) > 1:
            self.document_encode_calls += 1
        else:
            self.query_encode_calls += 1

        vectors = []
        for text in texts:
            words = text.lower().split()
            vectors.append(
                [
                    words.count("alpha") + words.count("retrieval"),
                    words.count("beta") + words.count("keyword"),
                    1.0,
                ]
            )
        return np.asarray(vectors, dtype="float32")


class StubRerankerModel:
    def __init__(self):
        self.predict_calls = 0

    def predict(self, pairs):
        self.predict_calls += 1
        return np.asarray(
            [
                float(
                    len(
                        set(query.lower().split())
                        & set(text.lower().split())
                    )
                )
                for query, text in pairs
            ],
            dtype="float32",
        )


class Phase2ServiceTests(unittest.TestCase):
    def make_service(self):
        embedding_model = StubEmbeddingModel()
        reranker_model = StubRerankerModel()
        load_counts = {"embedding": 0, "reranker": 0}

        def load_embedding_model():
            load_counts["embedding"] += 1
            return embedding_model

        def load_reranker_model():
            load_counts["reranker"] += 1
            return reranker_model

        registry = SharedModelRegistry(
            embedding_loader=load_embedding_model,
            reranker_loader=load_reranker_model,
        )
        store = InMemoryCorpusStore(id_factory=lambda: "corpus-test-id")
        retrieval = RetrievalService(model_registry=registry)
        service = QueryService(corpus_store=store, retrieval_service=retrieval)
        return service, embedding_model, reranker_model, load_counts

    def ingest_small_corpus(self, service):
        corpus_id = service.create_corpus()
        service.ingest_documents(
            corpus_id,
            [
                UploadPayload(
                    filename="alpha.txt",
                    content=b"alpha retrieval semantic document",
                ),
                UploadPayload(
                    filename="beta.txt",
                    content=b"beta keyword matching document",
                ),
                UploadPayload(
                    filename="combined.txt",
                    content=b"alpha beta combined retrieval keyword",
                ),
            ],
        )
        return corpus_id

    def test_corpus_creation_returns_an_empty_workspace_id(self):
        service, _, _, load_counts = self.make_service()

        corpus_id = service.create_corpus()
        corpus = service.corpus_store.get(corpus_id)

        self.assertEqual(corpus_id, "corpus-test-id")
        self.assertEqual(corpus.documents, [])
        self.assertEqual(corpus.chunks, [])
        self.assertFalse(corpus.is_indexed)
        self.assertEqual(load_counts, {"embedding": 0, "reranker": 0})

    def test_ingestion_keeps_metadata_chunks_and_builds_indexes(self):
        service, embedding_model, _, load_counts = self.make_service()
        corpus_id = service.create_corpus()
        words = " ".join(f"word{index}" for index in range(210))

        batch = service.ingest_documents(
            corpus_id,
            [UploadPayload(filename="notes.TXT", content=words.encode("utf-8"))],
        )
        corpus = service.corpus_store.get(corpus_id)

        self.assertEqual(batch.documents[0].filename, "notes.TXT")
        self.assertEqual(batch.documents[0].file_type, ".txt")
        self.assertEqual(batch.documents[0].chunk_count, 3)
        self.assertEqual([chunk.chunk_id for chunk in corpus.chunks], [1, 2, 3])
        self.assertEqual({chunk.source for chunk in corpus.chunks}, {"notes.TXT"})
        self.assertTrue(corpus.is_indexed)
        self.assertEqual(corpus.index_build_count, 1)
        self.assertEqual(embedding_model.document_encode_calls, 1)
        self.assertEqual(load_counts["embedding"], 1)
        self.assertEqual(load_counts["reranker"], 0)

    def test_ingestion_rejects_unsupported_file_types(self):
        ingestion = DocumentIngestionService()

        with self.assertRaises(UnsupportedFileTypeError):
            ingestion.ingest(
                [UploadPayload(filename="archive.zip", content=b"not supported")]
            )

    def test_indexes_and_shared_models_are_reused_across_questions(self):
        service, embedding_model, reranker_model, load_counts = self.make_service()
        corpus_id = self.ingest_small_corpus(service)
        corpus = service.corpus_store.get(corpus_id)
        searcher_identity = id(corpus.hybrid_searcher)

        service.query(corpus_id, "alpha retrieval", provider="none")
        service.query(corpus_id, "beta keyword", provider="none")

        self.assertEqual(corpus.index_build_count, 1)
        self.assertEqual(id(corpus.hybrid_searcher), searcher_identity)
        self.assertEqual(load_counts, {"embedding": 1, "reranker": 1})
        self.assertEqual(embedding_model.document_encode_calls, 1)
        self.assertEqual(embedding_model.query_encode_calls, 2)
        self.assertEqual(reranker_model.predict_calls, 2)

    def test_query_returns_structured_retrieval_results(self):
        service, _, _, _ = self.make_service()
        corpus_id = self.ingest_small_corpus(service)

        response = service.query(corpus_id, "alpha retrieval", provider="none")

        self.assertFalse(response.is_summary)
        self.assertTrue(response.retrieval_results)
        result = response.retrieval_results[0]
        self.assertIsInstance(result, RetrievalResult)
        self.assertIn(result.filename, {"alpha.txt", "beta.txt", "combined.txt"})
        self.assertIsInstance(result.chunk_id, int)
        self.assertTrue(result.text)
        self.assertIsNotNone(result.semantic_score)
        self.assertIsNotNone(result.keyword_score)
        self.assertIsNotNone(result.hybrid_score)
        self.assertIsNotNone(result.rerank_score)

    def test_query_returns_structured_citations_without_parsing_answer_text(self):
        service, _, _, _ = self.make_service()
        corpus_id = self.ingest_small_corpus(service)

        response = service.query(corpus_id, "alpha retrieval", provider="none")

        self.assertTrue(response.citations)
        citation = response.citations[0]
        self.assertIsInstance(citation, Citation)
        self.assertTrue(citation.filename.endswith(".txt"))
        self.assertIsInstance(citation.chunk_id, int)
        self.assertTrue(citation.text_snippet)
        self.assertIsNotNone(citation.hybrid_score)
        self.assertIsNotNone(citation.rerank_score)
        self.assertNotIn("Sources used:", response.answer)

    def test_summary_query_bypasses_retrieval_and_preserves_full_document_route(self):
        service, _, _, load_counts = self.make_service()
        corpus_id = self.ingest_small_corpus(service)

        response = service.query(
            corpus_id,
            "Please summarize this document",
            provider="none",
        )

        self.assertTrue(response.is_summary)
        self.assertEqual(len(response.retrieval_results), 3)
        self.assertTrue(all(result.hybrid_score is None for result in response.retrieval_results))
        self.assertIn("This document appears to be", response.answer)
        self.assertNotIn("Sources used:", response.answer)
        self.assertEqual(load_counts["reranker"], 0)

    def test_provider_without_api_key_preserves_retrieval_fallback(self):
        with (
            patch("src.generator.load_dotenv"),
            patch.dict(os.environ, {}, clear=True),
        ):
            service, _, _, _ = self.make_service()
            corpus_id = self.ingest_small_corpus(service)
            response = service.query(
                corpus_id,
                "alpha retrieval",
                provider="openai",
            )

        self.assertTrue(response.answer.startswith("No API key found"))
        self.assertIn("alpha", response.answer.lower())
        self.assertNotIn("Sources used:", response.answer)

    def test_corpus_reset_and_delete_have_explicit_lifecycle_behavior(self):
        service, _, _, _ = self.make_service()
        corpus_id = self.ingest_small_corpus(service)

        service.reset_corpus(corpus_id)
        reset_corpus = service.corpus_store.get(corpus_id)

        self.assertEqual(reset_corpus.documents, [])
        self.assertEqual(reset_corpus.chunks, [])
        self.assertFalse(reset_corpus.is_indexed)
        self.assertEqual(reset_corpus.index_build_count, 0)
        self.assertTrue(service.delete_corpus(corpus_id))
        self.assertFalse(service.delete_corpus(corpus_id))
        with self.assertRaises(CorpusNotFoundError):
            service.corpus_store.get(corpus_id)


if __name__ == "__main__":
    unittest.main()
