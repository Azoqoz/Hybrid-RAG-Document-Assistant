from collections.abc import Callable
from uuid import uuid4

from src.services.contracts import CorpusRecord


class CorpusNotFoundError(KeyError):
    pass


class InMemoryCorpusStore:
    def __init__(self, id_factory: Callable[[], str] | None = None):
        self._id_factory = id_factory or (lambda: uuid4().hex)
        self._corpora: dict[str, CorpusRecord] = {}

    def create(self) -> CorpusRecord:
        corpus_id = self._id_factory()
        if corpus_id in self._corpora:
            raise ValueError(f"Corpus ID already exists: {corpus_id}")

        corpus = CorpusRecord(corpus_id=corpus_id)
        self._corpora[corpus_id] = corpus
        return corpus

    def get(self, corpus_id: str) -> CorpusRecord:
        try:
            return self._corpora[corpus_id]
        except KeyError as error:
            raise CorpusNotFoundError(corpus_id) from error

    def reset(self, corpus_id: str) -> CorpusRecord:
        corpus = self.get(corpus_id)
        corpus.documents.clear()
        corpus.chunks.clear()
        corpus.hybrid_searcher = None
        corpus.index_build_count = 0
        return corpus

    def delete(self, corpus_id: str) -> bool:
        if corpus_id not in self._corpora:
            return False
        del self._corpora[corpus_id]
        return True

    def exists(self, corpus_id: str) -> bool:
        return corpus_id in self._corpora
