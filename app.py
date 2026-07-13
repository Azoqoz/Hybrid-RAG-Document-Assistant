import streamlit as st

from src.chunking import chunk_documents
from src.document_loader import load_uploaded_documents
from src.generator import AnswerGenerator
from src.hybrid_search import HybridSearcher
from src.keyword_search import KeywordSearcher
from src.reranker import CrossEncoderReranker
from src.semantic_search import SemanticSearcher


def split_answer_sections(answer: str) -> tuple[str, list[str]]:
    marker = "\n\nSources used:"
    if marker not in answer:
        return answer.strip(), []

    answer_body, sources_text = answer.split(marker, 1)
    sources = [
        line.strip()
        for line in sources_text.splitlines()
        if line.strip()
    ]

    return answer_body.strip(), sources


def render_sources(sources: list[str]) -> None:
    if not sources:
        return

    with st.expander("View sources", expanded=False):
        for source in sources:
            clean_source = source
            if ". Topic:" in clean_source:
                clean_source = clean_source.split(". ", 1)[-1]
            if "Topic:" in clean_source and "File:" in clean_source:
                topic_part, file_part = clean_source.split("File:", 1)
                topic = topic_part.replace("Topic:", "").strip(" -")
                file_name = file_part.strip()
                clean_source = f"{topic} - {file_name}"
            st.markdown(f"- {clean_source}")


def chunk_results_from_all_chunks(chunks) -> list[dict]:
    return [
        {
            "source": chunk.source,
            "chunk_id": chunk.chunk_id,
            "text": chunk.text,
        }
        for chunk in chunks
    ]


st.set_page_config(page_title="Hybrid RAG Document Assistant", layout="wide")

st.markdown(
    """
    <style>
    :root {
        --app-bg: #0b1020;
        --app-bg-soft: #0f172a;
        --card-bg: #111827;
        --card-bg-strong: #1e293b;
        --text-main: #f8fafc;
        --text-muted: #cbd5e1;
        --text-soft: #94a3b8;
        --border: #334155;
        --border-strong: #475569;
        --primary: #3b82f6;
        --primary-hover: #2563eb;
        --success-bg: #052e1a;
        --success-border: #166534;
        --success-text: #86efac;
    }

    .stApp {
        background:
            radial-gradient(circle at top left, rgba(59, 130, 246, 0.18), transparent 34rem),
            radial-gradient(circle at top right, rgba(20, 184, 166, 0.10), transparent 30rem),
            var(--app-bg);
        color: var(--text-main);
    }

    [data-testid="stHeader"],
    header[data-testid="stHeader"] {
        background: rgba(11, 16, 32, 0.96) !important;
        color: var(--text-main) !important;
        border-bottom: 1px solid rgba(51, 65, 85, 0.7);
    }

    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    [data-testid="stStatusWidget"],
    [data-testid="stHeader"] * {
        color: var(--text-main) !important;
    }

    .block-container {
        max-width: 1040px;
        padding-top: 2.5rem;
        padding-bottom: 4rem;
    }

    h1, h2, h3, h4, h5, h6,
    p, li, label, span,
    [data-testid="stMarkdownContainer"] {
        color: var(--text-main) !important;
    }

    .hero {
        padding: 2rem 0 1.35rem 0;
    }

    .hero h1 {
        color: var(--text-main);
        font-size: 3rem;
        line-height: 1.08;
        font-weight: 760;
        letter-spacing: 0;
        margin: 0 0 0.75rem 0;
    }

    .hero p {
        color: var(--text-muted);
        font-size: 1.13rem;
        line-height: 1.7;
        max-width: 720px;
        margin: 0;
    }

    .section-label {
        margin: 1.25rem 0 0.55rem 0;
        color: var(--text-muted) !important;
        font-size: 0.82rem;
        font-weight: 760;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }

    .upload-section-label {
        margin: 0;
        color: var(--text-muted) !important;
        font-size: 0.82rem;
        font-weight: 760;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: var(--card-bg);
        border: 1px solid var(--border);
        border-radius: 20px;
        box-shadow: 0 18px 44px rgba(0, 0, 0, 0.26);
    }

    [data-testid="stFileUploader"] {
        color: var(--text-main);
        margin-bottom: 0 !important;
    }

    [data-testid="stFileUploader"] section {
        background: var(--card-bg-strong);
        border: 1px dashed var(--border-strong);
        border-radius: 16px;
        padding: 0.85rem 1rem;
        min-height: auto;
    }

    [data-testid="stFileUploader"] small,
    [data-testid="stFileUploader"] span,
    [data-testid="stFileUploader"] p {
        color: var(--text-muted) !important;
    }

[data-testid="stTextInput"] input,
[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
textarea {
    background: #0f172a;
    color: var(--text-main) !important;
    border: 1px solid var(--border-strong);
    border-radius: 14px;
    box-shadow: none;
}

[data-testid="stTextInput"] input::placeholder,
textarea::placeholder {
        color: var(--text-soft);
        opacity: 1;
}

[data-testid="stTextInput"] input:focus,
[data-testid="stSelectbox"] div[data-baseweb="select"] > div:focus-within,
textarea:focus {
    border-color: var(--primary);
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.22);
}

[data-testid="stSelectbox"] * {
    color: var(--text-main) !important;
}

    div.stButton > button:first-child,
    [data-testid="stFormSubmitButton"] button {
        background: var(--primary);
        color: #ffffff;
        border: 1px solid var(--primary);
        border-radius: 999px;
        font-weight: 730;
        padding: 0.68rem 1.28rem;
        box-shadow: 0 10px 24px rgba(37, 99, 235, 0.34);
    }

    div.stButton > button:first-child:hover,
    [data-testid="stFormSubmitButton"] button:hover {
        background: var(--primary-hover);
        color: #ffffff;
        border-color: var(--primary-hover);
    }

    [data-testid="stBaseButton-secondary"] {
        background: #172033;
        color: var(--text-main) !important;
        border: 1px solid var(--border-strong);
        border-radius: 999px;
        font-weight: 650;
        box-shadow: none;
    }

    [data-testid="stBaseButton-secondary"]:hover {
        background: #1e293b;
        border-color: var(--primary);
        color: var(--text-main) !important;
    }

    .status-pill {
        display: inline-flex;
        align-items: center;
        width: fit-content;
        border: 1px solid var(--success-border);
        background: var(--success-bg);
        color: var(--success-text);
        border-radius: 999px;
        padding: 0.28rem 0.68rem;
        font-size: 0.84rem;
        font-weight: 680;
        line-height: 1.3;
        margin: 0;
        white-space: nowrap;
    }

    .element-container:has(.status-pill) {
        display: flex;
        justify-content: flex-end;
        margin: 0 !important;
    }

    .muted-note {
        color: var(--text-muted);
        font-size: 0.94rem;
        line-height: 1.58;
    }

    .answer-shell {
        padding: 0.1rem 0 0 0;
    }

    .answer-shell h2 {
        color: var(--text-main);
        font-size: 1.28rem;
        margin-bottom: 0.65rem;
    }

    .stMarkdown p, .stMarkdown li {
        line-height: 1.72;
    }

    [data-testid="stExpander"] {
        background: var(--card-bg);
        border: 1px solid var(--border);
        border-radius: 14px;
        color: var(--text-main);
    }

    [data-testid="stExpander"] summary {
        color: var(--text-main) !important;
        font-weight: 680;
    }

    [data-testid="stExpander"] details,
    [data-testid="stExpander"] div {
        color: var(--text-main) !important;
    }

    [data-testid="stAlert"] {
        background: var(--card-bg-strong);
        border: 1px solid var(--border);
        border-radius: 14px;
        color: var(--text-main) !important;
    }

    [data-testid="stMetric"] {
        background: var(--card-bg-strong);
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 0.75rem;
    }

    [data-testid="stMetric"] * {
        color: var(--text-main) !important;
    }

    [data-testid="stSpinner"] {
        color: var(--text-muted) !important;
    }

    hr {
        border-color: var(--border);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
        <h1>Hybrid RAG Document Assistant</h1>
        <p>Upload documents and ask questions with clear, source-grounded answers.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

uploaded_files = None

upload_header_left, upload_header_right = st.columns([0.72, 0.28], vertical_alignment="center")
with upload_header_left:
    st.markdown('<div class="upload-section-label">Upload Documents</div>', unsafe_allow_html=True)

upload_card = st.container(border=True)

with upload_card:
    uploaded_files = st.file_uploader(
        "Add PDF, DOCX, PPTX, or TXT files",
        type=["pdf", "docx", "pptx", "txt"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

if uploaded_files:
    documents = load_uploaded_documents(uploaded_files)
    chunks = chunk_documents(documents)

    with upload_header_right:
        file_label = "file" if len(documents) == 1 else "files"
        st.markdown(
            f'<div class="status-pill">{len(documents)} {file_label} uploaded</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="section-label">Ask Documents</div>', unsafe_allow_html=True)

    with st.container(border=True):
        with st.form("ask_documents_form"):
            provider_label = st.selectbox(
                "Answer provider",
                options=["Retrieval-only", "OpenAI", "Claude", "Gemini"],
                index=0,
            )
            final_query = st.text_input(
                "Question",
                placeholder=(
                    "Ask about your file, summarize a lecture, extract key ideas, "
                    "or explain a topic..."
                ),
                label_visibility="collapsed",
            )
            submitted = st.form_submit_button("Ask Documents")

        if submitted:
            if not final_query.strip():
                st.warning("Enter a question before generating an answer.")
            elif not chunks:
                st.warning("No searchable text was found in the uploaded documents.")
            else:
                provider_map = {
                    "Retrieval-only": "none",
                    "OpenAI": "openai",
                    "Claude": "anthropic",
                    "Gemini": "gemini",
                }
                generator = AnswerGenerator(provider=provider_map[provider_label])
                is_summary_question = generator._is_summary_question(final_query)
                status_text = (
                    "Reading the full document and preparing a summary..."
                    if is_summary_question
                    else "Finding the most relevant passages and preparing an answer..."
                )

                with st.spinner(status_text):
                    if is_summary_question:
                        answer_results = chunk_results_from_all_chunks(chunks)
                    else:
                        hybrid_searcher = HybridSearcher(chunks)
                        initial_results = hybrid_searcher.search(final_query, top_k=10)
                        reranker = CrossEncoderReranker()
                        answer_results = reranker.rerank(
                            final_query,
                            initial_results,
                            top_k=5,
                        )

                    answer = generator.generate_answer(final_query, answer_results)
                    answer_body, sources = split_answer_sections(answer)
                    st.session_state["current_answer_body"] = answer_body
                    st.session_state["current_answer_sources"] = sources
                    st.session_state["answer_reranked_results"] = answer_results

    if "current_answer_body" in st.session_state:
        st.markdown('<div class="section-label">Answer</div>', unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown('<div class="answer-shell">', unsafe_allow_html=True)
            st.markdown("## Answer")
            st.markdown(st.session_state["current_answer_body"])
            render_sources(st.session_state.get("current_answer_sources", []))
            st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("Advanced Debug Tools", expanded=False):
        st.markdown("### Advanced Debug Tools")

        metric_columns = st.columns(2)
        metric_columns[0].metric("Uploaded documents", len(documents))
        metric_columns[1].metric("Total chunks", len(chunks))

        st.markdown("#### Retrieved Source Details")

        answer_reranked_results = st.session_state.get("answer_reranked_results", [])
        if answer_reranked_results:
            for result in answer_reranked_results:
                rerank_score = result.get("rerank_score", 0.0)

                st.markdown(f"**File:** {result['source']}")
                st.write(f"Chunk ID: {result['chunk_id']}")
                st.write(f"Rerank score: {rerank_score:.4f}")
                st.write(result["text"])
                st.divider()
        else:
            st.info("Generate an answer to inspect retrieved source chunks.")

        st.markdown("#### Document Text Preview")

        for document in documents:
            st.markdown(f"**{document['source']}**")
            text = document["text"].strip()

            if text:
                st.text_area(
                    "Extracted text preview",
                    value=text[:3000],
                    height=250,
                    key=document["source"],
                )
            else:
                st.warning("No text could be extracted from this file.")

        st.markdown("#### Chunk Preview")

        if chunks:
            for chunk in chunks:
                st.markdown(f"**{chunk.source} - Chunk {chunk.chunk_id}**")
                st.write(chunk.text)
                st.divider()
        else:
            st.info("No chunks were created from the uploaded documents.")

        st.markdown("#### Semantic Search")

        query = st.text_input("Ask a question", key="semantic_query")

        if st.button("Semantic Search"):
            if not query.strip():
                st.warning("Enter a question before searching.")
            elif not chunks:
                st.warning("No chunks are available to search.")
            else:
                with st.spinner("Building embeddings and searching chunks..."):
                    searcher = SemanticSearcher(chunks)
                    results = searcher.search(query, top_k=5)

                if results:
                    for result in results:
                        score = result["score"]
                        label = (
                            f"{result['source']} - Chunk {result['chunk_id']} "
                            f"- Score {score:.4f}"
                        )

                        st.markdown(f"**{label}**")
                        st.write(f"Source: {result['source']}")
                        st.write(f"Chunk ID: {result['chunk_id']}")
                        st.write(f"Similarity score: {score:.4f}")
                        st.write(result["text"])
                        st.divider()
                else:
                    st.info("No semantic search results found.")

        st.markdown("#### Keyword Search")

        keyword_query = st.text_input("Enter keyword search query")

        if st.button("Keyword Search"):
            if not keyword_query.strip():
                st.warning("Enter a keyword query before searching.")
            elif not chunks:
                st.warning("No chunks are available to search.")
            else:
                keyword_searcher = KeywordSearcher(chunks)
                keyword_results = keyword_searcher.search(keyword_query, top_k=5)

                if keyword_results:
                    for result in keyword_results:
                        score = result["score"]
                        label = (
                            f"{result['source']} - Chunk {result['chunk_id']} "
                            f"- BM25 {score:.4f}"
                        )

                        st.markdown(f"**{label}**")
                        st.write(f"Source: {result['source']}")
                        st.write(f"Chunk ID: {result['chunk_id']}")
                        st.write(f"BM25 score: {score:.4f}")
                        st.write(result["text"])
                        st.divider()
                else:
                    st.info("No keyword search results found.")

        st.markdown("#### Hybrid Search")

        hybrid_query = st.text_input("Enter hybrid search query")

        if st.button("Hybrid Search"):
            if not hybrid_query.strip():
                st.warning("Enter a hybrid search query before searching.")
            elif not chunks:
                st.warning("No chunks are available to search.")
            else:
                with st.spinner("Combining semantic and keyword search results..."):
                    hybrid_searcher = HybridSearcher(chunks)
                    hybrid_results = hybrid_searcher.search(hybrid_query, top_k=5)

                if hybrid_results:
                    for result in hybrid_results:
                        semantic_score = result["semantic_score"]
                        keyword_score = result["keyword_score"]
                        hybrid_score = result["hybrid_score"]
                        label = (
                            f"{result['source']} - Chunk {result['chunk_id']} "
                            f"- Hybrid {hybrid_score:.4f}"
                        )

                        st.markdown(f"**{label}**")
                        st.write(f"Source: {result['source']}")
                        st.write(f"Chunk ID: {result['chunk_id']}")
                        st.write(f"Semantic score: {semantic_score:.4f}")
                        st.write(f"Keyword score: {keyword_score:.4f}")
                        st.write(f"Hybrid score: {hybrid_score:.4f}")
                        st.write(result["text"])
                        st.divider()
                else:
                    st.info("No hybrid search results found.")

        st.markdown("#### Hybrid Search + Reranking")

        rerank_query = st.text_input("Enter reranked search query")

        if st.button("Rerank Results"):
            if not rerank_query.strip():
                st.warning("Enter a reranked search query before searching.")
            elif not chunks:
                st.warning("No chunks are available to search.")
            else:
                with st.spinner("Running hybrid search and reranking results..."):
                    hybrid_searcher = HybridSearcher(chunks)
                    initial_results = hybrid_searcher.search(rerank_query, top_k=10)
                    reranker = CrossEncoderReranker()
                    reranked_results = reranker.rerank(
                        rerank_query,
                        initial_results,
                        top_k=5,
                    )

                if reranked_results:
                    for result in reranked_results:
                        semantic_score = result["semantic_score"]
                        keyword_score = result["keyword_score"]
                        hybrid_score = result["hybrid_score"]
                        rerank_score = result["rerank_score"]
                        label = (
                            f"{result['source']} - Chunk {result['chunk_id']} "
                            f"- Rerank {rerank_score:.4f}"
                        )

                        st.markdown(f"**{label}**")
                        st.write(f"Source: {result['source']}")
                        st.write(f"Chunk ID: {result['chunk_id']}")
                        st.write(f"Semantic score: {semantic_score:.4f}")
                        st.write(f"Keyword score: {keyword_score:.4f}")
                        st.write(f"Hybrid score: {hybrid_score:.4f}")
                        st.write(f"Rerank score: {rerank_score:.4f}")
                        st.write(result["text"])
                        st.divider()
                else:
                    st.info("No reranked results found.")
else:
    with upload_card:
        st.markdown(
            '<div class="muted-note">Upload one or more documents to begin. Your files are processed locally by the app pipeline.</div>',
            unsafe_allow_html=True,
        )
