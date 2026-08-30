CrossEncoder = None


class CrossEncoderReranker:
    def __init__(self, model=None):
        if model is None:
            cross_encoder_class = CrossEncoder
            if cross_encoder_class is None:
                from sentence_transformers import CrossEncoder as cross_encoder_class

            model = cross_encoder_class("cross-encoder/ms-marco-MiniLM-L-6-v2")
        self.model = model

    def rerank(self, query: str, results: list[dict], top_k: int = 5) -> list[dict]:
        if not query.strip() or not results:
            return []

        pairs = [(query, result["text"]) for result in results]
        scores = self.model.predict(pairs)

        reranked_results = []
        for result, score in zip(results, scores):
            reranked_result = result.copy()
            reranked_result["rerank_score"] = float(score)
            reranked_results.append(reranked_result)

        reranked_results.sort(
            key=lambda result: result["rerank_score"],
            reverse=True,
        )
        return reranked_results[:top_k]
