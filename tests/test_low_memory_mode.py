import json
import os
import subprocess
import sys
import unittest
import weakref
from pathlib import Path
from unittest.mock import patch

import numpy as np
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.services import (
    InMemoryCorpusStore,
    QueryService,
    RetrievalService,
    SharedModelRegistry,
    UploadPayload,
)


class DeterministicEmbeddingModel:
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


class DeterministicRerankerModel:
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


class ModelLifecycleTracker:
    def __init__(self):
        self.embedding_references = []
        self.reranker_references = []
        self.events = []

    def load_embedding(self):
        self._assert_released(self.reranker_references, "reranker")
        model = DeterministicEmbeddingModel()
        self.embedding_references.append(weakref.ref(model))
        self.events.append("load_embedding")
        return model

    def load_reranker(self):
        self._assert_released(self.embedding_references, "embedding")
        model = DeterministicRerankerModel()
        self.reranker_references.append(weakref.ref(model))
        self.events.append("load_reranker")
        return model

    @staticmethod
    def _assert_released(references, model_name):
        if any(reference() is not None for reference in references):
            raise AssertionError(f"{model_name} model is still resident")

    def all_models_released(self):
        references = self.embedding_references + self.reranker_references
        return all(reference() is None for reference in references)


class LowMemoryModeTests(unittest.TestCase):
    def make_service(self, registry, corpus_id="low-memory-corpus"):
        return QueryService(
            corpus_store=InMemoryCorpusStore(id_factory=lambda: corpus_id),
            retrieval_service=RetrievalService(model_registry=registry),
        )

    def ingest_corpus(self, service):
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

    def test_importing_default_fastapi_app_does_not_import_heavy_ml_libraries(self):
        project_root = Path(__file__).resolve().parents[1]
        script = (
            "import json, sys; "
            "import src.api.app; "
            "print(json.dumps({name: name in sys.modules for name in "
            "['sentence_transformers', 'transformers', 'torch']}))"
        )

        completed = subprocess.run(
            [sys.executable, "-c", script],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=True,
        )

        self.assertEqual(
            json.loads(completed.stdout.strip()),
            {
                "sentence_transformers": False,
                "transformers": False,
                "torch": False,
            },
        )

    def test_health_does_not_load_embedding_or_reranker_models(self):
        load_counts = {"embedding": 0, "reranker": 0}

        def load_embedding():
            load_counts["embedding"] += 1
            return DeterministicEmbeddingModel()

        def load_reranker():
            load_counts["reranker"] += 1
            return DeterministicRerankerModel()

        registry = SharedModelRegistry(
            embedding_loader=load_embedding,
            reranker_loader=load_reranker,
            low_memory_mode=True,
        )
        client = TestClient(create_app(self.make_service(registry)))

        response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        self.assertEqual(load_counts, {"embedding": 0, "reranker": 0})

    def test_low_memory_mode_releases_models_between_ingestion_and_query(self):
        tracker = ModelLifecycleTracker()
        with patch.dict(os.environ, {"LOW_MEMORY_MODE": "true"}):
            registry = SharedModelRegistry(
                embedding_loader=tracker.load_embedding,
                reranker_loader=tracker.load_reranker,
            )
        service = self.make_service(registry)

        corpus_id = self.ingest_corpus(service)
        corpus = service.corpus_store.get(corpus_id)

        self.assertTrue(registry.low_memory_mode)
        self.assertIsNone(corpus.hybrid_searcher.semantic_searcher.model)
        self.assertTrue(tracker.all_models_released())

        response = service.query(corpus_id, "alpha retrieval", provider="none")

        self.assertEqual(response.corpus_id, corpus_id)
        self.assertEqual(response.query, "alpha retrieval")
        self.assertEqual(response.provider, "none")
        self.assertTrue(response.answer)
        self.assertTrue(response.claims)
        self.assertTrue(response.retrieval_results)
        self.assertTrue(response.citations)
        self.assertIsNotNone(response.retrieval_results[0].semantic_score)
        self.assertIsNotNone(response.retrieval_results[0].keyword_score)
        self.assertIsNotNone(response.retrieval_results[0].hybrid_score)
        self.assertIsNotNone(response.retrieval_results[0].rerank_score)
        self.assertEqual(
            tracker.events,
            ["load_embedding", "load_embedding", "load_reranker"],
        )
        self.assertTrue(tracker.all_models_released())

    def test_low_memory_mode_preserves_the_api_query_contract(self):
        registry = SharedModelRegistry(
            embedding_loader=DeterministicEmbeddingModel,
            reranker_loader=DeterministicRerankerModel,
            low_memory_mode=True,
        )
        service = self.make_service(registry, corpus_id="api-low-memory-corpus")
        client = TestClient(create_app(service))
        corpus_id = client.post("/corpora").json()["corpus_id"]
        upload = client.post(
            f"/corpora/{corpus_id}/documents",
            files={
                "files": (
                    "alpha.txt",
                    b"Alpha retrieval explains semantic document search.",
                    "text/plain",
                )
            },
        )

        response = client.post(
            f"/corpora/{corpus_id}/query",
            json={"query": "alpha retrieval", "provider": "none"},
        )
        body = response.json()

        self.assertEqual(upload.status_code, 200)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(body),
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
        self.assertTrue(body["claims"])
        self.assertTrue(body["citations"])
        self.assertEqual(
            body["claims"][0]["citation_ids"][0],
            body["citations"][0]["citation_id"],
        )

    def test_normal_mode_remains_shared_and_is_the_default(self):
        load_counts = {"embedding": 0, "reranker": 0}

        def load_embedding():
            load_counts["embedding"] += 1
            return DeterministicEmbeddingModel()

        def load_reranker():
            load_counts["reranker"] += 1
            return DeterministicRerankerModel()

        with patch.dict(os.environ, {}, clear=True):
            registry = SharedModelRegistry(
                embedding_loader=load_embedding,
                reranker_loader=load_reranker,
            )
        service = self.make_service(registry, corpus_id="normal-mode-corpus")
        corpus_id = self.ingest_corpus(service)

        service.query(corpus_id, "alpha retrieval", provider="none")
        service.query(corpus_id, "beta keyword", provider="none")

        self.assertFalse(registry.low_memory_mode)
        self.assertEqual(load_counts, {"embedding": 1, "reranker": 1})
        self.assertIsNotNone(registry._embedding_model)
        self.assertIsNotNone(registry._reranker_model)


if __name__ == "__main__":
    unittest.main()
