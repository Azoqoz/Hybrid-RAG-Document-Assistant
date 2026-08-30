import { CorpusReady } from "./CorpusReady";
import { DocumentSlab } from "./DocumentSlab";
import type { SourceDocument } from "./types";
import styles from "./rag-workspace.module.css";

type DocumentsModeProps = {
  documents: SourceDocument[];
  onIndexDemo: () => void;
  onOpenAsk: () => void;
};

export function DocumentsMode({
  documents,
  onIndexDemo,
  onOpenAsk,
}: DocumentsModeProps) {
  const chunkCount = documents.reduce((total, document) => total + document.chunkCount, 0);
  const isReady = documents.every((document) => document.status === "indexed");

  return (
    <main id="workspace-main" className={styles.documentsMode}>
      <section className={styles.documentsIntro}>
        <div>
          <h1>Build the evidence base.</h1>
          <p>Add source files, then ask across one indexed corpus.</p>
        </div>
        <button className={styles.addDocumentsButton} type="button" onClick={onIndexDemo}>
          <span aria-hidden="true">＋</span> Add documents
        </button>
      </section>

      <div className={styles.documentTray}>
        {documents.map((document, index) => (
          <DocumentSlab
            document={document}
            sourceLabel={String.fromCharCode(65 + index)}
            key={document.id}
          />
        ))}
      </div>

      <CorpusReady
        ready={isReady}
        documentCount={documents.length}
        chunkCount={chunkCount}
        onOpenAsk={onOpenAsk}
      />
    </main>
  );
}
