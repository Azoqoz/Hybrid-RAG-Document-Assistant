from src.chunking import DocumentChunk
from src.keyword_search import KeywordSearcher
from src.semantic_search import SemanticSearcher


class HybridSearcher:
    def __init__(self, chunks: list[DocumentChunk]):
        self.chunks = chunks
        self.chunks_by_id = {chunk.chunk_id: chunk for chunk in chunks}
        self.semantic_searcher = SemanticSearcher(chunks)
        self.keyword_searcher = KeywordSearcher(chunks)

    def search(
        self,
        query: str,
        top_k: int = 5,
        semantic_weight: float = 0.65,
        keyword_weight: float = 0.35,
    ) -> list[dict]:
        if not query.strip() or not self.chunks:
            return []

        semantic_results = self.semantic_searcher.search(query, top_k=top_k)
        keyword_results = self.keyword_searcher.search(query, top_k=top_k)

        semantic_scores = self._normalize_scores(semantic_results)
        keyword_scores = self._normalize_scores(keyword_results)
        chunk_ids = set(semantic_scores) | set(keyword_scores)

        results = []
        for chunk_id in chunk_ids:
            chunk = self.chunks_by_id[chunk_id]
            semantic_score = semantic_scores.get(chunk_id, 0.0)
            keyword_score = keyword_scores.get(chunk_id, 0.0)
            hybrid_score = (
                semantic_weight * semantic_score + keyword_weight * keyword_score
            )

            results.append(
                {
                    "chunk_id": chunk.chunk_id,
                    "source": chunk.source,
                    "text": chunk.text,
                    "semantic_score": semantic_score,
                    "keyword_score": keyword_score,
                    "hybrid_score": hybrid_score,
                }
            )

        results.sort(key=lambda result: result["hybrid_score"], reverse=True)
        return results[:top_k]

    def _normalize_scores(self, results: list[dict]) -> dict[int, float]:
        if not results:
            return {}

        scores = [result["score"] for result in results]
        min_score = min(scores)
        max_score = max(scores)

        if max_score == min_score:
            return {result["chunk_id"]: 1.0 for result in results}

        return {
            result["chunk_id"]: (result["score"] - min_score) / (max_score - min_score)
            for result in results
        }
