import type { SourceDocument } from "./types";
import styles from "./rag-workspace.module.css";

type DocumentSlabProps = {
  document: SourceDocument;
  sourceLabel: string;
};

export function DocumentSlab({ document, sourceLabel }: DocumentSlabProps) {
  const isIndexed = document.status === "indexed";

  return (
    <article className={styles.documentSlab}>
      <div className={styles.fileEdge} aria-hidden="true">
        <span>{document.fileType}</span>
      </div>
      <div className={styles.documentBody}>
        <div className={styles.documentTopline}>
          <span>Source {sourceLabel}</span>
          <span className={isIndexed ? styles.indexedState : styles.indexingState}>
            <span aria-hidden="true" />
            {isIndexed ? "Indexed" : `Indexing ${document.progress}%`}
          </span>
        </div>
        <h3>{document.filename}</h3>
        <div className={styles.documentDetails}>
          {document.extent ? <span>{document.extent}</span> : null}
          <span>{document.chunkCount} chunks</span>
        </div>
        {!isIndexed ? (
          <div
            className={styles.indexProgress}
            role="progressbar"
            aria-label={`Indexing ${document.filename}`}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={document.progress}
          >
            <span style={{ width: `${document.progress}%` }} />
          </div>
        ) : null}
      </div>
    </article>
  );
}
