import re

from src.generator import AnswerGenerator
from src.services.contracts import Citation, Claim


class ClaimMapper:
    """Builds conservative claim-to-citation links from existing response data."""

    _STOP_WORDS = {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "that",
        "the",
        "this",
        "to",
        "was",
        "were",
        "with",
    }

    def build(
        self,
        answer: str,
        citations: list[Citation],
        is_summary: bool,
    ) -> list[Claim]:
        clean_answer = answer.strip()
        if not clean_answer:
            return []

        if is_summary:
            citation_ids = [citation.citation_id for citation in citations]
            return [
                Claim(
                    claim_id="claim-001",
                    text=clean_answer,
                    citation_ids=citation_ids,
                    support_status="summary_context" if citation_ids else None,
                )
            ]

        claim_texts = self._split_normal_answer(clean_answer)
        claims = []
        for index, claim_text in enumerate(claim_texts, start=1):
            citation_ids = self._matching_citation_ids(claim_text, citations)
            claims.append(
                Claim(
                    claim_id=f"claim-{index:03d}",
                    text=claim_text,
                    citation_ids=citation_ids,
                    support_status="evidence_match" if citation_ids else None,
                )
            )
        return claims

    def _split_normal_answer(self, answer: str) -> list[str]:
        claims = []
        paragraphs = re.split(r"\n\s*\n+", answer)

        for paragraph in paragraphs:
            paragraph = " ".join(paragraph.split()).strip()
            if not paragraph or paragraph == AnswerGenerator.MISSING_PROVIDER_KEY_NOTE:
                continue

            sentences = re.split(r"(?<=[.!?])\s+", paragraph)
            claims.extend(sentence.strip() for sentence in sentences if sentence.strip())

        return claims

    def _matching_citation_ids(
        self,
        claim_text: str,
        citations: list[Citation],
    ) -> list[str]:
        claim_terms = self._content_terms(claim_text)
        if not claim_terms:
            return []

        matches = []
        for citation in citations:
            citation_terms = self._content_terms(citation.snippet)
            overlap_count = len(claim_terms & citation_terms)
            minimum_term_count = min(len(claim_terms), len(citation_terms))
            overlap_ratio = (
                overlap_count / minimum_term_count
                if minimum_term_count
                else 0.0
            )

            if overlap_count >= 2 or overlap_ratio >= 0.5:
                matches.append(citation.citation_id)

        return matches

    def _content_terms(self, text: str) -> set[str]:
        return {
            term
            for term in re.findall(r"\b\w+\b", text.lower())
            if len(term) > 2 and term not in self._STOP_WORDS
        }
