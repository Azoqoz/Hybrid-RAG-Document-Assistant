export type ApiDocumentMetadata = {
  filename: string;
  file_type: string;
  size_bytes: number;
  character_count: number;
  chunk_count: number;
};

export type GuidedQuestion = { id: string; title: string; question: string };
export type ApiCapabilities = {
  app_mode: "demo" | "local";
  demo_mode_available: boolean;
  sample_filename: string;
  sample_download_path: string;
  guided_questions: GuidedQuestion[];
  allowed_document_count: number;
  max_upload_bytes: number;
  max_queries_per_session: number;
  max_uploads_per_session: number;
  retention_seconds: number;
  retention_information: string;
  provider: "none";
  answer_generation: string;
  free_text_enabled: boolean;
};

let demoSessionId: string | undefined;

export function configureDemoSession(enabled: boolean): void {
  demoSessionId = undefined;
  if (!enabled) return;
  const key = "hybrid-rag-demo-session";
  const stored = sessionStorage.getItem(key);
  const valid = stored && /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(stored);
  demoSessionId = valid ? stored : crypto.randomUUID();
  sessionStorage.setItem(key, demoSessionId);
}

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
        ...(demoSessionId ? { "X-Demo-Session-ID": demoSessionId } : {}),
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

  return response.status === 204 ? (undefined as T) : (await response.json()) as T;
}

export function getCapabilities(): Promise<ApiCapabilities> {
  return apiRequest<ApiCapabilities>("/capabilities");
}

export function deleteCorpus(corpusId: string): Promise<void> {
  return apiRequest<void>(`/corpora/${encodeURIComponent(corpusId)}`, { method: "DELETE" });
}

export function queryGuidedQuestion(corpusId: string, questionId: string): Promise<ApiQueryResponse> {
  return apiRequest<ApiQueryResponse>(`/corpora/${encodeURIComponent(corpusId)}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question_id: questionId }),
  });
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
