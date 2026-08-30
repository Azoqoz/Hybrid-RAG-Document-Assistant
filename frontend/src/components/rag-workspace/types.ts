export type WorkspaceMode = "documents" | "ask";

export type DocumentStatus = "indexed" | "indexing";

export type SourceDocument = {
  id: string;
  filename: string;
  fileType: "PDF" | "DOCX" | "PPTX" | "TXT";
  extent?: string;
  chunkCount: number;
  status: DocumentStatus;
  progress: number;
};

export type RetrievalMetadata = {
  semanticScore: number;
  bm25Score: number;
  hybridScore: number;
  rerankPosition: number;
  rerankScore?: number;
};

export type Evidence = {
  id: string;
  sourceId: string;
  filename: string;
  fileType: SourceDocument["fileType"];
  chunkId: number;
  location?: string;
  passageLead: string;
  passageHighlight: string;
  passageTail: string;
  surroundingContext: string;
  retrieval: RetrievalMetadata;
};

export type Claim = {
  id: string;
  number: string;
  text: string;
  citationIds: string[];
  supportStatus: "Grounded" | "Qualified";
};
