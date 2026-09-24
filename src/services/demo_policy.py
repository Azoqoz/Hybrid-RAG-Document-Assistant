"""Public demo policy and bounded, process-local session lifecycle.

The session token is a bearer capability, not authentication. Run one worker.
"""

import hashlib
import os
import time
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from uuid import UUID


SAMPLE_FILENAME = "Northstar_Cloud_Operations_Service_Handbook_2026.pdf"
SAMPLE_SHA256 = "8a27ff93146124a933a5bccbba709f9fc32f3e111b9b72f20d6dbf0d9f602a58"
QUESTIONS = {
    "demo_retention": "What are the data-retention periods for Standard and Enterprise plans, and what happens during a legal hold?",
    "demo_support": "Compare the P1 support response targets for Standard and Enterprise customers.",
    "demo_api_usage": "Which API requests are excluded from monthly usage and overage calculations?",
    "demo_private_deployment": "What requirements must be completed before a private deployment can move to production?",
    "demo_incident": "For a P1 incident during an active change window, what actions are required before a customer notification is sent?",
}
TITLES = ("Data retention", "P1 support", "API usage", "Private deployment", "Incident notification")


class DemoPolicyError(ValueError):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code


@dataclass
class DemoSession:
    expires_at: float
    corpus_id: str | None = None
    query_count: int = 0
    upload_count: int = 0


class DemoPolicy:
    MAX_UPLOAD_BYTES = 64 * 1024
    MAX_REQUEST_BYTES = MAX_UPLOAD_BYTES + 16 * 1024
    MAX_QUERY_LENGTH = 256
    MAX_QUERIES = 20
    MAX_UPLOADS = 5
    RETENTION_SECONDS = 24 * 60 * 60
    MAX_SESSIONS = 100

    def __init__(self, mode: str | None = None, clock=time.monotonic):
        self.mode = (mode or os.getenv("APP_MODE", "local")).strip().lower()
        if self.mode not in {"demo", "local"}:
            raise ValueError("APP_MODE must be demo or local")
        self.enabled = self.mode == "demo"
        self.clock = clock
        self.sessions: dict[str, DemoSession] = {}
        # Serialize demo operations, including ingestion/query/delete, so neither
        # concurrent uploads nor resets can race corpus or quota state.
        self.lock = RLock()

    def capabilities(self) -> dict:
        return {
            "app_mode": self.mode,
            "demo_mode_available": self.enabled,
            "sample_filename": SAMPLE_FILENAME,
            "sample_download_path": f"/demo/{SAMPLE_FILENAME}",
            "guided_questions": [
                {"id": key, "title": title, "question": question}
                for (key, question), title in zip(QUESTIONS.items(), TITLES)
            ],
            "allowed_document_count": 1,
            "max_upload_bytes": self.MAX_UPLOAD_BYTES,
            "max_queries_per_session": self.MAX_QUERIES,
            "max_uploads_per_session": self.MAX_UPLOADS,
            "retention_seconds": self.RETENTION_SECONDS,
            "retention_information": "Demo sessions expire after 24 hours; expired data is removed on the next demo request. Server restarts also clear demo data.",
            "provider": "none",
            "answer_generation": "no-key / extractive",
            "free_text_enabled": not self.enabled,
        }

    def session(self, token: str | None, store) -> DemoSession:
        try:
            parsed = UUID(token or "")
            if parsed.version != 4 or str(parsed) != token:
                raise ValueError
        except (ValueError, AttributeError):
            raise DemoPolicyError(400, "A valid UUID v4 X-Demo-Session-ID is required.")
        now = self.clock()
        for key, session in list(self.sessions.items()):
            if session.expires_at <= now:
                if session.corpus_id:
                    store.delete(session.corpus_id)
                del self.sessions[key]
        if token not in self.sessions:
            if len(self.sessions) >= self.MAX_SESSIONS:
                raise DemoPolicyError(429, "Demo capacity reached. Please try again later.")
            self.sessions[token] = DemoSession(now + self.RETENTION_SECONDS)
        return self.sessions[token]

    def require_owner(self, session: DemoSession, corpus_id: str) -> None:
        if session.corpus_id != corpus_id:
            raise DemoPolicyError(404, "Demo corpus not found for this session.")

    def validate_upload(self, filename: str, content: bytes) -> None:
        if Path(filename).suffix.lower() != ".pdf":
            raise DemoPolicyError(415, "Demo Mode accepts only the sample PDF.")
        if len(content) > self.MAX_UPLOAD_BYTES:
            raise DemoPolicyError(413, "Sample upload exceeds the demo byte limit.")
        if hashlib.sha256(content).hexdigest() != SAMPLE_SHA256:
            raise DemoPolicyError(422, "Upload the exact sample PDF downloaded from this website.")

    def question(self, session: DemoSession, question_id: str) -> str:
        question = QUESTIONS.get(question_id)
        if question is None:
            raise DemoPolicyError(422, "Unknown guided question ID.")
        if len(question) > self.MAX_QUERY_LENGTH:
            raise DemoPolicyError(422, "Guided question exceeds the demo length limit.")
        if session.query_count >= self.MAX_QUERIES:
            raise DemoPolicyError(429, "Demo query limit reached for this session. Reset does not renew the limit.")
        session.query_count += 1
        return question
