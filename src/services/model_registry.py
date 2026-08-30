import gc
import os
from collections.abc import Callable
from contextlib import contextmanager
from threading import Lock


class SharedModelRegistry:
    EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
    RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    def __init__(
        self,
        embedding_loader: Callable[[], object] | None = None,
        reranker_loader: Callable[[], object] | None = None,
        low_memory_mode: bool | None = None,
    ):
        self._embedding_loader = embedding_loader or self._load_default_embedding_model
        self._reranker_loader = reranker_loader or self._load_default_reranker_model
        self.low_memory_mode = (
            self._environment_bool("LOW_MEMORY_MODE")
            if low_memory_mode is None
            else low_memory_mode
        )
        self._embedding_model = None
        self._reranker_model = None
        self._lock = Lock()
        self._lifecycle_lock = Lock()

    def get_embedding_model(self):
        if self.low_memory_mode:
            raise RuntimeError(
                "Use use_embedding_model() while LOW_MEMORY_MODE is enabled."
            )
        if self._embedding_model is None:
            with self._lock:
                if self._embedding_model is None:
                    self._embedding_model = self._embedding_loader()
        return self._embedding_model

    def get_reranker_model(self):
        if self.low_memory_mode:
            raise RuntimeError(
                "Use use_reranker_model() while LOW_MEMORY_MODE is enabled."
            )
        if self._reranker_model is None:
            with self._lock:
                if self._reranker_model is None:
                    self._reranker_model = self._reranker_loader()
        return self._reranker_model

    @contextmanager
    def use_embedding_model(self):
        if not self.low_memory_mode:
            yield self.get_embedding_model()
            return

        with self._lifecycle_lock:
            model = self._embedding_loader()
            try:
                yield model
            finally:
                del model
                gc.collect()

    @contextmanager
    def use_reranker_model(self):
        if not self.low_memory_mode:
            yield self.get_reranker_model()
            return

        with self._lifecycle_lock:
            model = self._reranker_loader()
            try:
                yield model
            finally:
                del model
                gc.collect()

    def clear(self) -> None:
        with self._lock:
            self._embedding_model = None
            self._reranker_model = None
        gc.collect()

    @staticmethod
    def _environment_bool(name: str, default: bool = False) -> bool:
        value = os.getenv(name)
        if value is None:
            return default
        return value.strip().lower() in {"1", "true", "yes", "on"}

    def _load_default_embedding_model(self):
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(self.EMBEDDING_MODEL)

    def _load_default_reranker_model(self):
        from sentence_transformers import CrossEncoder

        return CrossEncoder(self.RERANKER_MODEL)
