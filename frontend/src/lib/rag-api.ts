export type ApiDocumentMetadata = {
  filename: string;
  file_type: string;
  size_bytes: number;
  character_count: number;
  chunk_count: number;
};

export type ApiCorpus = {
  corpus_id: string;
  document_count: number;
  chunk_count: number;
  indexed: boolean;
  documents: ApiDocumentMetadata[];
};

export type ApiRetrievalResult = {
  filename: string;
  chunk_id: number;
  text: string;
  semantic_score: number | null;
  keyword_score: number | null;
  hybrid_score: number | null;
  rerank_score: number | null;
  page_number: number | null;
  slide_number: number | null;
};

export type ApiCitation = {
  citation_id: string;
  filename: string;
  chunk_id: number;
  snippet: string;
  text_snippet: string;
  semantic_score: number | null;
  keyword_score: number | null;
  hybrid_score: number | null;
  rerank_score: number | null;
  rerank_position: number | null;
  page_number: number | null;
  slide_number: number | null;
};

export type ApiClaim = {
  claim_id: string;
  text: string;
  citation_ids: string[];
  support_status: string | null;
};

export type ApiQueryResponse = {
  corpus_id: string;
  query: string;
  provider: string;
  is_summary: boolean;
  answer: string;
  claims: ApiClaim[];
  retrieval_results: ApiRetrievalResult[];
  citations: ApiCitation[];
};

type ApiErrorBody = {
  detail?: unknown;
};

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

export const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL?.trim() || DEFAULT_API_BASE_URL
).replace(/\/$/, "");

export class RagApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "RagApiError";
    this.status = status;
  }
}

function detailMessage(detail: unknown): string | undefined {
  if (typeof detail === "string") return detail;
  if (!Array.isArray(detail)) return undefined;

  const messages = detail
    .map((item) => {
      if (typeof item === "string") return item;
      if (item && typeof item === "object" && "msg" in item) {
        const message = (item as { msg?: unknown }).msg;
        return typeof message === "string" ? message : undefined;
      }
      return undefined;
    })
    .filter((message): message is string => Boolean(message));

  return messages.length ? messages.join(" ") : undefined;
}

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: {
        Accept: "application/json",
        ...init?.headers,
      },
    });
  } catch {
    throw new RagApiError(
      `Cannot reach the Hybrid RAG API at ${API_BASE_URL}.`,
      0,
    );
  }

  if (!response.ok) {
    let body: ApiErrorBody | undefined;
    try {
      body = (await response.json()) as ApiErrorBody;
    } catch {
      body = undefined;
    }
    throw new RagApiError(
      detailMessage(body?.detail) || `The API request failed (${response.status}).`,
      response.status,
    );
  }

  return (await response.json()) as T;
}

export function createCorpus(): Promise<ApiCorpus> {
  return apiRequest<ApiCorpus>("/corpora", { method: "POST" });
}

export function getCorpus(corpusId: string): Promise<ApiCorpus> {
  return apiRequest<ApiCorpus>(`/corpora/${encodeURIComponent(corpusId)}`);
}

export function uploadDocuments(corpusId: string, files: File[]): Promise<ApiCorpus> {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));

  return apiRequest<ApiCorpus>(
    `/corpora/${encodeURIComponent(corpusId)}/documents`,
    {
      method: "POST",
      body: formData,
    },
  );
}

export function queryCorpus(
  corpusId: string,
  query: string,
  provider: "none" | "openai" | "anthropic" | "gemini" = "none",
): Promise<ApiQueryResponse> {
  return apiRequest<ApiQueryResponse>(
    `/corpora/${encodeURIComponent(corpusId)}/query`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, provider }),
    },
  );
}

export function isCorpusNotFound(error: unknown): boolean {
  return error instanceof RagApiError && error.status === 404;
}

export function apiErrorMessage(error: unknown): string {
  if (error instanceof RagApiError) return error.message;
  return "An unexpected API error occurred.";
}
