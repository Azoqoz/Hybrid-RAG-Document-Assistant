import asyncio
import hashlib
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import numpy as np
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.demo_limits import DemoBodyLimitMiddleware
from src.services import QueryService, RetrievalService, SharedModelRegistry
from src.services.demo_policy import DemoPolicy, QUESTIONS, SAMPLE_FILENAME, SAMPLE_SHA256


class Embeddings:
    def encode(self, texts, **kwargs):
        return np.asarray([[text.lower().count("support"), text.lower().count("data"), 1] for text in texts], dtype="float32")

    def get_sentence_embedding_dimension(self):
        return 3


class Reranker:
    def predict(self, pairs):
        return np.asarray([len(set(query.lower().split()) & set(text.lower().split())) for query, text in pairs], dtype="float32")


class DemoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sample = (Path(__file__).resolve().parents[1] / "frontend/public/demo" / SAMPLE_FILENAME).read_bytes()

    def setUp(self):
        self.now = 100.0
        self.policy = DemoPolicy("demo", clock=lambda: self.now)
        self.service = QueryService(retrieval_service=RetrievalService(
            SharedModelRegistry(embedding_loader=Embeddings, reranker_loader=Reranker, low_memory_mode=False)
        ))
        self.client = TestClient(create_app(self.service, self.policy))
        self.headers = {"X-Demo-Session-ID": str(uuid4())}
        self.other = {"X-Demo-Session-ID": str(uuid4())}
        response = self.client.post("/corpora", headers=self.headers)
        self.assertEqual(response.status_code, 201)
        self.corpus_id = response.json()["corpus_id"]
        self.path = f"/corpora/{self.corpus_id}"

    def upload(self, content=None, filename=SAMPLE_FILENAME, headers=None):
        return self.client.post(self.path + "/documents", headers=headers or self.headers,
                                files={"files": (filename, self.sample if content is None else content, "application/pdf")})

    def query(self, body=None, headers=None):
        return self.client.post(self.path + "/query", headers=headers or self.headers,
                                json=body or {"question_id": "demo_support"})

    def test_capabilities_and_canonical_hash(self):
        data = self.client.get("/capabilities").json()
        self.assertTrue(data["demo_mode_available"])
        self.assertFalse(data["free_text_enabled"])
        self.assertEqual(data["provider"], "none")
        self.assertEqual(data["allowed_document_count"], 1)
        self.assertEqual(data["sample_download_path"], f"/demo/{SAMPLE_FILENAME}")
        self.assertEqual({q["id"]: q["question"] for q in data["guided_questions"]}, QUESTIONS)
        self.assertEqual(len(QUESTIONS), 5)
        self.assertEqual(hashlib.sha256(self.sample).hexdigest(), SAMPLE_SHA256)
        self.assertNotIn(str(Path.cwd()), str(data))

    def test_sample_runs_real_parsing_chunking_and_indexes(self):
        response = self.upload()
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()["indexed"])
        self.assertGreater(response.json()["chunk_count"], 0)
        corpus = self.service.corpus_store.get(self.corpus_id)
        self.assertEqual(corpus.index_build_count, 1)
        self.assertEqual(corpus.hybrid_searcher.semantic_searcher.index.ntotal, len(corpus.chunks))
        self.assertIsNotNone(corpus.hybrid_searcher.keyword_searcher.bm25)

    def test_different_pdf_rejected_before_ingestion(self):
        with patch.object(self.service, "ingest_documents") as ingest:
            self.assertEqual(self.upload(b"%PDF-1.7 different").status_code, 422)
            ingest.assert_not_called()

    def test_non_pdf_rejected_even_with_exact_bytes(self):
        self.assertEqual(self.upload(filename="sample.txt").status_code, 415)

    def test_second_document_and_multiple_uploads_rejected(self):
        files = [("files", (SAMPLE_FILENAME, self.sample, "application/pdf"))] * 2
        self.assertEqual(self.client.post(self.path + "/documents", headers=self.headers, files=files).status_code, 409)
        self.assertEqual(self.upload().status_code, 200)
        self.assertEqual(self.upload().status_code, 409)
        self.assertEqual(self.service.corpus_store.get(self.corpus_id).index_build_count, 1)

    def test_no_text_rolls_back_and_cannot_query(self):
        with patch("src.services.ingestion.load_pdf", return_value=""):
            self.assertEqual(self.upload().status_code, 422)
        corpus = self.client.get(self.path, headers=self.headers).json()
        self.assertFalse(corpus["indexed"])
        self.assertEqual(corpus["document_count"], 0)
        self.assertEqual(self.query().status_code, 409)

    def test_index_failure_rolls_back(self):
        with patch.object(self.service.retrieval_service, "build_indexes", side_effect=RuntimeError("index failed")):
            with self.assertRaises(RuntimeError):
                self.upload()
        corpus = self.service.corpus_store.get(self.corpus_id)
        self.assertFalse(corpus.is_indexed)
        self.assertFalse(corpus.documents)

    def test_all_guided_questions_use_real_services_without_summary_or_provider(self):
        self.upload()
        with patch.object(self.service.retrieval_service, "retrieve_and_rerank", wraps=self.service.retrieval_service.retrieve_and_rerank) as retrieve, patch("src.generator.AnswerGenerator._generate_provider_answer", side_effect=AssertionError("external provider invoked")):
            for key, question in QUESTIONS.items():
                with self.subTest(question_id=key):
                    response = self.query({"question_id": key})
                    self.assertEqual(response.status_code, 200, response.text)
                    data = response.json()
                    self.assertEqual(data["query"], question)
                    self.assertEqual(data["provider"], "none")
                    self.assertFalse(data["is_summary"])
                    self.assertTrue(data["answer"])
                    self.assertTrue(data["citations"])
                    self.assertTrue(all(r["rerank_score"] is not None for r in data["retrieval_results"]))
                    for citation in data["citations"]:
                        chunk = next(c for c in self.service.corpus_store.get(self.corpus_id).chunks if c.chunk_id == citation["chunk_id"])
                        for excerpt in citation["snippet"].split(" … "):
                            self.assertIn(excerpt.removesuffix("..."), " ".join(chunk.text.split()))
                        self.assertEqual(citation["filename"], SAMPLE_FILENAME)
                        self.assertIsNone(citation["page_number"])
            self.assertEqual(retrieve.call_count, 5)

    def test_free_text_unknown_id_and_provider_overrides_rejected(self):
        self.upload()
        invalid = [
            {"query": "anything"}, {"question_id": "unknown"},
            {"question_id": "demo_support", "query": "override"},
            {"question_id": "demo_support", "provider": "openai"},
            {"question_id": "demo_support", "provider": "anthropic"},
            {"question_id": "demo_support", "provider": "gemini"},
            {"question_id": "x" * 257},
        ]
        with patch.object(self.service, "query") as query:
            for body in invalid:
                self.assertEqual(self.query(body).status_code, 422, body)
            query.assert_not_called()

    def test_cross_session_read_query_upload_delete_rejected(self):
        self.assertEqual(self.client.get(self.path, headers=self.other).status_code, 404)
        self.assertEqual(self.query(headers=self.other).status_code, 404)
        self.assertEqual(self.upload(headers=self.other).status_code, 404)
        self.assertEqual(self.client.delete(self.path, headers=self.other).status_code, 404)
        self.assertTrue(self.service.corpus_store.exists(self.corpus_id))

    def test_session_uuid_required(self):
        for token in (None, "invalid", "00000000-0000-0000-0000-000000000000"):
            headers = {"X-Demo-Session-ID": token} if token else {}
            self.assertEqual(self.client.post("/corpora", headers=headers).status_code, 400)

    def test_one_corpus_and_owned_reset_preserves_quota(self):
        self.assertEqual(self.client.post("/corpora", headers=self.headers).json()["corpus_id"], self.corpus_id)
        self.upload()
        self.query()
        self.assertEqual(self.client.delete(self.path, headers=self.headers).status_code, 204)
        self.assertFalse(self.service.corpus_store.exists(self.corpus_id))
        replacement = self.client.post("/corpora", headers=self.headers).json()["corpus_id"]
        self.assertNotEqual(replacement, self.corpus_id)
        session = self.policy.sessions[self.headers["X-Demo-Session-ID"]]
        self.assertEqual(session.query_count, 1)
        self.assertEqual(session.upload_count, 1)

    def test_expiry_cleans_corpus_and_session(self):
        self.now += self.policy.RETENTION_SECONDS
        self.assertEqual(self.client.get(self.path, headers=self.headers).status_code, 404)
        self.assertFalse(self.service.corpus_store.exists(self.corpus_id))
        self.assertIsNone(self.policy.sessions[self.headers["X-Demo-Session-ID"]].corpus_id)

    def test_query_upload_and_capacity_limits(self):
        self.upload()
        session = self.policy.sessions[self.headers["X-Demo-Session-ID"]]
        session.query_count = self.policy.MAX_QUERIES
        self.assertEqual(self.query().status_code, 429)
        self.client.delete(self.path, headers=self.headers)
        self.corpus_id = self.client.post("/corpora", headers=self.headers).json()["corpus_id"]
        self.path = f"/corpora/{self.corpus_id}"
        session.upload_count = self.policy.MAX_UPLOADS
        self.assertEqual(self.upload().status_code, 429)
        self.policy.MAX_SESSIONS = 1
        self.assertEqual(self.client.post("/corpora", headers=self.other).status_code, 429)

    def test_oversized_upload_rejected_before_ingestion(self):
        with patch.object(self.service, "ingest_documents") as ingest:
            self.assertEqual(self.upload(b"x" * (self.policy.MAX_UPLOAD_BYTES + 1)).status_code, 413)
            self.assertEqual(self.upload(b"x" * (self.policy.MAX_REQUEST_BYTES + 1)).status_code, 413)
            ingest.assert_not_called()

    def test_chunked_body_limit_without_content_length(self):
        messages = iter([
            {"type": "http.request", "body": b"123", "more_body": True},
            {"type": "http.request", "body": b"456", "more_body": False},
        ])
        sent = []

        async def receive():
            return next(messages)

        async def send(message):
            sent.append(message)

        async def forbidden_app(*args):
            self.fail("Oversized body reached application")

        asyncio.run(DemoBodyLimitMiddleware(forbidden_app, 5)(
            {"type": "http", "method": "POST", "headers": []}, receive, send))
        self.assertEqual(sent[0]["status"], 413)

    def test_local_mode_keeps_arbitrary_upload_and_query(self):
        client = TestClient(create_app(self.service, DemoPolicy("local")))
        self.assertFalse(client.get("/capabilities").json()["demo_mode_available"])
        self.assertTrue(client.get("/capabilities").json()["free_text_enabled"])
        corpus_id = client.post("/corpora").json()["corpus_id"]
        path = f"/corpora/{corpus_id}"
        self.assertEqual(client.post(path + "/documents", files={"files": ("other.txt", b"support data retention", "text/plain")}).status_code, 200)
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}):
            response = client.post(path + "/query", json={"query": "What is data retention?", "provider": "openai"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["provider"], "openai")


if __name__ == "__main__":
    unittest.main()
