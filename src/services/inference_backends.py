"""Inference adapters used by the framework-neutral RAG services.

The FastEmbed models are ONNX equivalents of the local SentenceTransformers
models. Small floating-point score differences between the two runtimes are
expected and do not change the retrieval or reranking contracts.
"""

import numpy as np


class FastEmbedEmbeddingAdapter:
    EMBEDDING_DIMENSION = 384

    def __init__(self, model_name: str):
        from fastembed import TextEmbedding

        self.model_name = model_name
        self._model = TextEmbedding(model_name=model_name)

    def encode(
        self,
        texts,
        convert_to_numpy: bool = True,
        show_progress_bar: bool = False,
    ) -> np.ndarray:
        del convert_to_numpy, show_progress_bar
        return np.asarray(list(self._model.embed(list(texts))), dtype="float32")

    def get_sentence_embedding_dimension(self) -> int:
        return self.EMBEDDING_DIMENSION


class FastEmbedCrossEncoderAdapter:
    def __init__(self, model_name: str):
        from fastembed.rerank.cross_encoder import TextCrossEncoder

        self.model_name = model_name
        self._model = TextCrossEncoder(model_name=model_name)

    def predict(self, pairs) -> np.ndarray:
        pair_list = list(pairs)
        if not pair_list:
            return np.asarray([], dtype="float32")

        scores = self._model.rerank_pairs(pair_list)
        return np.asarray(list(scores), dtype="float32")
