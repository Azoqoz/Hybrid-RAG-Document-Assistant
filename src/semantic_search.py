import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from src.chunking import DocumentChunk


class SemanticSearcher:
    def __init__(self, chunks: list[DocumentChunk]):
        self.chunks = chunks
        self.model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

        chunk_texts = [chunk.text for chunk in chunks]
        if chunk_texts:
            self.embeddings = self.model.encode(
                chunk_texts,
                convert_to_numpy=True,
                show_progress_bar=False,
            ).astype("float32")
            faiss.normalize_L2(self.embeddings)
        else:
            embedding_dimension = self.model.get_sentence_embedding_dimension()
            self.embeddings = np.empty((0, embedding_dimension), dtype="float32")

        embedding_dimension = self.embeddings.shape[1]
        self.index = faiss.IndexFlatIP(embedding_dimension)
        if len(self.embeddings) > 0:
            self.index.add(self.embeddings)

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        if not query.strip() or not self.chunks:
            return []

        query_embedding = self.model.encode(
            [query],
            convert_to_numpy=True,
            show_progress_bar=False,
        ).astype("float32")
        faiss.normalize_L2(query_embedding)

        search_k = min(top_k, len(self.chunks))
        scores, indices = self.index.search(query_embedding, search_k)

        results = []
        for score, index in zip(scores[0], indices[0]):
            if index == -1:
                continue

            chunk = self.chunks[index]
            results.append(
                {
                    "chunk_id": chunk.chunk_id,
                    "source": chunk.source,
                    "text": chunk.text,
                    "score": float(score),
                }
            )

        return results
