from dataclasses import dataclass


@dataclass
class DocumentChunk:
    chunk_id: int
    source: str
    text: str


def chunk_text(
    text: str,
    source: str,
    start_chunk_id: int,
    chunk_size: int = 120,
    chunk_overlap: int = 30,
) -> list[DocumentChunk]:
    words = text.split()
    chunks = []
    chunk_id = start_chunk_id

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")

    if chunk_overlap < 0:
        raise ValueError("chunk_overlap must be 0 or greater")

    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    step = chunk_size - chunk_overlap

    for start_index in range(0, len(words), step):
        chunk_words = words[start_index : start_index + chunk_size]

        if not chunk_words:
            break

        chunks.append(
            DocumentChunk(
                chunk_id=chunk_id,
                source=source,
                text=" ".join(chunk_words),
            )
        )
        chunk_id += 1

    return chunks


def chunk_documents(
    documents: list[dict],
    chunk_size: int = 120,
    chunk_overlap: int = 30,
) -> list[DocumentChunk]:
    chunks = []
    next_chunk_id = 1

    for document in documents:
        document_chunks = chunk_text(
            text=document["text"],
            source=document["source"],
            start_chunk_id=next_chunk_id,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        chunks.extend(document_chunks)
        next_chunk_id += len(document_chunks)

    return chunks
