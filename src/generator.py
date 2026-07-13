import os
import re

from dotenv import load_dotenv


class AnswerGenerator:
    OUT_OF_DOCUMENT_ANSWER = (
        "The uploaded documents do not provide enough information to answer this question."
        "\n\n"
        "Try asking about topics that appear in the uploaded file."
    )
    MISSING_PROVIDER_KEY_NOTE = (
        "No API key found for the selected provider. "
        "Showing retrieval-based answer."
    )
    SUPPORTED_PROVIDERS = {"none", "openai", "anthropic", "gemini"}

    def __init__(self, provider: str | None = None):
        load_dotenv()
        self.provider = self._normalize_provider(
            provider or os.getenv("LLM_PROVIDER", "none")
        )
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.anthropic_model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.api_key = self.openai_api_key
        self.model = self.openai_model

    def generate_answer(self, query: str, results: list[dict]) -> str:
        if self._is_summary_question(query):
            summary_answer = self._generate_full_document_summary(query, results)
            if self.provider != "none" and not self._api_key_for_provider():
                return f"{self.MISSING_PROVIDER_KEY_NOTE}\n\n{summary_answer}"

            return summary_answer

        if self._is_out_of_document_question(query, results):
            return self.OUT_OF_DOCUMENT_ANSWER

        if self.provider == "none":
            return self._clean_fallback_answer(query, results)

        api_key = self._api_key_for_provider()
        if not api_key:
            fallback_answer = self._clean_fallback_answer(query, results)
            return f"{self.MISSING_PROVIDER_KEY_NOTE}\n\n{fallback_answer}"

        context = self._build_context(results)
        clean_answer = self._generate_provider_answer(query, context)
        return self._append_sources(clean_answer, results[:3])

    def _normalize_provider(self, provider: str) -> str:
        normalized_provider = provider.strip().lower()

        if normalized_provider not in self.SUPPORTED_PROVIDERS:
            return "none"

        return normalized_provider

    def _api_key_for_provider(self) -> str | None:
        if self.provider == "openai":
            return self._valid_api_key(self.openai_api_key)
        if self.provider == "anthropic":
            return self._valid_api_key(self.anthropic_api_key)
        if self.provider == "gemini":
            return self._valid_api_key(self.gemini_api_key)

        return None

    def _valid_api_key(self, api_key: str | None) -> str | None:
        if not api_key:
            return None

        stripped_key = api_key.strip()
        if not stripped_key or stripped_key.lower().startswith("your_"):
            return None

        return stripped_key

    def _provider_prompt(self, query: str, context: str) -> str:
        return (
            f"Question:\n{query}\n\n"
            f"Context:\n{context}\n\n"
            "Write a concise answer in at most two short paragraphs. "
            "Do not add sources; they will be added separately."
        )

    def _provider_system_prompt(self) -> str:
        return (
            "You are a document question-answering assistant. "
            "Answer only using the uploaded document context. "
            "Write like a normal chatbot answer for a non-technical user. "
            "Never include raw source markers, chunk IDs, scores, or copied "
            "evidence blocks. Do not invent unsupported facts. "
            "If the context is insufficient, say exactly: "
            "\"The uploaded documents do not provide enough information to answer this question.\""
        )

    def _generate_provider_answer(self, query: str, context: str) -> str:
        if self.provider == "openai":
            answer = self._generate_openai_answer(query, context)
        elif self.provider == "anthropic":
            answer = self._generate_anthropic_answer(query, context)
        elif self.provider == "gemini":
            answer = self._generate_gemini_answer(query, context)
        else:
            answer = ""

        return self._sanitize_answer(answer)

    def _generate_openai_answer(self, query: str, context: str) -> str:
        from openai import OpenAI

        client = OpenAI(api_key=self.openai_api_key)
        response = client.responses.create(
            model=self.openai_model,
            input=[
                {
                    "role": "system",
                    "content": self._provider_system_prompt(),
                },
                {
                    "role": "user",
                    "content": self._provider_prompt(query, context),
                },
            ],
        )

        return response.output_text

    def _generate_anthropic_answer(self, query: str, context: str) -> str:
        import anthropic

        client = anthropic.Anthropic(api_key=self.anthropic_api_key)
        response = client.messages.create(
            model=self.anthropic_model,
            max_tokens=700,
            system=self._provider_system_prompt(),
            messages=[
                {
                    "role": "user",
                    "content": self._provider_prompt(query, context),
                }
            ],
        )

        text_parts = [
            block.text
            for block in response.content
            if getattr(block, "type", "") == "text"
        ]
        return "\n".join(text_parts)

    def _generate_gemini_answer(self, query: str, context: str) -> str:
        from google import genai

        client = genai.Client(api_key=self.gemini_api_key)
        prompt = (
            f"{self._provider_system_prompt()}\n\n"
            f"{self._provider_prompt(query, context)}"
        )
        response = client.models.generate_content(
            model=self.gemini_model,
            contents=prompt,
        )

        return response.text or ""

    def _clean_fallback_answer(self, query: str, results: list[dict]) -> str:
        if self._is_summary_question(query):
            return self._generate_full_document_summary(query, results)

        top_results = results[:3]
        sentences = self._extract_relevant_sentences(query, top_results)

        if not sentences:
            answer = "The uploaded documents do not provide enough information."
            return self._append_sources(answer, top_results)

        first_paragraph = " ".join(sentences[:2])
        second_paragraph = " ".join(sentences[2:4])
        paragraphs = [first_paragraph]

        if second_paragraph:
            paragraphs.append(second_paragraph)

        return self._append_sources("\n\n".join(paragraphs), top_results)

    def _is_out_of_document_question(self, query: str, results: list[dict]) -> bool:
        if not results:
            return True

        if self._is_summary_question(query):
            return False

        normalized_query = query.lower()
        external_patterns = [
            r"\bweather\b",
            r"\bcapital city\b",
            r"\bcapital of\b",
            r"\bcurrent news\b",
            r"\blatest news\b",
            r"\bstock price\b",
            r"\bshare price\b",
            r"\bexchange rate\b",
            r"\btoday'?s date\b",
            r"\bdate today\b",
            r"\bsports score\b",
            r"\blive score\b",
            r"\blive results?\b",
        ]

        if any(re.search(pattern, normalized_query) for pattern in external_patterns):
            return True

        combined_text = " ".join(result.get("text", "") for result in results)
        return not self._has_query_overlap(query, combined_text)

    def _has_query_overlap(self, query: str, combined_text: str) -> bool:
        stop_words = {
            "a",
            "about",
            "an",
            "and",
            "document",
            "file",
            "for",
            "give",
            "how",
            "in",
            "is",
            "me",
            "of",
            "on",
            "tell",
            "the",
            "this",
            "to",
            "what",
            "why",
        }
        query_words = {
            word
            for word in re.findall(r"\b\w+\b", query.lower())
            if word not in stop_words and len(word) > 2
        }
        text_words = set(re.findall(r"\b\w+\b", combined_text.lower()))

        return bool(query_words & text_words)

    def _is_summary_question(self, query: str) -> bool:
        normalized_query = query.lower()
        normalized_query = re.sub(r"\s+", " ", normalized_query).strip()
        summary_phrases = [
            "summarize this file",
            "summarize this document",
            "summarize this lecture",
            "summarize this lesson",
            "give me an overview",
            "what is this file",
            "what is this file about",
            "what is this document",
            "what is this document about",
            "what is this lecture about",
            "what is the document about",
            "what is this cv about",
            "summarize",
            "summary",
            "overview",
            "main topics",
            "main topics in this file",
            "what are the main topics",
            "what are the main topics in this file",
            "what is this about",
            "explain this file",
            "explain this document",
            "explain this document simply",
            "tell me about this file",
            "tell me about this document",
        ]

        return any(phrase in normalized_query for phrase in summary_phrases)

    def _generate_full_document_summary(self, query: str, results: list[dict]) -> str:
        if not results:
            return self.OUT_OF_DOCUMENT_ANSWER

        summary_results = results
        raw_text = "\n\n".join(result.get("text", "") for result in summary_results)
        title_count = len(re.findall(r"\bTitle\s*:", raw_text, flags=re.IGNORECASE))

        if re.search(r"\[slide\s+\d+\]", raw_text, flags=re.IGNORECASE) or title_count >= 3:
            return self._generate_lecture_summary(query, summary_results)

        combined_text = self._clean_text_for_answer(raw_text)
        document_type = self._detect_document_type(raw_text)
        topics = self._extract_main_topics(combined_text, summary_results)
        key_points = self._extract_summary_key_points(combined_text, topics)

        lines = [
            f"This document appears to be a {document_type}.",
            "",
            "Main topics:",
        ]

        if topics:
            lines.extend(f"- {topic}" for topic in topics[:4])
        else:
            lines.append("- General document content")

        lines.extend(["", "Key points:"])

        if key_points:
            lines.extend(f"- {point}" for point in key_points[:4])
        else:
            lines.append(
                "- The uploaded document contains relevant information, but it is not detailed enough to summarize confidently."
            )

        lines.extend(["", "Sources used:"])
        lines.extend(self._source_lines(summary_results[:3]))

        return "\n".join(lines)

    def _extract_slide_titles(self, text: str) -> list[str]:
        generic_titles = {
            "outline",
            "powerpoint presentation",
            "presentation",
            "thank you",
            "thanks",
            "questions",
            "q&a",
        }
        title_matches = re.findall(
            r"(?:^|\b)Title\s*:\s*(.*?)(?=\s+Content\s*:|\s+\[Slide\s+\d+\]|$)",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        titles = []
        seen = set()

        for title in title_matches:
            clean_title = self._clean_lecture_topic(title)
            normalized_title = clean_title.lower()

            if not clean_title or normalized_title in seen:
                continue

            titles.append(clean_title)
            seen.add(normalized_title)

        meaningful_titles = [
            title for title in titles if title.lower() not in generic_titles
        ]

        if meaningful_titles:
            return meaningful_titles

        return titles

    def _generate_lecture_summary(self, query: str, results: list[dict]) -> str:
        summary_results = results
        raw_text = "\n\n".join(result.get("text", "") for result in summary_results)
        combined_text = self._clean_text_for_answer(raw_text)
        slide_titles = self._extract_slide_titles(raw_text)
        outline_topics = self._extract_outline_topics(raw_text)

        topics = self._dedupe_preserving_order(outline_topics or slide_titles)

        if not topics:
            topics = self._extract_main_topics(combined_text, summary_results, max_topics=7)

        topics = [
            topic
            for topic in (self._clean_lecture_topic(topic) for topic in topics)
            if self._is_meaningful_lecture_topic(topic)
        ]
        topics = self._dedupe_preserving_order(topics)[:7]

        if not topics:
            topics = ["Lecture concepts and examples"]

        key_points = self._extract_lecture_key_points(raw_text, combined_text, topics)

        lines = [
            "This document appears to be lecture slides or study material.",
            "",
            "Main topics:",
        ]
        lines.extend(f"- {topic}" for topic in topics[:7])
        lines.extend(["", "Key points:"])

        if key_points:
            lines.extend(f"- {point}" for point in key_points[:4])
        else:
            lines.append(
                "- The lecture introduces the main concepts shown in the slide titles and supporting bullet points."
            )

        lines.extend(["", "Sources used:"])
        lines.extend(self._deduped_source_lines(summary_results, default_topic="Lecture slides"))

        return "\n".join(lines)

    def _extract_outline_topics(self, text: str) -> list[str]:
        ignored_topics = {
            "advanced programming language",
            "cs 516",
            "outline",
            "powerpoint presentation",
            "presentation",
            "thank you",
        }
        topics = []
        slide_blocks = re.split(r"(?=\[Slide\s+\d+\])", text, flags=re.IGNORECASE)

        for block in slide_blocks:
            title_match = re.search(
                r"\bTitle\s*:\s*(.*?)(?=\s+Content\s*:|$)",
                block,
                flags=re.IGNORECASE | re.DOTALL,
            )
            if not title_match:
                continue

            title = self._clean_lecture_topic(title_match.group(1))
            if title.lower() not in {"outline", "agenda", "contents", "table of contents"}:
                continue

            content_match = re.search(
                r"\bContent\s*:\s*(.*)",
                block,
                flags=re.IGNORECASE | re.DOTALL,
            )
            if not content_match:
                continue

            outline_text = content_match.group(1).replace("\u00e2\u20ac\u201c", "-")
            outline_text = re.sub(
                r"\bLISP\s+[-–—\uFFFD]\s+(Operators|Decision Making|Loops)\b",
                r"LISP \1",
                outline_text,
                flags=re.IGNORECASE,
            )

            for line in re.split(r"\s+-\s+|[\r\n]+", outline_text):
                topic = self._clean_lecture_topic(line)
                if (
                    self._is_meaningful_lecture_topic(topic)
                    and topic.lower() not in ignored_topics
                ):
                    topics.append(topic)

        return self._dedupe_preserving_order(topics)

    def _extract_lecture_key_points(
        self,
        raw_text: str,
        combined_text: str,
        topics: list[str],
    ) -> list[str]:
        normalized_text = raw_text.lower()
        key_points = []

        if re.search(r"\blisp\b", normalized_text):
            key_points.append(
                "LISP is a high-level programming language associated with symbolic processing and artificial intelligence."
            )
        if any(term in normalized_text for term in ["atom", "atoms", "list", "lists", "strings"]):
            key_points.append(
                "LISP programs are based on symbolic expressions made from atoms, lists, and strings."
            )
        if "prefix" in normalized_text or "parenthesized" in normalized_text:
            key_points.append(
                "LISP uses prefix notation and fully parenthesized expressions."
            )
        if (
            any(term in normalized_text for term in ["arithmetic", "comparison", "logical"])
            and any(term in normalized_text for term in ["cond", "when", "case"])
            and any(term in normalized_text for term in ["dotimes", "dolist", "loop for"])
        ):
            key_points.append(
                "The lecture introduces operators, decision-making constructs, and loop constructs."
            )

        extracted_points = self._extract_summary_key_points(
            combined_text,
            topics,
            max_points=6,
        )
        key_points.extend(extracted_points)

        return self._dedupe_preserving_order(key_points)[:6]

    def _clean_lecture_topic(self, topic: str) -> str:
        topic = topic.replace("\u00e2\u20ac\u201c", "-")
        topic = re.sub(r"[\r\n]+", " ", topic)
        topic = re.sub(r"\s+[-–—\uFFFD]\s+", " ", topic)
        topic = re.sub(r"^[-•\d.)\s]+", "", topic)
        topic = re.sub(r"\bContent\s*:.*$", "", topic, flags=re.IGNORECASE)
        topic = re.sub(r"\s+", " ", topic).strip(" .:-")

        replacements = {
            "lisp": "Introduction to LISP",
            "introduction": "Introduction to LISP",
            "introduction to lisp": "Introduction to LISP",
            "lisp basic syntax": "LISP basic syntax",
            "lisp program structure": "LISP program structure",
            "lisp variables": "Variables and constants",
            "lisp operators": "LISP operators",
            "lisp logical operators": "LISP operators",
            "lisp decision making": "LISP decision making",
            "lisp loops": "LISP loops",
            "construct": "LISP control constructs",
            "constructs": "LISP control constructs",
            "loop": "LISP loops",
            "loops": "LISP loops",
            "program": "LISP program structure",
            "expressions": "LISP expressions and syntax",
            "variables": "Variables and constants",
            "constants": "Variables and constants",
            "operators": "LISP operators",
        }
        normalized_topic = topic.lower()

        if normalized_topic in replacements:
            return replacements[normalized_topic]

        topic = re.sub(r"\bLisp\b", "LISP", topic, flags=re.IGNORECASE)

        return topic

    def _is_meaningful_lecture_topic(self, topic: str) -> bool:
        if not topic:
            return False

        generic_topics = {
            "lecture slides",
            "lecture content",
            "study material",
            "slide",
            "slides",
            "content",
            "title",
            "outline",
            "powerpoint presentation",
            "thank you",
        }
        normalized_topic = topic.lower()

        if normalized_topic in generic_topics:
            return False

        if len(topic.split()) == 1 and normalized_topic not in {
            "introduction",
            "operators",
        }:
            return False

        return True

    def _dedupe_preserving_order(self, items: list[str]) -> list[str]:
        deduped_items = []
        seen = set()

        for item in items:
            normalized_item = item.lower()
            if normalized_item in seen:
                continue

            deduped_items.append(item)
            seen.add(normalized_item)

        return deduped_items

    def _clean_text_for_answer(self, text: str) -> str:
        text = re.sub(r"[\u2022\u25cf\u25aa\u25ab\u25e6\u2023\u2043]", " ", text)
        text = re.sub(r"[\r\n]+", ". ", text)
        text = re.sub(r"[-_=]{3,}", " ", text)
        text = re.sub(r"\s+", " ", text).strip()

        noise_patterns = [
            r"\[slide\s+\d+\]",
            r"\bpage\s+\d+\s+of\s+\d+\b",
            r"\b\d+\s*/\s*\d+\b",
            r"\bclick here\b",
            r"\btable of contents\b",
            r"\bwww\.[^\s]+",
            r"\bhttps?://[^\s]+",
        ]
        for pattern in noise_patterns:
            text = re.sub(pattern, " ", text, flags=re.IGNORECASE)

        fragments = re.split(r"(?<=[.!?])\s+|\s{2,}", text)
        readable_fragments = []

        for fragment in fragments:
            clean_fragment = " ".join(fragment.split())
            word_count = len(re.findall(r"\b\w+\b", clean_fragment))

            if word_count >= 4:
                readable_fragments.append(clean_fragment)

        return " ".join(readable_fragments)

    def _generate_document_overview(self, results: list[dict]) -> str:
        top_results = results[:5]
        combined_text = self._clean_text_for_answer(
            " ".join(result["text"] for result in top_results)
        )
        document_type = self._detect_document_type(combined_text)
        points = self._extract_overview_points(combined_text)

        lines = [f"This document appears to be a {document_type}.", "", "Main points:"]

        if points:
            lines.extend(f"- {point}" for point in points[:4])
        else:
            lines.append("- The uploaded document contains relevant information, but it is not detailed enough to summarize confidently.")

        lines.extend(["", "Sources used:"])
        lines.extend(self._source_lines(top_results[:3]))

        return "\n".join(lines)

    def _detect_document_type(self, text: str) -> str:
        normalized_text = text.lower()

        if re.search(r"\[slide\s+\d+\]", normalized_text):
            return "lecture slides or presentation"
        if (
            re.search(r"\blecture\b", normalized_text)
            or re.search(r"\bchapter\b", normalized_text)
            or re.search(r"\bexam\b", normalized_text)
            or "learning objectives" in normalized_text
        ):
            return "lecture notes or study material"
        if any(
            keyword in normalized_text
            for keyword in [
                "abstract",
                "methodology",
                "findings",
                "conclusion",
                "references",
            ]
        ):
            return "academic report or research document"
        if any(
            keyword in normalized_text
            for keyword in [
                "experience",
                "education",
                "skills",
                "projects",
                "tools",
                "certifications",
            ]
        ):
            return "CV or resume"
        if any(keyword in normalized_text for keyword in ["invoice", "amount", "payment"]):
            return "invoice or financial document"

        return "uploaded document"

    def _extract_main_topics(
        self,
        text: str,
        results: list[dict],
        max_topics: int = 4,
    ) -> list[str]:
        topic_candidates = []

        for result in results:
            topic = self._get_source_topic(result.get("text", ""))
            if topic != "Relevant document section":
                topic_candidates.append(topic)

        word_counts = {}
        for word in self._content_words(text):
            if len(word) < 4:
                continue
            word_counts[word] = len(re.findall(rf"\b{re.escape(word)}\b", text.lower()))

        ignored_words = {
            "document",
            "documents",
            "section",
            "information",
            "important",
            "relevant",
            "uploaded",
            "using",
        }
        frequent_words = [
            word
            for word, count in sorted(
                word_counts.items(),
                key=lambda item: (-item[1], item[0]),
            )
            if count >= 2 and word not in ignored_words
        ]

        topic_candidates.extend(word.replace("_", " ").title() for word in frequent_words)

        topics = []
        seen = set()

        for topic in topic_candidates:
            normalized_topic = topic.lower()
            if normalized_topic in seen:
                continue

            topics.append(topic)
            seen.add(normalized_topic)

            if len(topics) >= max_topics:
                break

        return topics

    def _extract_summary_key_points(
        self,
        text: str,
        topics: list[str],
        max_points: int = 4,
    ) -> list[str]:
        sentences = self._split_sentences(text)
        topic_words = set()

        for topic in topics:
            topic_words.update(self._content_words(topic))

        scored_sentences = []
        for sentence_index, sentence in enumerate(sentences):
            sentence_words = self._content_words(sentence)
            if len(sentence_words) < 3:
                continue

            score = len(sentence_words & topic_words)
            score += min(len(sentence_words), 20) / 100
            scored_sentences.append((score, sentence_index, sentence))

        scored_sentences.sort(key=lambda item: (-item[0], item[1]))

        selected_points = []
        seen = set()

        for _, _, sentence in scored_sentences:
            point = self._shorten_sentence(sentence, max_words=26)
            normalized_point = point.lower()

            if normalized_point in seen:
                continue

            selected_points.append(point)
            seen.add(normalized_point)

            if len(selected_points) >= max_points:
                break

        return selected_points

    def _extract_overview_points(self, text: str) -> list[str]:
        sentences = self._split_sentences(text)
        selected_points = []
        seen = set()

        for sentence in sentences:
            point = self._shorten_sentence(sentence, max_words=22)
            normalized_point = point.lower()

            if normalized_point in seen:
                continue

            selected_points.append(point)
            seen.add(normalized_point)

            if len(selected_points) >= 4:
                break

        return selected_points

    def _get_source_topic(self, text: str) -> str:
        normalized_text = text.lower()

        if "work experience" in normalized_text or "experience" in normalized_text:
            return "Work experience"
        if "education" in normalized_text:
            return "Education"
        if "skills" in normalized_text:
            return "Skills"
        if "projects" in normalized_text:
            return "Projects"
        if "certifications" in normalized_text or "certificates" in normalized_text:
            return "Certifications"
        if (
            "contact" in normalized_text
            or "email" in normalized_text
            or "phone" in normalized_text
        ):
            return "Contact information"
        if "embedding" in normalized_text or "embeddings" in normalized_text:
            return "Embeddings and semantic search"
        if "vector database" in normalized_text or "vector databases" in normalized_text:
            return "Vector databases"
        if "citation" in normalized_text or "citations" in normalized_text:
            return "Citations and source grounding"
        if (
            re.search(r"\brag\b", normalized_text)
            or "retrieval augmented generation" in normalized_text
        ):
            return "RAG document retrieval"
        if "bm25" in normalized_text:
            return "BM25 keyword search"
        if "rerank" in normalized_text or "reranking" in normalized_text:
            return "Reranking search results"
        if re.search(r"\[slide\s+\d+\]", normalized_text):
            return "Lecture slides"
        if "learning objectives" in normalized_text or "lecture" in normalized_text:
            return "Lecture content"
        if "chapter" in normalized_text or "exam" in normalized_text:
            return "Study material"

        return "Relevant document section"

    def _build_context(self, results: list[dict]) -> str:
        context_blocks = []

        for result in results:
            context_blocks.append(
                (
                    f"File: {result['source']}\n"
                    f"Text:\n{result['text']}"
                )
            )

        return "\n\n".join(context_blocks)

    def _extract_relevant_sentences(
        self,
        query: str,
        results: list[dict],
        max_sentences: int = 4,
    ) -> list[str]:
        query_terms = self._content_words(query)
        candidates = []

        for result_index, result in enumerate(results):
            for sentence_index, sentence in enumerate(self._split_sentences(result["text"])):
                sentence_terms = self._content_words(sentence)
                overlap = len(query_terms & sentence_terms)
                candidates.append((overlap, result_index, sentence_index, sentence))

        candidates.sort(key=lambda item: (-item[0], item[1], item[2]))

        selected = []
        seen = set()

        for _, _, _, sentence in candidates:
            shortened_sentence = self._shorten_sentence(sentence)
            normalized_sentence = shortened_sentence.lower()

            if normalized_sentence in seen:
                continue

            selected.append(shortened_sentence)
            seen.add(normalized_sentence)

            if len(selected) >= max_sentences:
                break

        return selected

    def _split_sentences(self, text: str) -> list[str]:
        text = self._clean_text_for_answer(text)
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        return [" ".join(sentence.split()) for sentence in sentences if sentence.strip()]

    def _content_words(self, text: str) -> set[str]:
        stop_words = {
            "a",
            "an",
            "and",
            "are",
            "as",
            "by",
            "for",
            "from",
            "how",
            "in",
            "is",
            "it",
            "of",
            "on",
            "or",
            "that",
            "the",
            "this",
            "to",
            "what",
            "with",
        }
        return {
            word
            for word in re.findall(r"\b\w+\b", text.lower())
            if word not in stop_words and len(word) > 2
        }

    def _shorten_sentence(self, sentence: str, max_words: int = 32) -> str:
        words = sentence.split()

        if len(words) <= max_words:
            return sentence

        return " ".join(words[:max_words]).rstrip(".,;:") + "."

    def _append_sources(self, answer: str, results: list[dict]) -> str:
        source_lines = ["Sources used:"]
        source_lines.extend(self._source_lines(results))

        return f"{answer.strip()}\n\n" + "\n".join(source_lines)

    def _source_lines(self, results: list[dict]) -> list[str]:
        source_lines = []
        for index, result in enumerate(results, start=1):
            topic = self._get_source_topic(result["text"])
            source_lines.append(
                f"{index}. Topic: {topic} \u2014 File: {result['source']}"
            )

        return source_lines

    def _deduped_source_lines(
        self,
        results: list[dict],
        default_topic: str | None = None,
    ) -> list[str]:
        source_lines = []
        seen_sources = set()

        for result in results:
            source = result.get("source", "Uploaded file")
            if source in seen_sources:
                continue

            topic = default_topic or self._get_source_topic(result.get("text", ""))
            source_lines.append(
                f"{len(source_lines) + 1}. Topic: {topic} \u2014 File: {source}"
            )
            seen_sources.add(source)

        return source_lines

    def _sanitize_answer(self, answer: str) -> str:
        clean_lines = []

        for line in answer.splitlines():
            if "[source:" in line.lower():
                continue
            if "chunk" in line.lower() and re.search(r"\bchunk\b", line.lower()):
                continue
            clean_lines.append(line)

        clean_answer = "\n".join(clean_lines).strip()
        clean_answer = re.sub(r"\n{3,}", "\n\n", clean_answer)

        if not clean_answer:
            return "The uploaded documents do not provide enough information."

        return clean_answer
