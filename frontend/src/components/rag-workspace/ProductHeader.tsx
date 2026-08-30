import styles from "./rag-workspace.module.css";

type ProductHeaderProps = {
  indexedCount: number;
  chunkCount: number;
};

export function ProductHeader({ indexedCount, chunkCount }: ProductHeaderProps) {
  return (
    <header className={styles.productHeader}>
      <a className={styles.productIdentity} href="#workspace-main" aria-label="Hybrid RAG home">
        <span className={styles.productMark} aria-hidden="true">
          <span />
          <span />
          <span />
        </span>
        <span>
          <strong>Hybrid RAG</strong>
          <small>Document Assistant</small>
        </span>
      </a>

      <div className={styles.corpusContext} aria-label="Current corpus">
        <span className={styles.liveDot} aria-hidden="true" />
        <span>Current corpus</span>
        <strong>{indexedCount} indexed</strong>
        <span aria-hidden="true">·</span>
        <span>{chunkCount} chunks</span>
      </div>
    </header>
  );
}
