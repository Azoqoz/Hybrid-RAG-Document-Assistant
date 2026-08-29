import os

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware

from src.api.schemas import (
    CorpusResponse,
    HealthResponse,
    QueryRequest,
    QueryResponse,
)
from src.services import (
    CorpusNotFoundError,
    QueryService,
    UnsupportedFileTypeError,
    UploadPayload,
)


def _environment_list(name: str, default: str) -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


def _environment_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _corpus_response(service: QueryService, corpus_id: str) -> CorpusResponse:
    corpus = service.corpus_store.get(corpus_id)
    return CorpusResponse(
        corpus_id=corpus.corpus_id,
        document_count=len(corpus.documents),
        chunk_count=len(corpus.chunks),
        indexed=corpus.is_indexed,
        documents=corpus.documents,
    )


def get_query_service(request: Request) -> QueryService:
    return request.app.state.query_service


def create_app(query_service: QueryService | None = None) -> FastAPI:
    application = FastAPI(title="Hybrid RAG Document Assistant API")
    application.state.query_service = query_service or QueryService()
    application.add_middleware(
        CORSMiddleware,
        allow_origins=_environment_list(
            "CORS_ALLOWED_ORIGINS",
            "http://localhost:3000",
        ),
        allow_credentials=_environment_bool("CORS_ALLOW_CREDENTIALS"),
        allow_methods=_environment_list("CORS_ALLOWED_METHODS", "*"),
        allow_headers=_environment_list("CORS_ALLOWED_HEADERS", "*"),
    )

    @application.exception_handler(CorpusNotFoundError)
    async def corpus_not_found_handler(request: Request, error: CorpusNotFoundError):
        corpus_id = error.args[0] if error.args else "unknown"
        return _json_error(status.HTTP_404_NOT_FOUND, f"Corpus not found: {corpus_id}")

    @application.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok")

    @application.post(
        "/corpora",
        response_model=CorpusResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_corpus(
        service: QueryService = Depends(get_query_service),
    ) -> CorpusResponse:
        corpus_id = service.create_corpus()
        return _corpus_response(service, corpus_id)

    @application.post(
        "/corpora/{corpus_id}/documents",
        response_model=CorpusResponse,
    )
    async def upload_documents(
        corpus_id: str,
        files: list[UploadFile] = File(...),
        service: QueryService = Depends(get_query_service),
    ) -> CorpusResponse:
        uploads = [
            UploadPayload(
                filename=upload.filename or "",
                content=await upload.read(),
            )
            for upload in files
        ]
        try:
            service.ingest_documents(corpus_id, uploads)
        except UnsupportedFileTypeError as error:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=str(error),
            ) from error
        return _corpus_response(service, corpus_id)

    @application.get(
        "/corpora/{corpus_id}",
        response_model=CorpusResponse,
    )
    def get_corpus(
        corpus_id: str,
        service: QueryService = Depends(get_query_service),
    ) -> CorpusResponse:
        return _corpus_response(service, corpus_id)

    @application.delete(
        "/corpora/{corpus_id}",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def delete_corpus(
        corpus_id: str,
        service: QueryService = Depends(get_query_service),
    ) -> None:
        if not service.delete_corpus(corpus_id):
            raise CorpusNotFoundError(corpus_id)

    @application.post(
        "/corpora/{corpus_id}/query",
        response_model=QueryResponse,
    )
    def query_corpus(
        corpus_id: str,
        request_body: QueryRequest,
        service: QueryService = Depends(get_query_service),
    ) -> QueryResponse:
        response = service.query(
            corpus_id=corpus_id,
            query=request_body.query,
            provider=request_body.provider,
        )
        return QueryResponse.model_validate(response, from_attributes=True)

    return application


def _json_error(status_code: int, detail: str):
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=status_code, content={"detail": detail})


app = create_app()
