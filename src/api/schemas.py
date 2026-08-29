from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DocumentMetadataResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    filename: str
    file_type: str
    size_bytes: int
    character_count: int
    chunk_count: int


class CorpusResponse(BaseModel):
    corpus_id: str
    document_count: int
    chunk_count: int
    indexed: bool
    documents: list[DocumentMetadataResponse]


class QueryRequest(BaseModel):
    query: str = Field(min_length=1)
    provider: Literal["none", "openai", "anthropic", "gemini"] = "none"

    @field_validator("query")
    @classmethod
    def query_must_contain_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("query must contain non-whitespace text")
        return stripped


class RetrievalResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    filename: str
    chunk_id: int
    text: str
    semantic_score: float | None = None
    keyword_score: float | None = None
    hybrid_score: float | None = None
    rerank_score: float | None = None


class CitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    filename: str
    chunk_id: int
    text_snippet: str
    semantic_score: float | None = None
    keyword_score: float | None = None
    hybrid_score: float | None = None
    rerank_score: float | None = None


class QueryResponse(BaseModel):
    corpus_id: str
    query: str
    provider: str
    is_summary: bool
    answer: str
    retrieval_results: list[RetrievalResultResponse]
    citations: list[CitationResponse]


class HealthResponse(BaseModel):
    status: str
