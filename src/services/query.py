from src.services.contracts import (
    Citation,
    QueryResponse,
    RetrievalResult,
    UploadPayload,
)
from src.services.corpus import InMemoryCorpusStore
from src.services.ingestion import DocumentIngestionService
from src.services.provider import ProviderService
from src.services.retrieval import RetrievalService


class QueryService:
    CITATION_LIMIT = 3
    CITATION_SNIPPET_LENGTH = 240

    def __init__(
        self,
        corpus_store: InMemoryCorpusStore | None = None,
        ingestion_service: DocumentIngestionService | None = None,
        retrieval_service: RetrievalService | None = None,
        provider_service: ProviderService | None = None,
    ):
        self.corpus_store = corpus_store or InMemoryCorpusStore()
        self.ingestion_service = ingestion_service or DocumentIngestionService()
        self.retrieval_service = retrieval_service or RetrievalService()
        self.provider_service = provider_service or ProviderService()

    def create_corpus(self) -> str:
        return self.corpus_store.create().corpus_id

    def ingest_documents(
        self,
        corpus_id: str,
        uploads: list[UploadPayload],
    ):
        corpus = self.corpus_store.get(corpus_id)
        next_chunk_id = corpus.chunks[-1].chunk_id + 1 if corpus.chunks else 1
        batch = self.ingestion_service.ingest(
            uploads,
            start_chunk_id=next_chunk_id,
        )
        corpus.documents.extend(batch.documents)
        corpus.chunks.extend(batch.chunks)
        self.retrieval_service.build_indexes(corpus)
        return batch

    def query(
        self,
        corpus_id: str,
        query: str,
        provider: str = "none",
    ) -> QueryResponse:
        corpus = self.corpus_store.get(corpus_id)
        is_summary = self.provider_service.is_summary_question(query)

        if is_summary:
            results = [
                RetrievalResult(
                    filename=chunk.source,
                    chunk_id=chunk.chunk_id,
                    text=chunk.text,
                )
                for chunk in corpus.chunks
            ]
        else:
            results = self.retrieval_service.retrieve_and_rerank(corpus, query)

        answer = self.provider_service.generate(provider, query, results)
        citations = [
            self._citation_from_result(result)
            for result in results[: self.CITATION_LIMIT]
        ]
        return QueryResponse(
            corpus_id=corpus_id,
            query=query,
            provider=provider,
            is_summary=is_summary,
            answer=answer,
            retrieval_results=results,
            citations=citations,
        )

    def reset_corpus(self, corpus_id: str) -> None:
        self.corpus_store.reset(corpus_id)

    def delete_corpus(self, corpus_id: str) -> bool:
        return self.corpus_store.delete(corpus_id)

    def _citation_from_result(self, result: RetrievalResult) -> Citation:
        text = " ".join(result.text.split())
        if len(text) > self.CITATION_SNIPPET_LENGTH:
            text = text[: self.CITATION_SNIPPET_LENGTH].rstrip() + "..."

        return Citation(
            filename=result.filename,
            chunk_id=result.chunk_id,
            text_snippet=text,
            semantic_score=result.semantic_score,
            keyword_score=result.keyword_score,
            hybrid_score=result.hybrid_score,
            rerank_score=result.rerank_score,
        )
