import unittest

from src.extractive import ExtractiveAssembler
from src.generator import AnswerGenerator
from src.services import InMemoryCorpusStore, QueryService, RetrievalResult


def passage(text, chunk_id=1, source="operations.txt"):
    return {"source": source, "chunk_id": chunk_id, "text": text}


class ExtractiveTests(unittest.TestCase):
    def setUp(self):
        self.assembler = ExtractiveAssembler()

    def test_exact_and_near_duplicates_removed(self):
        results = [passage("Backup records are retained for 45 days. Backup records are retained for 45 days."),
                   passage("The backup records are retained for 45 days.", 2)]
        selected = self.assembler.select("How long are backup records retained?", results)
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0].chunk_id, 1)

    def test_noise_and_flattened_headers_removed_conservatively(self):
        text = ("Operations Manual - Internal reference Page 4 SECTION 03 Backup policy and lifecycle "
                "Backup records are retained for 45 days. "
                "Retention reference Plan Normal retention Basic 45 days Premium 180 days "
                "Operations Manual - Internal reference Page 5 SECTION 04 Legal holds "
                "A legal hold suspends deletion until release.")
        selected = self.assembler.select("How long are backup records retained and how do legal holds affect deletion?", [passage(text)])
        answer = " ".join(s.text for s in selected)
        self.assertIn("Backup records are retained for 45 days.", answer)
        self.assertIn("A legal hold suspends deletion until release.", answer)
        for noise in ("Operations Manual", "Page", "SECTION", "Retention reference", "Backup policy", "Legal holds A"):
            self.assertNotIn(noise, answer)

    def test_incomplete_fragments_and_title_only_lines_rejected(self):
        text = ("records for deletion. Records and Operational Procedures. "
                "Backup records are retained for 45 days. The legal hold requires approval from the")
        selected = self.assembler.select("What are backup records and legal hold requirements?", [passage(text)])
        self.assertEqual([s.text for s in selected], ["Backup records are retained for 45 days."])

    def test_flattened_table_cannot_absorb_following_complete_sentence(self):
        table = ("Usage exclusions Health checks, invalid-key rejects, internal retries "
                 "Private installation All technical gates must be complete before launch "
                 "Operations checklist Pause change, preserve logs, notify "
                 "End of guide This document is a synthetic operations reference.")
        prose = "A private installation can launch only after security review and network validation are complete."
        selected = self.assembler.select("What must be complete before a private installation can launch?", [passage(prose), passage(table, 2)])
        self.assertEqual([s.text for s in selected], [prose])
        self.assertFalse(self.assembler._flattened_table("The engineers at Amazon Web Services and Microsoft Azure must approve access."))

    def test_pdf_wrapping_and_decimals_preserved(self):
        text = "The request limit is 2.5\nrequests per second. Additional requests are\nrejected until the next interval."
        candidates = self.assembler.candidates([passage(text)])
        self.assertEqual([s.text for s in candidates], [
            "The request limit is 2.5 requests per second.",
            "Additional requests are rejected until the next interval.",
        ])

    def test_prose_page_references_and_abbreviations_preserved(self):
        text = "Dr. Silva approves the release. See Page 4 for release instructions. Section 2 describes access controls."
        self.assertEqual([s.text for s in self.assembler.candidates([passage(text)])], [
            "Dr. Silva approves the release.",
            "See Page 4 for release instructions.",
            "Section 2 describes access controls.",
        ])

    def test_complete_long_list_not_cut_at_word_limit(self):
        sentence = ("Requests are excluded from billing when they are health checks sent to the monitoring endpoint; "
                    "when authentication rejects the supplied key before routing; and when the platform marks "
                    "an internal retry with its documented retry header.")
        selected = self.assembler.select("Which requests are excluded from billing?", [passage(sentence)])
        self.assertEqual(selected[0].text, sentence)
        self.assertGreater(len(sentence.split()), 32)

    def test_complementary_comparison_preserves_distinct_values_and_sources(self):
        rows = [passage("A legal hold suspends deletion for Basic and Premium records until release.", 8),
                passage("Basic plan records are retained for 45 days.", 2),
                passage("Premium plan records are retained for 180 days.", 3),
                passage("Basic plan support response is available within 20 minutes.", 9)]
        selected = self.assembler.select("What are the retention periods for Basic and Premium plans during a legal hold?", rows)
        self.assertEqual({s.chunk_id for s in selected}, {2, 3, 8})
        for s in selected:
            self.assertIn(s.text, next(r["text"] for r in rows if r["chunk_id"] == s.chunk_id))

    def test_different_entities_numbers_and_negations_not_deduplicated(self):
        pairs = [
            ("Basic plan records are retained for 45 days.", "Premium plan records are retained for 180 days."),
            ("Requests are counted toward the account usage limit.", "Requests are not counted toward the account usage limit."),
            ("Operators must follow the approved release procedure.", "Operators may follow the approved release procedure."),
            ("Orion records are retained in the approved storage system until review.", "Vega records are retained in the approved storage system until review."),
        ]
        for left, right in pairs:
            self.assertFalse(self.assembler._duplicate(left, right))

    def test_heading_cleanup_does_not_remove_conditions_or_proper_names(self):
        statements = [
            "If Orion fails, the operator must notify Support immediately.",
            "Northwind Cloud owns platform operations and service availability.",
            "Before a notification is sent, the owner must validate the impact.",
            "No records are deleted until Compliance approves the release.",
            "Basic and Premium records are retained until approval.",
            "Customers in Europe must approve the release.",
        ]
        for text in statements:
            self.assertEqual(self.assembler._strip_heading(text), text)

    def test_provenance_links_exact_supporting_chunk_including_later_results(self):
        results = [RetrievalResult(filename="guide.txt", chunk_id=i, text=text, rerank_score=6-i)
                   for i, text in enumerate([
                       "Internal Operations Reference.", "Customer Support Reference.", "Service Policy Reference.",
                       "The backup period is 45 days. Backup records are retained until the period expires.",
                       "A legal hold suspends deletion until the owner approves release.",
                   ], 1)]

        class Retrieval:
            def retrieve_and_rerank(self, corpus, query):
                return results

        store = InMemoryCorpusStore()
        corpus = store.create()
        service = QueryService(corpus_store=store, retrieval_service=Retrieval())
        response = service.query(corpus.corpus_id, "What is the backup period and how does a legal hold affect deletion?")
        by_id = {c.citation_id: c for c in response.citations}
        self.assertEqual({c.chunk_id for c in response.citations}, {4, 5})
        self.assertEqual(" ".join(c.text for c in response.claims), response.answer)
        for claim in response.claims:
            self.assertEqual(len(claim.citation_ids), 1)
            citation = by_id[claim.citation_ids[0]]
            source = next(r for r in results if r.chunk_id == citation.chunk_id)
            self.assertIn(claim.text, source.text)
            self.assertIn(claim.text, citation.snippet)
            self.assertEqual(citation.rerank_position, citation.chunk_id)
            self.assertIsNone(citation.page_number)
            self.assertEqual(claim.support_status, "source_excerpt")

    def test_generator_clears_request_provenance_on_refusal(self):
        generator = AnswerGenerator(provider="none", include_sources=False)
        generator.generate_answer("What is the backup period?", [passage("The backup period is 45 days.")])
        self.assertTrue(generator.extractive_statements)
        generator.generate_answer("What is the weather?", [passage("The backup period is 45 days.")])
        self.assertFalse(generator.extractive_statements)


if __name__ == "__main__":
    unittest.main()
