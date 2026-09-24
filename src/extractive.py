"""Conservative sentence selection from already-retrieved passages.

No retrieval, language model, or document-specific rules live here. Statements
remain excerpts of a single chunk; incomplete chunks are never stitched together.
"""

import re
import math
from dataclasses import dataclass


@dataclass(frozen=True)
class ExtractiveStatement:
    text: str
    source: str
    chunk_id: int
    rank: int
    position: int


class ExtractiveAssembler:
    STOP = set("a an and are as at be been both by do does during for from how in into is it of on or that the their these this those to until was were what when which while who why with would can could should must may compare happens".split())
    # Predicate recognition is a conservative fragment filter, not a parser.
    PREDICATE = re.compile(
        r"\b(?:is|are|was|were|has|have|had|must|shall|should|can|cannot|could|may|will|"
        r"means|includes?|contains?|requires?|provides?|uses?|supports?|allows?|"
        r"retains?|suspends?|applies|apply|begins?|starts?|ends?|remains?|"
        r"counts?|counted|excludes?|continues?|enters?|improves?|retrieves?|"
        r"matches|preserves?|reorders?|reports?|sends?|validates?|measures?|"
        r"explains?|describes?|protects?|stores?|deletes?|expires?|owns?|"
        r"encrypts?|processes|process|returns?|runs?|rejects?|accepts?|"
        r"increases?|decreases?|reduces?|affects?|enables?|prevents?|"
        r"limits?|verifies|verify|approves?|schedules?|see|refer)\b", re.I
    )
    DANGLING = re.compile(r"\b(?:a|an|the|and|or|but|because|to|of|for|from|with|by|as|than|when|if|unless|until|while|is|are|was|were|be|been|must|shall|should|can|could|may|will|not|its|their|which|that)\s*[.!?]?$", re.I)

    @classmethod
    def terms(cls, text: str) -> set[str]:
        words = re.findall(r"\b[\w]+\b", text.lower())
        # Inflection normalization affects ranking only, never the quoted text.
        def stem(word):
            word = {"sent": "send", "kept": "keep", "held": "hold", "made": "make", "found": "find"}.get(word, word)
            if len(word) > 4 and word.endswith("s") and not word.endswith("ss"):
                word = word[:-1]
            if len(word) > 5 and word.endswith("ed"):
                word = word[:-2]
            elif len(word) > 5 and word.endswith("e"):
                word = word[:-1]
            return word
        return {stem(word) for word in words if word not in cls.STOP and len(word) > 1}

    def candidates(self, results: list[dict]) -> list[ExtractiveStatement]:
        candidates = []
        for rank, result in enumerate(results):
            raw = result["text"]
            # Keep explicit list/paragraph boundaries, but join ordinary PDF wraps.
            raw = re.sub(r"[\u007f\u2022\u25cf\u25aa\u25ab\u25e6]", "\n\n", raw)
            blocks = re.split(r"\n\s*\n|(?:^|\n)\s*[-*]\s+", raw)
            position = 0
            for block in blocks:
                text = " ".join(block.split())
                # Page and section markers are boundaries, not sentence material.
                # This also prevents attaching a footer to the next page's prose.
                pieces = self._segments(text)
                for piece in pieces:
                    for fragment in self._sentences(piece):
                        sentence = fragment.strip()
                        if self._flattened_table(sentence):
                            continue
                        sentence = self._strip_heading(sentence)
                        position += 1
                        if not self._complete(sentence):
                            continue
                        candidates.append(ExtractiveStatement(
                            sentence, result["source"], result["chunk_id"], rank, position
                        ))
        return candidates

    @staticmethod
    def _flattened_table(text: str) -> bool:
        # Several lowercase-to-title transitions before a grammatical auxiliary
        # indicate flattened row labels. Count word starts so ordinary multiword
        # proper names (e.g. Amazon Web Services) are not mistaken for rows.
        auxiliary = re.search(r"\b(?:is|are|was|were|must|shall|should|can|cannot|could|may|will|has|have|had)\b", text, re.I)
        prefix = text[:auxiliary.start()] if auxiliary else text
        return len(re.findall(r"\b[a-z][a-z-]*\s+[A-Z][a-z]+\b", prefix)) >= 3

    def _segments(self, text: str) -> list[str]:
        pieces = []
        start = 0
        for marker in re.finditer(r"\bPage\s+\d+(?:\s+of\s+\d+)?\b|\bSECTION\s+\d+\b|\[Slide\s+\d+\]", text, re.I):
            prefix = re.split(r"[.!?]\s+", text[start:marker.start()])[-1]
            suffix = text[marker.end():].lstrip()
            # Preserve prose references such as "See Page 4 for details" or
            # "Section 2 describes access controls"; discard standalone markers.
            if self.PREDICATE.search(prefix) or self.PREDICATE.match(suffix):
                continue
            pieces.append(text[start:marker.start()])
            start = marker.end()
        pieces.append(text[start:])
        return pieces

    @staticmethod
    def _sentences(text: str) -> list[str]:
        pieces = []
        start = 0
        for boundary in re.finditer(r"(?<=[.!?])\s+(?=[A-Z\d])", text):
            prefix = text[start:boundary.start()]
            if re.search(r"\b(?:Mr|Mrs|Ms|Dr|Prof|Sr|Jr|[A-Z])\.$", prefix):
                continue
            pieces.append(prefix)
            start = boundary.end()
        pieces.append(text[start:])
        return pieces

    def _strip_heading(self, text: str) -> str:
        # In flattened PDF text a heading can precede a capitalized sentence.
        # Remove only a short predicate-free prefix; never cut a conditional,
        # negation, clause with commas/colons, or an existing complete sentence.
        for match in re.finditer(r"(?<=[a-z])\s+(?=(?:[A-Z][a-z]+|A|I)\b)", text):
            prefix, suffix = text[:match.start()], text[match.end():]
            if not 2 <= len(prefix.split()) <= 12 or re.search(
                r"[,;:]|\b(?:no|not|if|unless|when|before|after|for|either|both|neither|"
                r"only|all|in|on|at|by|with|from|to|of|under|over|between|within|without)\b",
                prefix, re.I,
            ):
                continue
            if prefix.split()[-1].lower() in {"and", "or"}:
                continue
            if prefix.split()[-1][:1].isupper() and not re.match(r"(?:A|The|This|These)\b", suffix):
                continue
            if not self.PREDICATE.search(prefix) and self.PREDICATE.search(suffix):
                text = suffix
                break
        return text.strip()

    def _complete(self, text: str) -> bool:
        words = text.split()
        if len(words) < 4 or len(words) > 100 or not text[:1].isupper():
            return False
        if self.DANGLING.search(text) or not self.PREDICATE.search(text):
            return False
        predicate = self.PREDICATE.search(text)
        if len(re.findall(r"[a-z]\s+[A-Z][a-z]+", text[:predicate.start()])) >= 3:
            return False  # flattened columns/title chains, not a prose subject
        # A punctuation-free tail at a word chunk boundary is unsafe to emit.
        if not re.search(r"[.!?]$", text):
            return False
        return True

    def _duplicate(self, left: str, right: str) -> bool:
        a, b = self.terms(left), self.terms(right)
        # Different quantities and negations are distinct facts, even when the
        # rest of the sentence is almost identical.
        facts = lambda text: set(re.findall(r"\b\d+(?:[./-]\d+)*\b|\b(?:not|no|never|unless|only|must|may|can|cannot|should|required|before|after)\b", text.lower()))
        if facts(left) != facts(right):
            return False
        left_names = {word.lower() for word in re.findall(r"\b[A-Z][\w-]+\b", left)}
        right_names = {word.lower() for word in re.findall(r"\b[A-Z][\w-]+\b", right)}
        if (left_names & (a - b)) and (right_names & (b - a)):
            return False
        return bool(a and b) and len(a & b) / len(a | b) >= 0.82

    def select(self, query: str, results: list[dict]) -> list[ExtractiveStatement]:
        query_terms = self.terms(query)
        candidates = self.candidates(results)
        unique = []
        for candidate in candidates:
            if not any(self._duplicate(candidate.text, other.text) for other in unique):
                unique.append(candidate)
        selected = []
        covered: set[str] = set()
        numbers = lambda text: set(re.findall(r"\b\d+(?:[./-]\d+)*\b", text))
        def relevance(candidate):
            overlap = self.terms(candidate.text) & query_terms
            detail = min(3, max(0, candidate.text.count(",") - 1) * 0.6 + candidate.text.count(";"))
            return (len(overlap) + 1.5 * len(overlap) / math.sqrt(len(candidate.text.split()))
                    + detail + (1 if numbers(candidate.text) else 0) - 0.12 * candidate.rank)
        strongest = max((relevance(c) for c in unique), default=0)
        while unique and len(selected) < 4:
            def score(candidate):
                terms = self.terms(candidate.text)
                overlap = terms & query_terms
                novelty = overlap - covered
                redundancy = max((len(terms & self.terms(s.text)) / max(1, len(terms)) for s in selected), default=0)
                numeric_sources = [s for s in selected if numbers(s.text)]
                # Comparisons often repeat the same predicate with a different
                # entity/value. Prefer that counterpart over unrelated numbers.
                counterpart = any(
                    numbers(candidate.text) != numbers(s.text)
                    and len(terms & self.terms(s.text)) / max(1, len(terms | self.terms(s.text))) >= 0.5
                    for s in numeric_sources
                )
                numeric_fact = bool(numbers(candidate.text)) and len(candidate.text.split()) <= 20 and (not numeric_sources or counterpart)
                if len(overlap) < min(2, len(query_terms)) or relevance(candidate) < strongest * 0.45:
                    return -1.0
                if selected and not novelty and not numeric_fact:
                    return -1.0
                return relevance(candidate) + len(novelty) - (0 if numeric_fact else 2 * redundancy)
            best = max(unique, key=score)
            terms = self.terms(best.text)
            if not terms & query_terms:
                break
            if score(best) <= 0:
                break
            selected.append(best)
            covered |= terms
            unique.remove(best)
        # Keep a short anaphoric continuation with its selected source sentence.
        if len(selected) == 1:
            first = selected[0]
            for candidate in unique:
                if (candidate.rank == first.rank and candidate.position == first.position + 1
                        and len(candidate.text.split()) <= 12
                        and re.search(r"\b(?:it|their|these|this|they)\b", candidate.text, re.I)):
                    selected.append(candidate)
                    break
        return sorted(selected, key=lambda s: (s.source, s.chunk_id, s.position))
