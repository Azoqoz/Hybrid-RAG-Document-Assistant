import type {
  ApiCitation,
  ApiCorpus,
  ApiQueryResponse,
  ApiRetrievalResult,
} from "@/lib/rag-api";
import type {
  AnswerView,
  Evidence,
  RetrievalMetadata,
  SourceDocument,
} from "./types";

function fileType(filename: string, explicitType?: string): string {
  const type = explicitType || filename.split(".").pop() || "FILE";
  return type.replace(/^\./, "").toUpperCase();
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function sourceLetter(index: number): string {
  let value = index + 1;
  let label = "";
  while (value > 0) {
    value -= 1;
    label = String.fromCharCode(65 + (value % 26)) + label;
    value = Math.floor(value / 26);
  }
  return label;
}

function retrievalKey(filename: string, chunkId: number): string {
  return `${filename}\u0000${chunkId}`;
}

function definedNumber(value: number | null | undefined): number | undefined {
  return typeof value === "number" ? value : undefined;
}

function retrievalMetadata(
  citation: ApiCitation,
  result?: ApiRetrievalResult,
): RetrievalMetadata {
  return {
    semanticScore: definedNumber(citation.semantic_score ?? result?.semantic_score),
    bm25Score: definedNumber(citation.keyword_score ?? result?.keyword_score),
    hybridScore: definedNumber(citation.hybrid_score ?? result?.hybrid_score),
    rerankScore: definedNumber(citation.rerank_score ?? result?.rerank_score),
    rerankPosition: definedNumber(citation.rerank_position),
  };
}

function locationLabel(citation: ApiCitation): string | undefined {
  const parts: string[] = [];
  if (citation.page_number !== null) parts.push(`Page ${citation.page_number}`);
  if (citation.slide_number !== null) parts.push(`Slide ${citation.slide_number}`);
  return parts.length ? parts.join(" · ") : undefined;
}

export function corpusDocuments(corpus: ApiCorpus): SourceDocument[] {
  return corpus.documents.map((document, index) => ({
    id: `${document.filename}-${index}`,
    filename: document.filename,
    fileType: fileType(document.filename, document.file_type),
    extent: `${formatBytes(document.size_bytes)} · ${document.character_count.toLocaleString()} characters`,
    chunkCount: document.chunk_count,
    status: corpus.indexed ? "indexed" : "preparing",
  }));
}

export function pendingDocument(file: File, index: number): SourceDocument {
  return {
    id: `pending-${file.name}-${file.lastModified}-${index}`,
    filename: file.name,
    fileType: fileType(file.name),
    extent: formatBytes(file.size),
    chunkCount: 0,
    status: "indexing",
  };
}

export function answerView(response: ApiQueryResponse): AnswerView {
  const retrievalByChunk = new Map(
    response.retrieval_results.map((result) => [
      retrievalKey(result.filename, result.chunk_id),
      result,
    ]),
  );
  const sourceIndex = new Map<string, number>();
  const citationLabelById: Record<string, string> = {};
  const evidenceById: Record<string, Evidence> = {};

  response.citations.forEach((citation) => {
    if (!sourceIndex.has(citation.filename)) {
      sourceIndex.set(citation.filename, sourceIndex.size);
    }
    const sourceLabel = sourceLetter(sourceIndex.get(citation.filename) ?? 0);
    const displayId = `${sourceLabel}·${String(citation.chunk_id).padStart(2, "0")}`;
    const result = retrievalByChunk.get(
      retrievalKey(citation.filename, citation.chunk_id),
    );
    const fullText = result?.text.trim();
    const snippet = citation.snippet || citation.text_snippet;

    citationLabelById[citation.citation_id] = displayId;
    evidenceById[citation.citation_id] = {
      id: citation.citation_id,
      displayId,
      filename: citation.filename,
      fileType: fileType(citation.filename),
      chunkId: citation.chunk_id,
      location: locationLabel(citation),
      snippet,
      surroundingContext:
        fullText && fullText !== snippet.trim() ? fullText : undefined,
      retrieval: retrievalMetadata(citation, result),
    };
  });

  return {
    answer: response.answer,
    claims: response.claims.map((claim, index) => ({
      id: claim.claim_id,
      number: String(index + 1).padStart(2, "0"),
      text: claim.text,
      citationIds: claim.citation_ids.filter((id) => Boolean(evidenceById[id])),
      supportStatus: claim.support_status ?? undefined,
    })),
    evidenceById,
    citationLabelById,
  };
}

export function isSupportedDocument(file: File): boolean {
  return /\.(pdf|docx|pptx|txt)$/i.test(file.name);
}
