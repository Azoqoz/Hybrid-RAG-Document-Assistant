import os
from contextlib import nullcontext

from dotenv import load_dotenv

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware

from src.api.schemas import (
    CorpusResponse,
    DemoQueryRequest,
    HealthResponse,
    QueryRequest,
    QueryResponse,
)
from src.api.demo_limits import DemoBodyLimitMiddleware
from src.services.demo_policy import DemoPolicy, DemoPolicyError, SAMPLE_FILENAME
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


def create_app(query_service: QueryService | None = None, demo_policy: DemoPolicy | None = None) -> FastAPI:
    load_dotenv()
    policy = demo_policy or DemoPolicy()
    application = FastAPI(title="Hybrid RAG Document Assistant API")
    application.state.query_service = query_service or QueryService()
    application.state.demo_policy = policy
    if policy.enabled:
        application.add_middleware(DemoBodyLimitMiddleware, max_bytes=policy.MAX_REQUEST_BYTES)
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

    def session_for(request: Request, service: QueryService, corpus_id: str | None = None):
        session = policy.session(request.headers.get("X-Demo-Session-ID"), service.corpus_store)
        if corpus_id is not None:
            policy.require_owner(session, corpus_id)
        return session

    @application.exception_handler(DemoPolicyError)
    async def demo_error_handler(request: Request, error: DemoPolicyError):
        return _json_error(error.status_code, str(error))

    @application.get("/capabilities")
    def capabilities():
        return policy.capabilities()

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
        request: Request,
        service: QueryService = Depends(get_query_service),
    ) -> CorpusResponse:
        with policy.lock if policy.enabled else nullcontext():
            if policy.enabled:
                session = session_for(request, service)
                if not session.corpus_id:
                    session.corpus_id = service.create_corpus()
                corpus_id = session.corpus_id
            else:
                corpus_id = service.create_corpus()
            return _corpus_response(service, corpus_id)

    @application.post(
        "/corpora/{corpus_id}/documents",
        response_model=CorpusResponse,
    )
    def upload_documents(
        corpus_id: str,
        request: Request,
        files: list[UploadFile] = File(...),
        service: QueryService = Depends(get_query_service),
    ) -> CorpusResponse:
        if policy.enabled:
            with policy.lock:
                session = session_for(request, service, corpus_id)
                corpus = service.corpus_store.get(corpus_id)
                if len(files) != 1 or corpus.documents:
                    raise DemoPolicyError(409, "Demo Mode allows one sample document per corpus. Reset to upload again.")
                if session.upload_count >= policy.MAX_UPLOADS:
                    raise DemoPolicyError(429, "Demo upload limit reached for this session.")
                upload = files[0]
                content = upload.file.read(policy.MAX_UPLOAD_BYTES + 1)
                policy.validate_upload(upload.filename or "", content)
                session.upload_count += 1
                try:
                    batch = service.ingest_documents(corpus_id, [UploadPayload(SAMPLE_FILENAME, content)])
                    if not batch.chunks or not any(chunk.text.strip() for chunk in batch.chunks):
                        raise DemoPolicyError(422, "No searchable text was found. The demo is not ready.")
                except Exception:
                    service.reset_corpus(corpus_id)
                    raise
                return _corpus_response(service, corpus_id)
        uploads = [UploadPayload(filename=upload.filename or "", content=upload.file.read()) for upload in files]
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
        request: Request,
        service: QueryService = Depends(get_query_service),
    ) -> CorpusResponse:
        with policy.lock if policy.enabled else nullcontext():
            if policy.enabled:
                session_for(request, service, corpus_id)
            return _corpus_response(service, corpus_id)

    @application.delete(
        "/corpora/{corpus_id}",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def delete_corpus(
        corpus_id: str,
        request: Request,
        service: QueryService = Depends(get_query_service),
    ) -> None:
        with policy.lock if policy.enabled else nullcontext():
            if policy.enabled:
                session = session_for(request, service, corpus_id)
            if not service.delete_corpus(corpus_id):
                raise CorpusNotFoundError(corpus_id)
            if policy.enabled:
                session.corpus_id = None

    @application.post(
        "/corpora/{corpus_id}/query",
        response_model=QueryResponse,
    )
    def query_corpus(
        corpus_id: str,
        request: Request,
        request_body: QueryRequest | DemoQueryRequest,
        service: QueryService = Depends(get_query_service),
    ) -> QueryResponse:
        if policy.enabled:
            with policy.lock:
                session = session_for(request, service, corpus_id)
                if not isinstance(request_body, DemoQueryRequest):
                    raise DemoPolicyError(422, "Demo Mode accepts guided question IDs only; free text and provider selection are disabled.")
                corpus = service.corpus_store.get(corpus_id)
                if not corpus.is_indexed or not corpus.chunks:
                    raise DemoPolicyError(409, "Upload and index the sample document first.")
                question = policy.question(session, request_body.question_id)
                response = service.query(corpus_id=corpus_id, query=question, provider="none")
                return QueryResponse.model_validate(response, from_attributes=True)
        if not isinstance(request_body, QueryRequest):
            raise HTTPException(422, "Local Mode requires a query string.")
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
