import styles from "./rag-workspace.module.css";

type CorpusReadyProps = {
  ready: boolean;
  documentCount: number;
  chunkCount: number;
  onOpenAsk: () => void;
};

export function CorpusReady({
  ready,
  documentCount,
  chunkCount,
  onOpenAsk,
}: CorpusReadyProps) {
  return (
    <section className={styles.corpusReady} aria-label="Corpus status">
      <p>
        <strong>{ready ? "Corpus ready" : "Indexing corpus"}</strong>
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
