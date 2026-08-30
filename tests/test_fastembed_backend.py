import builtins
import os
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

import numpy as np
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.chunking import DocumentChunk
from src.reranker import CrossEncoderReranker
from src.services import (
    CorpusRecord,
    InMemoryCorpusStore,
    QueryService,
    RetrievalService,
    SharedModelRegistry,
)


class FastEmbedBackendTests(unittest.TestCase):
    @contextmanager
    def fake_fastembed(self):
        calls = {
            "embedding_model_names": [],
            "reranker_model_names": [],
        }

        class FakeTextEmbedding:
            def __init__(self, model_name):
                calls["embedding_model_names"].append(model_name)

            def embed(self, texts):
                for text in texts:
                    words = text.lower().split()
                    vector = np.zeros(384, dtype="float32")
                    vector[0] = words.count("alpha") + words.count("retrieval")
                    vector[1] = words.count("beta") + words.count("keyword")
                    vector[2] = 1.0
                    yield vector

        class FakeTextCrossEncoder:
            def __init__(self, model_name):
                calls["reranker_model_names"].append(model_name)

            def rerank_pairs(self, pairs):
                for query, text in pairs:
                    yield float(
                        len(
                            set(query.lower().split())
                            & set(text.lower().split())
                        )
                    )

        fastembed_module = ModuleType("fastembed")
        fastembed_module.__path__ = []
        fastembed_module.TextEmbedding = FakeTextEmbedding
        rerank_module = ModuleType("fastembed.rerank")
        rerank_module.__path__ = []
        cross_encoder_module = ModuleType("fastembed.rerank.cross_encoder")
        cross_encoder_module.TextCrossEncoder = FakeTextCrossEncoder

        with patch.dict(
            sys.modules,
            {
                "fastembed": fastembed_module,
                "fastembed.rerank": rerank_module,
                "fastembed.rerank.cross_encoder": cross_encoder_module,
            },
        ):
            yield calls

    def make_registry(self, low_memory_mode=True):
        return SharedModelRegistry(
            low_memory_mode=low_memory_mode,
            inference_backend="fastembed",
        )

    def test_sentence_transformers_backend_remains_the_default(self):
        with patch.dict(os.environ, {}, clear=True):
            registry = SharedModelRegistry(
                embedding_loader=lambda: object(),
                reranker_loader=lambda: object(),
            )

        self.assertEqual(
            registry.inference_backend,
            SharedModelRegistry.SENTENCE_TRANSFORMERS_BACKEND,
        )
        self.assertEqual(
            SharedModelRegistry.EMBEDDING_MODEL,
            "sentence-transformers/all-MiniLM-L6-v2",
        )
        self.assertEqual(
            SharedModelRegistry.RERANKER_MODEL,
            "cross-encoder/ms-marco-MiniLM-L-6-v2",
        )

    def test_fastembed_loaders_do_not_import_pytorch_transformer_libraries(self):
        original_import = builtins.__import__
        forbidden_imports = {"sentence_transformers", "torch", "transformers"}

        def guarded_import(name, *args, **kwargs):
            if name.split(".", 1)[0] in forbidden_imports:
                raise AssertionError(f"Unexpected heavy import: {name}")
            return original_import(name, *args, **kwargs)

        with self.fake_fastembed() as calls, patch(
            "builtins.__import__",
            side_effect=guarded_import,
        ):
            registry = self.make_registry()
            with registry.use_embedding_model() as embedding_model:
                embeddings = embedding_model.encode(["alpha document"])
                del embedding_model
            with registry.use_reranker_model() as reranker_model:
                scores = reranker_model.predict([("alpha", "alpha document")])
                del reranker_model

        self.assertEqual(embeddings.shape, (1, 384))
        self.assertEqual(scores.tolist(), [1.0])
        self.assertEqual(
            calls["embedding_model_names"],
            ["sentence-transformers/all-MiniLM-L6-v2"],
        )
        self.assertEqual(
            calls["reranker_model_names"],
            ["Xenova/ms-marco-MiniLM-L-6-v2"],
        )

    def test_fastembed_embeddings_build_and_query_the_faiss_index(self):
        chunks = [
            DocumentChunk(1, "alpha.txt", "alpha retrieval semantic document"),
            DocumentChunk(2, "beta.txt", "beta keyword matching document"),
        ]
        corpus = CorpusRecord(corpus_id="faiss-fastembed", chunks=chunks)

        with self.fake_fastembed():
            retrieval = RetrievalService(model_registry=self.make_registry())
            retrieval.build_indexes(corpus)
            results = retrieval.semantic_search(corpus, "alpha retrieval", top_k=2)

        self.assertTrue(corpus.is_indexed)
        self.assertEqual(corpus.hybrid_searcher.semantic_searcher.index.d, 384)
        self.assertEqual(corpus.hybrid_searcher.semantic_searcher.index.ntotal, 2)
        self.assertEqual(results[0].filename, "alpha.txt")
        self.assertIsNotNone(results[0].semantic_score)

    def test_fastembed_reranking_preserves_the_existing_contract(self):
        input_results = [
            {
                "chunk_id": 1,
                "source": "alpha.txt",
                "text": "alpha retrieval semantic document",
                "hybrid_score": 0.8,
            },
            {
                "chunk_id": 2,
                "source": "beta.txt",
                "text": "beta keyword document",
                "hybrid_score": 0.7,
            },
            {
                "chunk_id": 3,
                "source": "mixed.txt",
                "text": "alpha beta retrieval keyword",
                "hybrid_score": 0.6,
            },
        ]

        with self.fake_fastembed():
            registry = self.make_registry()
            with registry.use_reranker_model() as model:
                reranker = CrossEncoderReranker(model=model)
                results = reranker.rerank(
                    "alpha retrieval",
                    input_results,
                    top_k=2,
                )
                del reranker, model

        self.assertEqual([result["chunk_id"] for result in results], [1, 3])
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["source"], "alpha.txt")
        self.assertEqual(results[0]["hybrid_score"], 0.8)
        self.assertEqual(results[0]["rerank_score"], 2.0)
        self.assertNotIn("rerank_score", input_results[0])

    def test_fastembed_health_is_lazy_and_query_schema_is_unchanged(self):
        original_import = builtins.__import__

        def reject_model_imports(name, *args, **kwargs):
            if name.split(".", 1)[0] in {
                "fastembed",
                "sentence_transformers",
                "torch",
                "transformers",
            }:
                raise AssertionError(f"Model import during health check: {name}")
            return original_import(name, *args, **kwargs)

        with patch.dict(
            os.environ,
            {
                "LOW_MEMORY_MODE": "true",
                "RAG_INFERENCE_BACKEND": "fastembed",
            },
        ), patch("builtins.__import__", side_effect=reject_model_imports):
            health_client = TestClient(create_app())
            health_response = health_client.get("/health")

        self.assertEqual(health_response.status_code, 200)
        self.assertEqual(health_response.json(), {"status": "ok"})

        with self.fake_fastembed():
            service = QueryService(
                corpus_store=InMemoryCorpusStore(
                    id_factory=lambda: "fastembed-api-corpus"
                ),
                retrieval_service=RetrievalService(
                    model_registry=self.make_registry()
                ),
            )
            client = TestClient(create_app(service))
            corpus_id = client.post("/corpora").json()["corpus_id"]
            upload_response = client.post(
                f"/corpora/{corpus_id}/documents",
                files={
                    "files": (
                        "alpha.txt",
                        b"alpha retrieval semantic document",
                        "text/plain",
                    )
                },
            )
            query_response = client.post(
                f"/corpora/{corpus_id}/query",
                json={"query": "alpha retrieval", "provider": "none"},
            )

        self.assertEqual(upload_response.status_code, 200)
        self.assertEqual(query_response.status_code, 200)
        self.assertEqual(
            set(query_response.json()),
            {
                "corpus_id",
                "query",
                "provider",
                "is_summary",
                "answer",
                "claims",
                "retrieval_results",
                "citations",
            },
        )
        self.assertTrue(query_response.json()["citations"])

    def test_render_requirements_exclude_pytorch_and_local_ui_dependencies(self):
        requirements_path = Path(__file__).resolve().parents[1] / "requirements-render.txt"
        requirements = requirements_path.read_text(encoding="utf-8").lower()

        self.assertIn("fastembed", requirements)
        self.assertIn("fastapi", requirements)
        self.assertIn("faiss-cpu", requirements)
        self.assertIn("rank-bm25", requirements)
        self.assertNotIn("sentence-transformers", requirements)
        self.assertNotIn("torch", requirements)
        self.assertNotIn("streamlit", requirements)


if __name__ == "__main__":
    unittest.main()
