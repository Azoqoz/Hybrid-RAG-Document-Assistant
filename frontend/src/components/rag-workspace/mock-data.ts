import type { Claim, Evidence, SourceDocument } from "./types";

export const initialDocuments: SourceDocument[] = [
  {
    id: "source-a",
    filename: "hybrid-retrieval.pdf",
    fileType: "PDF",
    extent: "18 pages",
    chunkCount: 42,
    status: "indexed",
    progress: 100,
  },
  {
    id: "source-b",
    filename: "evaluation-notes.docx",
    fileType: "DOCX",
    extent: "9 sections",
    chunkCount: 19,
    status: "indexed",
    progress: 100,
  },
  {
    id: "source-c",
    filename: "lecture-07.pptx",
    fileType: "PPTX",
    extent: "31 slides",
    chunkCount: 31,
    status: "indexed",
    progress: 100,
  },
];

export const evidenceById: Record<string, Evidence> = {
  "A·18": {
    id: "A·18",
    sourceId: "source-a",
    filename: "hybrid-retrieval.pdf",
    fileType: "PDF",
    chunkId: 18,
    location: "Page 6",
    passageLead:
      "The retriever runs dense and lexical searches against the same chunk set. ",
    passageHighlight:
      "Normalized semantic and BM25 results are fused with weights of 0.65 and 0.35 before the cross-encoder evaluates the leading candidates.",
    passageTail:
      " This gives semantic similarity broader recall while preserving exact terminology that may be decisive for a technical question.",
    surroundingContext:
      "The candidate pool is intentionally wider than the final answer context. After fusion, the cross-encoder reads each question–passage pair and establishes the final ordering used for generation.",
    retrieval: {
      semanticScore: 0.91,
      bm25Score: 7.42,
      hybridScore: 0.86,
      rerankPosition: 1,
    },
  },
  "B·07": {
    id: "B·07",
    sourceId: "source-b",
    filename: "evaluation-notes.docx",
    fileType: "DOCX",
    chunkId: 7,
    passageLead:
      "Keyword retrieval remains useful when the prompt contains names, identifiers, or implementation language. ",
    passageHighlight:
      "BM25 contributes exact-token evidence that dense retrieval can underweight, then the weighted fusion retains candidates from both retrieval paths.",
    passageTail:
      " The resulting list is deliberately provisional until reranking.",
    surroundingContext:
      "Evaluation prompts containing model names and numeric parameters showed the clearest gains from the lexical branch. Pure semantic retrieval occasionally returned conceptually close passages without the requested value.",
    retrieval: {
      semanticScore: 0.72,
      bm25Score: 9.18,
      hybridScore: 0.79,
      rerankPosition: 3,
    },
  },
  "C·04": {
    id: "C·04",
    sourceId: "source-c",
    filename: "lecture-07.pptx",
    fileType: "PPTX",
    chunkId: 4,
    location: "Slide 12",
    passageLead:
      "Fusion produces candidates; it does not make the final relevance decision. ",
    passageHighlight:
      "A cross-encoder scores the complete question and passage together, allowing the final ranking to move a lower fused result above a superficially similar one.",
    passageTail:
      " Only the highest reranked passages are supplied to answer generation.",
    surroundingContext:
      "This second-stage model is more computationally expensive than embedding similarity, so it is applied to a restricted candidate set rather than the entire corpus.",
    retrieval: {
      semanticScore: 0.83,
      bm25Score: 5.63,
      hybridScore: 0.77,
      rerankPosition: 2,
    },
  },
};

export const claims: Claim[] = [
  {
    id: "claim-01",
    number: "01",
    text: "Semantic retrieval supplies broad conceptual recall, finding passages that match the meaning of the question even when the wording differs.",
    citationIds: ["A·18"],
    supportStatus: "Grounded",
  },
  {
    id: "claim-02",
    number: "02",
    text: "BM25 preserves exact technical language; its results are combined with semantic results at a 0.35 / 0.65 weighting before reranking.",
    citationIds: ["A·18", "B·07"],
    supportStatus: "Grounded",
  },
  {
    id: "claim-03",
    number: "03",
    text: "The cross-encoder then reads each question–passage pair and can reorder the fused candidates before the strongest evidence reaches answer generation.",
    citationIds: ["C·04"],
    supportStatus: "Grounded",
  },
];

export const exampleQuestions = [
  "Why combine semantic and keyword retrieval?",
  "How are candidates reranked?",
  "Summarize the evaluation findings.",
];

export const initialQuestion =
  "How does the system combine semantic and keyword retrieval before reranking?";
