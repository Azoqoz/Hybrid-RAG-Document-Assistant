import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.api.app import create_app
from src.chunking import DocumentChunk
from src.generator import AnswerGenerator
from src.services import (
    Citation,
    ClaimMapper,
    InMemoryCorpusStore,
    ProviderService,
    QueryService,
    RetrievalResult,
)


class StaticRetrievalService:
    def __init__(self, results):
        self.results = results

    def retrieve_and_rerank(self, corpus, query):
        return list(self.results)

    def build_indexes(self, corpus):
        corpus.index_build_count += 1


class Phase35ContractTests(unittest.TestCase):
    def setUp(self):
        self.results = [
            RetrievalResult(
                filename="semantic.txt",
                chunk_id=11,
                text=(
                    "Semantic retrieval matches meaning across paraphrases. "
                    "It broadens recall."
                ),
                semantic_score=1.0,
                keyword_score=0.2,
                hybrid_score=0.72,
                rerank_score=8.5,
            ),
            RetrievalResult(
                filename="keyword.txt",
                chunk_id=22,
                text="BM25 keyword search preserves exact technical terms.",
                semantic_score=0.3,
                keyword_score=1.0,
                hybrid_score=0.545,
                rerank_score=6.4,
            ),
            RetrievalResult(
                filename="reranking.txt",
                chunk_id=33,
                text="Cross encoder reranking reorders retrieved candidates.",
                semantic_score=0.5,
                keyword_score=0.4,
                hybrid_score=0.465,
                rerank_score=4.2,
            ),
        ]
        self.store = InMemoryCorpusStore(id_factory=lambda: "phase35-corpus")
        corpus = self.store.create()
        corpus.chunks = [
            DocumentChunk(
                chunk_id=result.chunk_id,
                source=result.filename,
                text=result.text,
            )
            for result in self.results
        ]
        self.provider = ProviderService()
        self.service = QueryService(
            corpus_store=self.store,
            retrieval_service=StaticRetrievalService(self.results),
            provider_service=self.provider,
        )
        self.client = TestClient(create_app(self.service))

    def query_api(self, query, provider="none"):
        return self.client.post(
            "/corpora/phase35-corpus/query",
            json={"query": query, "provider": provider},
        )

    def test_claims_schema_and_stable_claim_ids(self):
        first = self.query_api(
            "How does semantic retrieval match meaning across paraphrases?"
        ).json()
        second = self.query_api(
            "How does semantic retrieval match meaning across paraphrases?"
        ).json()

        self.assertTrue(first["claims"])
        self.assertEqual(
            [claim["claim_id"] for claim in first["claims"]],
            [claim["claim_id"] for claim in second["claims"]],
        )
        self.assertEqual(first["claims"][0]["claim_id"], "claim-001")
        self.assertEqual(
            set(first["claims"][0]),
            {"claim_id", "text", "citation_ids", "support_status"},
        )

    def test_claim_mapping_uses_only_returned_citation_ids(self):
        citations = [
            Citation(
                citation_id="citation-000011",
                filename="semantic.txt",
                chunk_id=11,
                snippet="Semantic retrieval matches meaning across paraphrases.",
            ),
            Citation(
                citation_id="citation-000022",
                filename="keyword.txt",
                chunk_id=22,
                snippet="BM25 keyword search preserves exact technical terms.",
            ),
        ]
        claims = ClaimMapper().build(
            (
                "Semantic retrieval matches meaning across paraphrases. "
                "BM25 preserves exact keyword terms."
            ),
            citations,
            is_summary=False,
        )
        returned_ids = {citation.citation_id for citation in citations}

        self.assertEqual(claims[0].citation_ids, ["citation-000011"])
        self.assertEqual(claims[1].citation_ids, ["citation-000022"])
        self.assertTrue(
            all(set(claim.citation_ids) <= returned_ids for claim in claims)
        )

    def test_flat_answer_remains_backward_compatible(self):
        query = "How does semantic retrieval match meaning across paraphrases?"
        expected_answer = self.provider.generate("none", query, self.results)

        response = self.query_api(query).json()

        self.assertEqual(response["answer"], expected_answer)
        self.assertIsInstance(response["answer"], str)
        self.assertTrue(response["claims"])

    def test_retrieval_only_fallback_returns_mapped_claims(self):
        response = self.query_api(
            "How does semantic retrieval match meaning across paraphrases?"
        ).json()
        returned_citation_ids = {
            citation["citation_id"] for citation in response["citations"]
        }

        self.assertFalse(response["is_summary"])
        self.assertTrue(any(claim["citation_ids"] for claim in response["claims"]))
        self.assertTrue(
            all(
                set(claim["citation_ids"]) <= returned_citation_ids
                for claim in response["claims"]
            )
        )

    def test_provider_fallback_notice_is_preserved_but_not_made_a_claim(self):
        with (
            patch("src.generator.load_dotenv"),
            patch.dict(os.environ, {"OPENAI_API_KEY": ""}),
        ):
            response = self.query_api(
                "How does semantic retrieval match meaning across paraphrases?",
                provider="openai",
            ).json()

        self.assertTrue(response["answer"].startswith("No API key found"))
        self.assertTrue(response["claims"])
        self.assertNotIn(
            AnswerGenerator.MISSING_PROVIDER_KEY_NOTE,
            [claim["text"] for claim in response["claims"]],
        )

    def test_summary_response_uses_one_safe_full_answer_claim(self):
        response = self.query_api("Please summarize this document").json()

        self.assertTrue(response["is_summary"])
        self.assertEqual(len(response["claims"]), 1)
        self.assertEqual(response["claims"][0]["claim_id"], "claim-001")
        self.assertEqual(response["claims"][0]["text"], response["answer"])
        self.assertEqual(
            response["claims"][0]["citation_ids"],
            [citation["citation_id"] for citation in response["citations"]],
        )
        self.assertEqual(
            response["claims"][0]["support_status"],
            "summary_context",
        )

    def test_citation_contract_includes_scores_position_and_no_fake_locations(self):
        response = self.query_api(
            "How does semantic retrieval match meaning across paraphrases?"
        ).json()
        citation = response["citations"][0]

        self.assertEqual(citation["citation_id"], "citation-000011")
        self.assertEqual(citation["filename"], "semantic.txt")
        self.assertEqual(citation["chunk_id"], 11)
        self.assertEqual(citation["snippet"], citation["text_snippet"])
        self.assertEqual(citation["semantic_score"], 1.0)
        self.assertEqual(citation["keyword_score"], 0.2)
        self.assertEqual(citation["hybrid_score"], 0.72)
        self.assertEqual(citation["rerank_score"], 8.5)
        self.assertEqual(citation["rerank_position"], 1)
        self.assertIsNone(citation["page_number"])
        self.assertIsNone(citation["slide_number"])


if __name__ == "__main__":
    unittest.main()
