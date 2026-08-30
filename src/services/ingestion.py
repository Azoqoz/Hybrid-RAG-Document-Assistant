from pathlib import Path

from src.chunking import chunk_text
from src.document_loader import load_docx, load_pdf, load_pptx, load_txt
from src.services.contracts import (
    DocumentMetadata,
    IngestionBatch,
    UploadPayload,
)


class UnsupportedFileTypeError(ValueError):
    pass


class DocumentIngestionService:
    SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".txt"}
    CHUNK_SIZE = 120
    CHUNK_OVERLAP = 30

    def validate_file_type(self, filename: str) -> str:
        suffix = Path(filename).suffix.lower()
        if suffix not in self.SUPPORTED_EXTENSIONS:
            supported = ", ".join(sorted(self.SUPPORTED_EXTENSIONS))
            raise UnsupportedFileTypeError(
                f"Unsupported file type for '{filename}'. Supported types: {supported}."
            )
        return suffix

    def extract_text(self, upload: UploadPayload) -> tuple[str, str]:
        suffix = self.validate_file_type(upload.filename)
        loaders = {
            ".pdf": load_pdf,
            ".docx": load_docx,
            ".pptx": load_pptx,
            ".txt": load_txt,
        }
        return loaders[suffix](upload.content), suffix

    def ingest(
        self,
        uploads: list[UploadPayload],
        start_chunk_id: int = 1,
    ) -> IngestionBatch:
        documents = []
        chunks = []
        next_chunk_id = start_chunk_id

        for upload in uploads:
            text, suffix = self.extract_text(upload)
            document_chunks = chunk_text(
                text=text,
                source=upload.filename,
                start_chunk_id=next_chunk_id,
                chunk_size=self.CHUNK_SIZE,
                chunk_overlap=self.CHUNK_OVERLAP,
            )
            documents.append(
                DocumentMetadata(
                    filename=upload.filename,
                    file_type=suffix,
                    size_bytes=len(upload.content),
                    character_count=len(text),
                    chunk_count=len(document_chunks),
                )
            )
            chunks.extend(document_chunks)
            next_chunk_id += len(document_chunks)

        return IngestionBatch(documents=documents, chunks=chunks)
