from src.services.contracts import (
    Citation,
    Claim,
    QueryResponse,
    RetrievalResult,
    UploadPayload,
)
from src.services.claims import ClaimMapper
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
        claim_mapper: ClaimMapper | None = None,
    ):
        self.corpus_store = corpus_store or InMemoryCorpusStore()
        self.ingestion_service = ingestion_service or DocumentIngestionService()
        self.retrieval_service = retrieval_service or RetrievalService()
        self.provider_service = provider_service or ProviderService()
        self.claim_mapper = claim_mapper or ClaimMapper()

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

        answer, statements = self.provider_service.generate_with_provenance(provider, query, results)
        citations = [
            self._citation_from_result(result, rerank_position)
            for rerank_position, result in enumerate(
                results[: self.CITATION_LIMIT],
                start=1,
            )
        ]
        claims = self.claim_mapper.build(answer, citations, is_summary)
        if statements:
            # Cite only the chunk actually used for each extractive statement.
            # Later reranked passages can contribute without changing retrieval.
            selected_keys = {(s.source, s.chunk_id) for s in statements}
            citations = [
                self._citation_from_result(
                    result, position,
                    snippet=" … ".join(s.text for s in statements
                                     if (s.source, s.chunk_id) == (result.filename, result.chunk_id)),
                )
                for position, result in enumerate(results, 1)
                if (result.filename, result.chunk_id) in selected_keys
            ]
            claims = [Claim(
                claim_id=f"claim-{index:03d}", text=statement.text,
                citation_ids=[f"citation-{statement.chunk_id:06d}"],
                support_status="source_excerpt",
            ) for index, statement in enumerate(statements, 1)]
        return QueryResponse(
            corpus_id=corpus_id,
            query=query,
            provider=provider,
            is_summary=is_summary,
            answer=answer,
            claims=claims,
            retrieval_results=results,
            citations=citations,
        )

    def reset_corpus(self, corpus_id: str) -> None:
        self.corpus_store.reset(corpus_id)

    def delete_corpus(self, corpus_id: str) -> bool:
        return self.corpus_store.delete(corpus_id)

    def _citation_from_result(
        self,
        result: RetrievalResult,
        rerank_position: int,
        snippet: str | None = None,
    ) -> Citation:
        text = " ".join(result.text.split())
        if len(text) > self.CITATION_SNIPPET_LENGTH:
            text = text[: self.CITATION_SNIPPET_LENGTH].rstrip() + "..."

        return Citation(
            citation_id=f"citation-{result.chunk_id:06d}",
            filename=result.filename,
            chunk_id=result.chunk_id,
            snippet=snippet if snippet is not None else text,
            semantic_score=result.semantic_score,
            keyword_score=result.keyword_score,
            hybrid_score=result.hybrid_score,
            rerank_score=result.rerank_score,
            rerank_position=(
                rerank_position
                if result.rerank_score is not None
                else None
            ),
            page_number=result.page_number,
            slide_number=result.slide_number,
        )
