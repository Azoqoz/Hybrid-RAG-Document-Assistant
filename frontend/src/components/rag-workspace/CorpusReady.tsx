import styles from "./rag-workspace.module.css";

type CorpusReadyProps = {
  ready: boolean;
  isIndexing: boolean;
  unavailable: boolean;
  documentCount: number;
  chunkCount: number;
  onOpenAsk: () => void;
};

export function CorpusReady({
  ready,
  isIndexing,
  unavailable,
  documentCount,
  chunkCount,
  onOpenAsk,
}: CorpusReadyProps) {
  return (
    <section className={styles.corpusReady} aria-label="Corpus status">
      <p>
        <strong>
          {unavailable
            ? "Corpus unavailable"
            : isIndexing
              ? "Indexing corpus"
              : ready
                ? "Corpus ready"
                : "Corpus empty"}
        </strong>
        <span aria-hidden="true"> · </span>
        {documentCount} documents
        <span aria-hidden="true"> · </span>
        {chunkCount} chunks
      </p>
      <button type="button" onClick={onOpenAsk} disabled={!ready}>
        Ask this corpus <span aria-hidden="true">→</span>
      </button>
    </section>
  );
}
