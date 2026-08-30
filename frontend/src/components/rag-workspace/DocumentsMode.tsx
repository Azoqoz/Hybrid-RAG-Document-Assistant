import { useRef } from "react";
import { CorpusReady } from "./CorpusReady";
import { DocumentSlab } from "./DocumentSlab";
import type { SourceDocument } from "./types";
import styles from "./rag-workspace.module.css";

type DocumentsModeProps = {
  documents: SourceDocument[];
  documentCount: number;
  chunkCount: number;
  indexed: boolean;
  isUploading: boolean;
  isConnecting: boolean;
  connectionError?: string;
  uploadError?: string;
  onFilesSelected: (files: File[]) => void;
  onOpenAsk: () => void;
  onRetryConnection: () => void;
};

export function DocumentsMode({
  documents,
  documentCount,
  chunkCount,
  indexed,
  isUploading,
  isConnecting,
  connectionError,
  uploadError,
  onFilesSelected,
  onOpenAsk,
  onRetryConnection,
}: DocumentsModeProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cannotUpload = isUploading || isConnecting || Boolean(connectionError);

  return (
    <main id="workspace-main" className={styles.documentsMode}>
      <section className={styles.documentsIntro}>
        <div>
          <h1>Build the evidence base.</h1>
          <p>Add source files, then ask across one indexed corpus.</p>
        </div>
        <button
          className={styles.addDocumentsButton}
          type="button"
          disabled={cannotUpload}
          onClick={() => fileInputRef.current?.click()}
        >
          <span aria-hidden="true">＋</span>
          {isUploading ? "Indexing…" : "Add documents"}
        </button>
        <input
          className={styles.fileInput}
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.docx,.pptx,.txt"
          disabled={cannotUpload}
          onChange={(event) => {
            const files = Array.from(event.target.files ?? []);
            event.target.value = "";
            if (files.length) onFilesSelected(files);
          }}
        />
      </section>

      {connectionError ? (
        <div className={styles.inlineError} role="alert">
          <span>{connectionError}</span>
          <button type="button" onClick={onRetryConnection}>Retry connection</button>
        </div>
      ) : null}
      {uploadError ? <p className={styles.inlineError} role="alert">{uploadError}</p> : null}

      <div className={styles.documentTray}>
        {documents.length ? (
          documents.map((document, index) => (
            <DocumentSlab
              document={document}
              sourceLabel={String.fromCharCode(65 + (index % 26))}
              key={document.id}
            />
          ))
        ) : (
          <div className={styles.emptyDocuments}>
            <strong>{isConnecting ? "Preparing a corpus…" : "No documents yet."}</strong>
            <span>Supported files: PDF, DOCX, PPTX, and TXT.</span>
          </div>
        )}
      </div>

      <CorpusReady
        ready={indexed && documentCount > 0}
        isIndexing={isUploading}
        unavailable={Boolean(connectionError)}
        documentCount={documentCount}
        chunkCount={chunkCount}
        onOpenAsk={onOpenAsk}
      />
    </main>
  );
}
