import type { SourceDocument } from "./types";
import styles from "./rag-workspace.module.css";

type DocumentSlabProps = {
  document: SourceDocument;
  sourceLabel: string;
};

export function DocumentSlab({ document, sourceLabel }: DocumentSlabProps) {
  const isIndexed = document.status === "indexed";
  const isFailed = document.status === "failed";
  const statusLabel =
    document.status === "indexed"
      ? "Indexed"
      : document.status === "indexing"
        ? "Indexing"
        : document.status === "preparing"
          ? "Preparing"
          : "Failed";

  return (
    <article className={styles.documentSlab}>
      <div className={styles.fileEdge} aria-hidden="true">
        <span>{document.fileType}</span>
      </div>
      <div className={styles.documentBody}>
        <div className={styles.documentTopline}>
          <span>Source {sourceLabel}</span>
          <span
            className={
              isIndexed
                ? styles.indexedState
                : isFailed
                  ? styles.failedState
                  : styles.indexingState
            }
          >
            <span aria-hidden="true" />
            {statusLabel}
          </span>
        </div>
        <h3>{document.filename}</h3>
        <div className={styles.documentDetails}>
          {document.extent ? <span>{document.extent}</span> : null}
          <span>{document.chunkCount} chunks</span>
        </div>
      </div>
    </article>
  );
}
