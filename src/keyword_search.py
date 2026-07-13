import re

from rank_bm25 import BM25Okapi

from src.chunking import DocumentChunk


class KeywordSearcher:
    def __init__(self, chunks: list[DocumentChunk]):
        self.chunks = chunks
        self.tokenized_chunks = [self._tokenize(chunk.text) for chunk in chunks]
        self.bm25 = BM25Okapi(self.tokenized_chunks) if self.tokenized_chunks else None

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        if not query.strip() or not self.chunks or self.bm25 is None:
            return []

        tokenized_query = self._tokenize(query)
        if not tokenized_query:
            return []

        scores = self.bm25.get_scores(tokenized_query)
        ranked_indices = sorted(
            range(len(scores)),
            key=lambda index: scores[index],
            reverse=True,
        )

        results = []
        for index in ranked_indices[:top_k]:
            chunk = self.chunks[index]
            results.append(
                {
                    "chunk_id": chunk.chunk_id,
                    "source": chunk.source,
                    "text": chunk.text,
                    "score": float(scores[index]),
                }
            )

        return results

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r"\b\w+\b", text.lower())
