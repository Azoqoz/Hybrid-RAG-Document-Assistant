from collections.abc import Callable
from threading import Lock


class SharedModelRegistry:
    EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
    RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    def __init__(
        self,
        embedding_loader: Callable[[], object] | None = None,
        reranker_loader: Callable[[], object] | None = None,
    ):
        self._embedding_loader = embedding_loader or self._load_default_embedding_model
        self._reranker_loader = reranker_loader or self._load_default_reranker_model
        self._embedding_model = None
        self._reranker_model = None
        self._lock = Lock()

    def get_embedding_model(self):
        if self._embedding_model is None:
            with self._lock:
                if self._embedding_model is None:
                    self._embedding_model = self._embedding_loader()
        return self._embedding_model

    def get_reranker_model(self):
        if self._reranker_model is None:
            with self._lock:
                if self._reranker_model is None:
                    self._reranker_model = self._reranker_loader()
        return self._reranker_model

    def clear(self) -> None:
        with self._lock:
            self._embedding_model = None
            self._reranker_model = None

    def _load_default_embedding_model(self):
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(self.EMBEDDING_MODEL)

    def _load_default_reranker_model(self):
        from sentence_transformers import CrossEncoder

        return CrossEncoder(self.RERANKER_MODEL)
