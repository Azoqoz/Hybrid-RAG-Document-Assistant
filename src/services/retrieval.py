from src.hybrid_search import HybridSearcher
from src.reranker import CrossEncoderReranker
from src.services.contracts import CorpusRecord, RetrievalResult
from src.services.model_registry import SharedModelRegistry


class RetrievalService:
    SEMANTIC_WEIGHT = 0.65
    KEYWORD_WEIGHT = 0.35
    HYBRID_TOP_K = 10
    RERANK_TOP_K = 5

    def __init__(self, model_registry: SharedModelRegistry | None = None):
        self.model_registry = model_registry or SharedModelRegistry()
        self._reranker = None

    def build_indexes(self, corpus: CorpusRecord) -> None:
        embedding_model = self.model_registry.get_embedding_model()
        corpus.hybrid_searcher = HybridSearcher(
            corpus.chunks,
            semantic_model=embedding_model,
        )
        corpus.index_build_count += 1

    def semantic_search(
        self,
        corpus: CorpusRecord,
        query: str,
        top_k: int = 5,
    ) -> list[RetrievalResult]:
        searcher = self._get_searcher(corpus)
        return [
            RetrievalResult(
                filename=result["source"],
                chunk_id=result["chunk_id"],
                text=result["text"],
                semantic_score=result["score"],
            )
            for result in searcher.semantic_searcher.search(query, top_k=top_k)
        ]

    def keyword_search(
        self,
        corpus: CorpusRecord,
        query: str,
        top_k: int = 5,
    ) -> list[RetrievalResult]:
        searcher = self._get_searcher(corpus)
        return [
            RetrievalResult(
                filename=result["source"],
                chunk_id=result["chunk_id"],
                text=result["text"],
                keyword_score=result["score"],
            )
            for result in searcher.keyword_searcher.search(query, top_k=top_k)
        ]

    def hybrid_search(
        self,
        corpus: CorpusRecord,
        query: str,
        top_k: int = 5,
    ) -> list[RetrievalResult]:
        searcher = self._get_searcher(corpus)
        results = searcher.search(
            query,
            top_k=top_k,
            semantic_weight=self.SEMANTIC_WEIGHT,
            keyword_weight=self.KEYWORD_WEIGHT,
        )
        return [RetrievalResult.from_search_result(result) for result in results]

    def retrieve_and_rerank(
        self,
        corpus: CorpusRecord,
        query: str,
    ) -> list[RetrievalResult]:
        hybrid_results = self.hybrid_search(
            corpus,
            query,
            top_k=self.HYBRID_TOP_K,
        )
        reranker = self._get_reranker()
        reranked = reranker.rerank(
            query,
            [result.to_generator_result() for result in hybrid_results],
            top_k=self.RERANK_TOP_K,
        )
        return [RetrievalResult.from_search_result(result) for result in reranked]

    def _get_searcher(self, corpus: CorpusRecord) -> HybridSearcher:
        if corpus.hybrid_searcher is None:
            self.build_indexes(corpus)
        return corpus.hybrid_searcher

    def _get_reranker(self) -> CrossEncoderReranker:
        if self._reranker is None:
            self._reranker = CrossEncoderReranker(
                model=self.model_registry.get_reranker_model()
            )
        return self._reranker
