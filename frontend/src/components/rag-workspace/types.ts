export type WorkspaceMode = "documents" | "ask";

export type DocumentStatus = "preparing" | "indexing" | "indexed" | "failed";

export type SourceDocument = {
  id: string;
  filename: string;
  fileType: string;
  extent?: string;
  chunkCount: number;
  status: DocumentStatus;
};

export type RetrievalMetadata = {
  semanticScore?: number;
  bm25Score?: number;
  hybridScore?: number;
  rerankPosition?: number;
  rerankScore?: number;
};

export type Evidence = {
  id: string;
  displayId: string;
  filename: string;
  fileType: string;
  chunkId: number;
  location?: string;
  snippet: string;
  surroundingContext?: string;
  retrieval: RetrievalMetadata;
};

export type Claim = {
  id: string;
  number: string;
  text: string;
  citationIds: string[];
  supportStatus?: string;
};

export type AnswerView = {
  answer: string;
  claims: Claim[];
  evidenceById: Record<string, Evidence>;
  citationLabelById: Record<string, string>;
};
