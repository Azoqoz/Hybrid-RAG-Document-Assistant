from collections.abc import Callable

from src.generator import AnswerGenerator
from src.services.contracts import RetrievalResult


class ProviderService:
    def __init__(
        self,
        generator_factory: Callable[..., AnswerGenerator] = AnswerGenerator,
    ):
        self._generator_factory = generator_factory
        self._routing_generator = generator_factory(
            provider="none",
            include_sources=False,
        )

    def is_summary_question(self, query: str) -> bool:
        return self._routing_generator._is_summary_question(query)

    def generate(
        self,
        provider: str,
        query: str,
        results: list[RetrievalResult],
    ) -> str:
        generator = self._generator_factory(
            provider=provider,
            include_sources=False,
        )
        return generator.generate_answer(
            query,
            [result.to_generator_result() for result in results],
        )
