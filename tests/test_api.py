import os
import unittest
from unittest.mock import patch

import numpy as np
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.services import (
    InMemoryCorpusStore,
    QueryService,
    RetrievalService,
    SharedModelRegistry,
)


class ApiEmbeddingModel:
    def encode(self, texts, convert_to_numpy=True, show_progress_bar=False):
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

    def get_sentence_embedding_dimension(self):
        return 3


class ApiRerankerModel:
    def predict(self, pairs):
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


class FastApiTests(unittest.TestCase):
    def setUp(self):
        registry = SharedModelRegistry(
            embedding_loader=ApiEmbeddingModel,
            reranker_loader=ApiRerankerModel,
        )
        retrieval = RetrievalService(model_registry=registry)
        corpus_store = InMemoryCorpusStore(id_factory=lambda: "api-corpus-id")
        self.service = QueryService(
            corpus_store=corpus_store,
            retrieval_service=retrieval,
        )
        self.client = TestClient(create_app(self.service))

    def create_corpus(self):
        response = self.client.post("/corpora")
        self.assertEqual(response.status_code, 201)
        return response.json()["corpus_id"]

    def upload_text_corpus(self):
        corpus_id = self.create_corpus()
        response = self.client.post(
            f"/corpora/{corpus_id}/documents",
            files=[
                ("files", ("alpha.txt", b"alpha retrieval semantic document", "text/plain")),
                ("files", ("beta.txt", b"beta keyword matching document", "text/plain")),
                (
                    "files",
                    (
                        "combined.txt",
                        b"alpha beta combined retrieval keyword",
                        "text/plain",
                    ),
                ),
            ],
        )
        self.assertEqual(response.status_code, 200)
        return corpus_id

    def test_health_endpoint_and_environment_cors(self):
        with patch.dict(
            os.environ,
            {
                "CORS_ALLOWED_ORIGINS": "https://frontend.example",
                "CORS_ALLOW_CREDENTIALS": "true",
            },
        ):
            client = TestClient(create_app(self.service))

        health = client.get("/health")
        preflight = client.options(
            "/health",
            headers={
                "Origin": "https://frontend.example",
                "Access-Control-Request-Method": "GET",
            },
        )

        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json(), {"status": "ok"})
        self.assertEqual(preflight.status_code, 200)
        self.assertEqual(
            preflight.headers["access-control-allow-origin"],
            "https://frontend.example",
        )
        self.assertEqual(
            preflight.headers["access-control-allow-credentials"],
            "true",
        )

    def test_create_and_get_corpus(self):
        corpus_id = self.create_corpus()

        response = self.client.get(f"/corpora/{corpus_id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "corpus_id": corpus_id,
                "document_count": 0,
                "chunk_count": 0,
                "indexed": False,
                "documents": [],
            },
        )

    def test_multipart_document_upload_returns_corpus_metadata(self):
        corpus_id = self.upload_text_corpus()

        response = self.client.get(f"/corpora/{corpus_id}")
        body = response.json()

        self.assertEqual(body["document_count"], 3)
        self.assertEqual(body["chunk_count"], 3)
        self.assertTrue(body["indexed"])
        self.assertEqual(
            [document["filename"] for document in body["documents"]],
            ["alpha.txt", "beta.txt", "combined.txt"],
        )
        self.assertTrue(all(document["file_type"] == ".txt" for document in body["documents"]))

    def test_upload_rejects_unsupported_extensions(self):
        corpus_id = self.create_corpus()

        response = self.client.post(
            f"/corpora/{corpus_id}/documents",
            files={"files": ("archive.zip", b"unsupported", "application/zip")},
        )

        self.assertEqual(response.status_code, 415)
        self.assertIn("Unsupported file type", response.json()["detail"])

    def test_normal_query_returns_structured_retrieval_and_citations(self):
        corpus_id = self.upload_text_corpus()

        response = self.client.post(
            f"/corpora/{corpus_id}/query",
            json={"query": "alpha retrieval", "provider": "none"},
        )
        body = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertFalse(body["is_summary"])
        self.assertEqual(body["provider"], "none")
        self.assertTrue(body["retrieval_results"])
        self.assertTrue(body["citations"])
        retrieval = body["retrieval_results"][0]
        citation = body["citations"][0]
        self.assertIn("filename", retrieval)
        self.assertIn("chunk_id", retrieval)
        self.assertIn("semantic_score", retrieval)
        self.assertIn("keyword_score", retrieval)
        self.assertIn("hybrid_score", retrieval)
        self.assertIn("rerank_score", retrieval)
        self.assertIn("text_snippet", citation)
        self.assertIn("rerank_score", citation)
        self.assertNotIn("Sources used:", body["answer"])

    def test_summary_query_preserves_summary_routing(self):
        corpus_id = self.upload_text_corpus()

        response = self.client.post(
            f"/corpora/{corpus_id}/query",
            json={"query": "Please summarize this document", "provider": "none"},
        )
        body = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(body["is_summary"])
        self.assertEqual(len(body["retrieval_results"]), 3)
        self.assertTrue(
            all(result["rerank_score"] is None for result in body["retrieval_results"])
        )
        self.assertIn("This document appears to be", body["answer"])

    def test_missing_provider_key_preserves_retrieval_fallback(self):
        corpus_id = self.upload_text_corpus()

        with (
            patch("src.generator.load_dotenv"),
            patch.dict(os.environ, {"OPENAI_API_KEY": ""}),
        ):
            response = self.client.post(
                f"/corpora/{corpus_id}/query",
                json={"query": "alpha retrieval", "provider": "openai"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["answer"].startswith("No API key found"))
        self.assertTrue(response.json()["citations"])

    def test_delete_corpus_and_missing_corpus_errors(self):
        corpus_id = self.create_corpus()

        deleted = self.client.delete(f"/corpora/{corpus_id}")
        missing_get = self.client.get(f"/corpora/{corpus_id}")
        missing_delete = self.client.delete(f"/corpora/{corpus_id}")

        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(deleted.content, b"")
        self.assertEqual(missing_get.status_code, 404)
        self.assertEqual(missing_delete.status_code, 404)
        self.assertIn("Corpus not found", missing_get.json()["detail"])


if __name__ == "__main__":
    unittest.main()
