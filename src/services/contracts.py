from dataclasses import dataclass, field
from typing import Any

from src.chunking import DocumentChunk


@dataclass(frozen=True)
class UploadPayload:
    filename: str
    content: bytes


@dataclass(frozen=True)
class DocumentMetadata:
    filename: str
    file_type: str
    size_bytes: int
    character_count: int
    chunk_count: int


@dataclass
class IngestionBatch:
    documents: list[DocumentMetadata] = field(default_factory=list)
    chunks: list[DocumentChunk] = field(default_factory=list)


@dataclass
class CorpusRecord:
    corpus_id: str
    documents: list[DocumentMetadata] = field(default_factory=list)
    chunks: list[DocumentChunk] = field(default_factory=list)
    hybrid_searcher: Any | None = None
    index_build_count: int = 0

    @property
    def is_indexed(self) -> bool:
        return self.hybrid_searcher is not None


@dataclass(frozen=True)
class RetrievalResult:
    filename: str
    chunk_id: int
    text: str
    semantic_score: float | None = None
    keyword_score: float | None = None
    hybrid_score: float | None = None
    rerank_score: float | None = None
    page_number: int | None = None
    slide_number: int | None = None

    @classmethod
    def from_search_result(cls, result: dict) -> "RetrievalResult":
        return cls(
            filename=result["source"],
            chunk_id=result["chunk_id"],
            text=result["text"],
            semantic_score=result.get("semantic_score"),
            keyword_score=result.get("keyword_score"),
            hybrid_score=result.get("hybrid_score"),
            rerank_score=result.get("rerank_score"),
            page_number=result.get("page_number"),
            slide_number=result.get("slide_number"),
        )

    def to_generator_result(self) -> dict:
        result = {
            "source": self.filename,
            "chunk_id": self.chunk_id,
            "text": self.text,
        }
        if self.semantic_score is not None:
            result["semantic_score"] = self.semantic_score
        if self.keyword_score is not None:
            result["keyword_score"] = self.keyword_score
        if self.hybrid_score is not None:
            result["hybrid_score"] = self.hybrid_score
        if self.rerank_score is not None:
            result["rerank_score"] = self.rerank_score
        return result


@dataclass(frozen=True)
class Citation:
    citation_id: str
    filename: str
    chunk_id: int
    snippet: str
    semantic_score: float | None = None
    keyword_score: float | None = None
    hybrid_score: float | None = None
    rerank_score: float | None = None
    rerank_position: int | None = None
    page_number: int | None = None
    slide_number: int | None = None

    @property
    def text_snippet(self) -> str:
        """Backward-compatible alias for clients using the Phase 3 field name."""
        return self.snippet


@dataclass(frozen=True)
class Claim:
    claim_id: str
    text: str
    citation_ids: list[str]
    support_status: str | None = None


@dataclass(frozen=True)
class QueryResponse:
    corpus_id: str
    query: str
    provider: str
    is_summary: bool
    answer: str
    claims: list[Claim]
    retrieval_results: list[RetrievalResult]
    citations: list[Citation]
