from __future__ import annotations

import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEST_DOCUMENTS_DIR = PROJECT_ROOT / "test_documents"
LLM_ENV_KEYS = [
    "LLM_PROVIDER",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def print_section(title: str) -> None:
    print(f"\n=== {title} ===")


def fail(message: str) -> None:
    raise RuntimeError(f"FAIL: {message}")


def pop_llm_environment() -> dict:
    return {key: os.environ.pop(key, None) for key in LLM_ENV_KEYS}


def restore_llm_environment(original_values: dict) -> None:
    for key, value in original_values.items():
        if value is not None:
            os.environ[key] = value


def import_main_modules() -> dict:
    print_section("Imports")
    imported_modules = {}
    module_names = [
        "src.document_loader",
        "src.chunking",
        "src.semantic_search",
        "src.keyword_search",
        "src.hybrid_search",
        "src.reranker",
        "src.generator",
    ]

    for module_name in module_names:
        try:
            imported_modules[module_name] = __import__(module_name, fromlist=["*"])
            print(f"OK: imported {module_name}")
        except Exception as exc:
            print(f"FAIL: could not import {module_name}")
            print(f"Error: {type(exc).__name__}: {exc}")
            print("Next fix: install the dependencies in requirements.txt.")
            raise

    return imported_modules


def load_test_documents() -> list[dict]:
    print_section("Load Test Documents")
    documents = []

    for path in sorted(TEST_DOCUMENTS_DIR.glob("*.txt")):
        text = path.read_text(encoding="utf-8")
        documents.append({"source": path.name, "text": text})
        print(f"Loaded {path.name}: {len(text.split())} words")

    if not documents:
        fail("No test documents found in test_documents/")

    return documents


def run_chunking_test(documents: list[dict]):
    print_section("Chunking")
    from src.chunking import chunk_documents

    all_chunks = []
    for document in documents:
        chunks = chunk_documents([document])
        print(f"{document['source']}: {len(chunks)} chunks")
        if not chunks:
            fail(f"Zero chunks created for {document['source']}")
        all_chunks.extend(chunks)

    print(f"Total chunks: {len(all_chunks)}")
    return all_chunks


def print_basic_results(results: list[dict], score_name: str = "score") -> None:
    for index, result in enumerate(results, start=1):
        print(
            f"{index}. source={result['source']} "
            f"chunk_id={result['chunk_id']} "
            f"{score_name}={result[score_name]:.4f}"
        )


def run_semantic_search_test(chunks) -> None:
    print_section("Semantic Search")
    try:
        from src.semantic_search import SemanticSearcher

        searcher = SemanticSearcher(chunks)
        results = searcher.search("What are embeddings?", top_k=3)
        print_basic_results(results)
    except Exception as exc:
        print(f"FAIL: semantic search could not run: {type(exc).__name__}: {exc}")
        print(
            "Next fix: install sentence-transformers/faiss-cpu and allow the "
            "embedding model to download once."
        )


def run_keyword_search_test(chunks) -> None:
    print_section("Keyword Search")
    try:
        from src.keyword_search import KeywordSearcher

        searcher = KeywordSearcher(chunks)
        results = searcher.search("BM25", top_k=3)
        print_basic_results(results)
    except Exception as exc:
        print(f"FAIL: keyword search could not run: {type(exc).__name__}: {exc}")
        print("Next fix: install rank-bm25 from requirements.txt.")


def run_hybrid_search_test(chunks) -> list[dict]:
    print_section("Hybrid Search")
    try:
        from src.hybrid_search import HybridSearcher

        searcher = HybridSearcher(chunks)
        results = searcher.search("Why are citations important in RAG?", top_k=3)
        for index, result in enumerate(results, start=1):
            print(
                f"{index}. source={result['source']} "
                f"chunk_id={result['chunk_id']} "
                f"semantic_score={result['semantic_score']:.4f} "
                f"keyword_score={result['keyword_score']:.4f} "
                f"hybrid_score={result['hybrid_score']:.4f}"
            )
        return results
    except Exception as exc:
        print(f"FAIL: hybrid search could not run: {type(exc).__name__}: {exc}")
        print(
            "Next fix: make sure semantic search, FAISS, sentence-transformers, "
            "and rank-bm25 are installed and models can download."
        )
        return []


def run_reranking_test(chunks) -> list[dict]:
    print_section("Reranking")
    try:
        from src.hybrid_search import HybridSearcher
        from src.reranker import CrossEncoderReranker

        hybrid_searcher = HybridSearcher(chunks)
        initial_results = hybrid_searcher.search(
            "Why are citations important in RAG?",
            top_k=10,
        )
        reranker = CrossEncoderReranker()
        reranked_results = reranker.rerank(
            "Why are citations important in RAG?",
            initial_results,
            top_k=5,
        )

        for index, result in enumerate(reranked_results, start=1):
            print(
                f"{index}. source={result['source']} "
                f"chunk_id={result['chunk_id']} "
                f"rerank_score={result['rerank_score']:.4f}"
            )

        return reranked_results
    except Exception as exc:
        print(f"FAIL: reranking could not run: {type(exc).__name__}: {exc}")
        print(
            "Next fix: install sentence-transformers and allow the cross-encoder "
            "model to download once."
        )
        return []


def run_answer_generator_fallback_test(chunks) -> None:
    print_section("Answer Generator Fallback")
    try:
        from src.generator import AnswerGenerator
        from src.hybrid_search import HybridSearcher
        from src.reranker import CrossEncoderReranker

        original_env = pop_llm_environment()
        try:
            query = "What are embeddings and why are they useful in RAG?"
            hybrid_searcher = HybridSearcher(chunks)
            initial_results = hybrid_searcher.search(query, top_k=10)
            reranker = CrossEncoderReranker()
            reranked_results = reranker.rerank(query, initial_results, top_k=5)
            generator = AnswerGenerator(provider="none")
            answer = generator.generate_answer(query, reranked_results)
        finally:
            restore_llm_environment(original_env)

        print(answer)
        forbidden_terms = ["No OpenAI API key found", "[source:", "chunk:"]
        bad_terms = [term for term in forbidden_terms if term.lower() in answer.lower()]

        if bad_terms:
            print(f"FAIL: fallback answer contains forbidden terms: {bad_terms}")
        else:
            print("OK: fallback answer is clean.")
    except Exception as exc:
        print(f"FAIL: answer generator fallback test could not run: {type(exc).__name__}: {exc}")
        print("Next fix: resolve retrieval/reranking dependencies first.")


def run_missing_provider_key_tests(chunks) -> None:
    print_section("Missing Provider API Keys")
    try:
        from src.generator import AnswerGenerator

        original_env = pop_llm_environment()
        try:
            provider_results = [
                {
                    "chunk_id": chunk.chunk_id,
                    "source": chunk.source,
                    "text": chunk.text,
                }
                for chunk in chunks
                if "embedding" in chunk.text.lower() or "embeddings" in chunk.text.lower()
            ][:5]

            if not provider_results:
                fail("No embedding-related chunks available for provider fallback tests.")

            for provider in ["openai", "anthropic", "gemini"]:
                generator = AnswerGenerator(provider=provider)
                answer = generator.generate_answer(
                    "What are embeddings?",
                    provider_results,
                )
                print(f"\nProvider: {provider}")
                print(answer)

                if "no api key found for the selected provider" not in answer.lower():
                    fail(f"Missing-key fallback note was not shown for {provider}.")
                if "sources used:" not in answer.lower():
                    fail(f"Missing-key fallback answer did not include sources for {provider}.")
        finally:
            restore_llm_environment(original_env)

        print("OK: missing provider keys fall back without external API calls.")
    except Exception as exc:
        print(f"FAIL: missing provider key tests could not run: {type(exc).__name__}: {exc}")
        raise


def run_summary_question_test(cv_document: dict) -> None:
    print_section("Summary Question")
    try:
        from src.chunking import chunk_documents
        from src.generator import AnswerGenerator

        original_env = pop_llm_environment()
        try:
            cv_chunks = chunk_documents([cv_document])
            cv_results = [
                {
                    "chunk_id": chunk.chunk_id,
                    "source": chunk.source,
                    "text": chunk.text,
                    "semantic_score": 0.0,
                    "keyword_score": 0.0,
                    "hybrid_score": 0.0,
                    "rerank_score": 0.0,
                }
                for chunk in cv_chunks[:5]
            ]
            generator = AnswerGenerator(provider="none")
            answer = generator.generate_answer("summarize this file", cv_results)
        finally:
            restore_llm_environment(original_env)

        print(answer)

        lower_answer = answer.lower()
        if "cv or resume" not in lower_answer:
            fail("Summary answer did not identify the document as a CV or resume.")
        if "sources used:" not in lower_answer:
            fail("Summary answer did not include Sources used.")
    except Exception as exc:
        print(f"FAIL: summary question test could not run: {type(exc).__name__}: {exc}")


def run_lecture_summary_tests(lecture_document: dict) -> None:
    print_section("Lecture Summary Questions")
    try:
        from src.chunking import chunk_documents
        from src.generator import AnswerGenerator

        original_env = pop_llm_environment()
        try:
            lecture_chunks = chunk_documents([lecture_document])
            lecture_results = [
                {
                    "chunk_id": chunk.chunk_id,
                    "source": chunk.source,
                    "text": chunk.text,
                    "semantic_score": 0.0,
                    "keyword_score": 0.0,
                    "hybrid_score": 0.0,
                    "rerank_score": 0.0,
                }
                for chunk in lecture_chunks[:15]
            ]
            generator = AnswerGenerator(provider="none")

            for query in [
                "summarize this lecture",
                "what are the main topics?",
                "What is the document about?",
            ]:
                answer = generator.generate_answer(query, lecture_results)
                print(f"\nQuery: {query}")
                print(answer)

                for expected_text in ["Main topics", "Key points", "Sources used"]:
                    if expected_text.lower() not in answer.lower():
                        fail(
                            f"Lecture summary answer for '{query}' did not include {expected_text}."
                        )

                lower_answer = answer.lower()
                if "lecture slides or study material" not in lower_answer:
                    fail(
                        f"Lecture summary answer for '{query}' did not identify lecture slides or study material."
                    )

                main_topics_text = answer.split("Key points:", 1)[0].lower()
                generic_topics = {
                    "- lecture slides",
                    "- construct",
                    "- loop",
                }
                main_topic_lines = {
                    line.strip()
                    for line in main_topics_text.splitlines()
                    if line.strip().startswith("-")
                }
                expected_topics = {
                    "- introduction to lisp",
                    "- lisp basic syntax",
                    "- lisp operators",
                    "- lisp decision making",
                    "- lisp loops",
                }
                missing_topics = expected_topics - main_topic_lines
                if missing_topics:
                    fail(
                        f"Lecture summary answer for '{query}' missed outline topics: {sorted(missing_topics)}."
                    )

                for generic_topic in generic_topics:
                    if generic_topic in main_topic_lines:
                        fail(
                            f"Lecture summary answer for '{query}' used generic topic {generic_topic}."
                        )

                source_lines = [
                    line
                    for line in answer.splitlines()
                    if line.startswith("1. Topic:") or line.startswith("2. Topic:")
                ]
                if len(source_lines) != 1:
                    fail(
                        f"Lecture summary answer for '{query}' repeated duplicate source files."
                    )
        finally:
            restore_llm_environment(original_env)

        print("OK: lecture summary answers include the expected sections.")
    except Exception as exc:
        print(f"FAIL: lecture summary tests could not run: {type(exc).__name__}: {exc}")
        raise


def run_out_of_document_question_test(chunks) -> None:
    print_section("Out-of-Document Question")
    try:
        from src.generator import AnswerGenerator
        from src.hybrid_search import HybridSearcher
        from src.reranker import CrossEncoderReranker

        original_env = pop_llm_environment()
        try:
            query = "What is the weather today?"
            hybrid_searcher = HybridSearcher(chunks)
            initial_results = hybrid_searcher.search(query, top_k=10)
            reranker = CrossEncoderReranker()
            reranked_results = reranker.rerank(query, initial_results, top_k=5)
            generator = AnswerGenerator(provider="none")
            answer = generator.generate_answer(query, reranked_results)
        finally:
            restore_llm_environment(original_env)

        print(answer)
        if "do not provide enough information" not in answer.lower():
            fail("Out-of-document answer did not explain that the documents are insufficient.")

        print("OK: out-of-document answer is clear.")
    except Exception as exc:
        print(f"FAIL: out-of-document question test could not run: {type(exc).__name__}: {exc}")


def main() -> int:
    try:
        import_main_modules()
        documents = load_test_documents()
        chunks = run_chunking_test(documents)
        run_semantic_search_test(chunks)
        run_keyword_search_test(chunks)
        run_hybrid_search_test(chunks)
        run_reranking_test(chunks)
        run_answer_generator_fallback_test(chunks)
        run_missing_provider_key_tests(chunks)

        cv_document = next(
            document for document in documents if document["source"] == "cv_sample.txt"
        )
        run_summary_question_test(cv_document)
        lecture_document = next(
            document
            for document in documents
            if document["source"] == "lecture_slides_sample.txt"
        )
        run_lecture_summary_tests(lecture_document)
        run_out_of_document_question_test(chunks)
    except Exception as exc:
        print(f"\nSmoke tests stopped: {type(exc).__name__}: {exc}")
        return 1

    print("\nSmoke tests finished.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
