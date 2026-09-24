import { useRef } from "react";
import type { ApiCapabilities } from "@/lib/rag-api";
import { CorpusReady } from "./CorpusReady";
import { DocumentSlab } from "./DocumentSlab";
import type { SourceDocument } from "./types";
import styles from "./rag-workspace.module.css";

type DocumentsModeProps = {
  demo?: ApiCapabilities;
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
  demo,
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
  const cannotUpload = isUploading || isConnecting || Boolean(connectionError) || Boolean(demo && documentCount);

  return (
    <main id="workspace-main" className={styles.documentsMode}>
      <section className={styles.documentsIntro}>
        <div>
          <h1>{demo ? "Try the guided RAG demo" : "Build the evidence base."}</h1>
          {demo ? (
            <>
              <ol className={styles.demoSteps}>
                <li>Download the sample document</li>
                <li>Upload it here</li>
                <li>Wait for indexing</li>
                <li>Test the guided questions</li>
              </ol>
              <a className={styles.demoDownload} href={demo.sample_download_path} download={demo.sample_filename}>Download sample PDF <span aria-hidden="true">↓</span></a>
              <p>Demo Mode accepts only this sample document.</p>
              <p>{demo.retention_information}</p>
            </>
          ) : <p>Add source files, then ask across one indexed corpus.</p>}
        </div>
        <button
          className={styles.addDocumentsButton}
          type="button"
          disabled={cannotUpload}
          onClick={() => fileInputRef.current?.click()}
        >
          <span aria-hidden="true">＋</span>
          {isUploading ? "Uploading, processing & indexing…" : demo ? "Upload sample document" : "Add documents"}
        </button>
        <input
          className={styles.fileInput}
          ref={fileInputRef}
          type="file"
          multiple={!demo}
          accept={demo ? ".pdf" : ".pdf,.docx,.pptx,.txt"}
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
            <span>{demo ? "Download the Northstar handbook above, then upload the same PDF." : "Supported files: PDF, DOCX, PPTX, and TXT."}</span>
          </div>
        )}
      </div>

      <CorpusReady
        ready={indexed && documentCount > 0 && (!demo || chunkCount > 0)}
        isIndexing={isUploading}
        unavailable={Boolean(connectionError)}
        documentCount={documentCount}
        chunkCount={chunkCount}
        onOpenAsk={onOpenAsk}
      />
    </main>
  );
}
