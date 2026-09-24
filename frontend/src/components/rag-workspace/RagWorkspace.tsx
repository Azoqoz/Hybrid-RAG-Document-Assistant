"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  apiErrorMessage,
  createCorpus,
  configureDemoSession,
  deleteCorpus,
  getCapabilities,
  getCorpus,
  isCorpusNotFound,
  queryCorpus,
  queryGuidedQuestion,
  RagApiError,
  uploadDocuments,
  type ApiCorpus,
  type ApiCapabilities,
} from "@/lib/rag-api";
import {
  answerView as createAnswerView,
  corpusDocuments,
  isSupportedDocument,
  pendingDocument,
} from "./adapters";
import { DocumentsMode } from "./DocumentsMode";
import { GroundedAnswer } from "./GroundedAnswer";
import { ProductHeader } from "./ProductHeader";
import { QuestionComposer } from "./QuestionComposer";
import { exampleQuestions } from "./suggestions";
import type { AnswerView, Evidence, SourceDocument, WorkspaceMode } from "./types";
import { WorkflowContext } from "./WorkflowContext";
import styles from "./rag-workspace.module.css";

type CorpusLoad = {
  corpus: ApiCorpus;
  recreated: boolean;
};

async function loadOrCreateCorpus(existingId?: string): Promise<CorpusLoad> {
  if (existingId) {
    try {
      return { corpus: await getCorpus(existingId), recreated: false };
    } catch (error) {
      if (!isCorpusNotFound(error)) throw error;
    }
  }

  const created = await createCorpus();
  return {
    corpus: await getCorpus(created.corpus_id),
    recreated: Boolean(existingId),
  };
}

async function uploadAndLoadCorpus(corpusId: string, files: File[]): Promise<ApiCorpus> {
  const uploaded = await uploadDocuments(corpusId, files);
  return getCorpus(uploaded.corpus_id);
}

export function RagWorkspace() {
  const [capabilities, setCapabilities] = useState<ApiCapabilities>();
  const demo = capabilities?.demo_mode_available ? capabilities : undefined;
  const [mode, setMode] = useState<WorkspaceMode>("documents");
  const [corpus, setCorpus] = useState<ApiCorpus | null>(null);
  const [isConnecting, setIsConnecting] = useState(true);
  const [connectionError, setConnectionError] = useState<string>();
  const [transientDocuments, setTransientDocuments] = useState<SourceDocument[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string>();
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<AnswerView | null>(null);
  const [queryError, setQueryError] = useState<string>();
  const [selectedClaimId, setSelectedClaimId] = useState<string>();
  const [selectedEvidenceId, setSelectedEvidenceId] = useState<string>();
  const [isGrounding, setIsGrounding] = useState(false);
  const evidenceHeadingRef = useRef<HTMLHeadingElement>(null);
  const returnFocusRef = useRef<HTMLButtonElement | null>(null);
  const shouldFocusEvidenceRef = useRef(false);
  const hasStartedRef = useRef(false);

  const clearAnswer = useCallback(() => {
    setAnswer(null);
    setSelectedClaimId(undefined);
    setSelectedEvidenceId(undefined);
  }, []);

  const connectCorpus = useCallback(
    async (existingId?: string) => {
      setIsConnecting(true);
      setConnectionError(undefined);
      try {
        const config = await getCapabilities();
        configureDemoSession(config.demo_mode_available);
        setCapabilities(config);
        const loaded = await loadOrCreateCorpus(existingId);
        setCorpus(loaded.corpus);
        if (loaded.recreated) {
          clearAnswer();
          setUploadError(
            "The previous corpus was no longer available. A new empty corpus was created.",
          );
          setMode("documents");
        }
      } catch (error) {
        setConnectionError(apiErrorMessage(error));
      } finally {
        setIsConnecting(false);
      }
    },
    [clearAnswer],
  );

  useEffect(() => {
    if (hasStartedRef.current) return;
    hasStartedRef.current = true;
    void connectCorpus();
  }, [connectCorpus]);

  const documents = useMemo(
    () => [...(corpus ? corpusDocuments(corpus) : []), ...transientDocuments],
    [corpus, transientDocuments],
  );
  const selectedClaim =
    answer?.claims.find((claim) => claim.id === selectedClaimId) ?? answer?.claims[0];
  const selectedEvidence =
    answer && selectedEvidenceId ? answer.evidenceById[selectedEvidenceId] : undefined;
  const evidenceOptions = useMemo(
    () =>
      selectedClaim && answer
        ? selectedClaim.citationIds
            .map((id) => answer.evidenceById[id])
            .filter((evidence): evidence is Evidence => Boolean(evidence))
        : [],
    [answer, selectedClaim],
  );

  useEffect(() => {
    if (!shouldFocusEvidenceRef.current || !selectedEvidence) return;
    evidenceHeadingRef.current?.focus();
    shouldFocusEvidenceRef.current = false;
  }, [selectedEvidence]);

  function changeMode(nextMode: WorkspaceMode) {
    setMode(nextMode);
    if (nextMode === "documents") {
      setSelectedEvidenceId(undefined);
      if (corpus) void connectCorpus(corpus.corpus_id);
    }
  }

  function openEvidence(
    claimId: string,
    evidenceId: string,
    trigger: HTMLButtonElement,
    focusEvidence: boolean,
  ) {
    returnFocusRef.current = trigger;
    setSelectedClaimId(claimId);
    setSelectedEvidenceId(evidenceId);
    shouldFocusEvidenceRef.current = focusEvidence;
  }

  function closeEvidence(restoreFocus: boolean) {
    setSelectedEvidenceId(undefined);
    if (restoreFocus) {
      window.requestAnimationFrame(() => returnFocusRef.current?.focus());
    }
  }

  async function handleFilesSelected(files: File[]) {
    setUploadError(undefined);
    if (demo && (files.length !== demo.allowed_document_count || files.some((file) => !/\.pdf$/i.test(file.name) || file.size > demo.max_upload_bytes))) {
      setUploadError(`Upload only the sample PDF (maximum ${demo.max_upload_bytes.toLocaleString()} bytes).`);
      return;
    }
    const supported = files.filter(isSupportedDocument);
    const unsupported = files.filter((file) => !isSupportedDocument(file));
    const unsupportedRows = unsupported.map((file, index) => ({
      ...pendingDocument(file, index),
      status: "failed" as const,
    }));
    const indexingRows = supported.map(pendingDocument);
    const unsupportedMessage = unsupported.length
      ? `Unsupported file${unsupported.length > 1 ? "s" : ""}: ${unsupported
          .map((file) => file.name)
          .join(", ")}. Use PDF, DOCX, PPTX, or TXT.`
      : undefined;

    setTransientDocuments([...unsupportedRows, ...indexingRows]);
    setUploadError(unsupportedMessage);
    if (!supported.length) return;

    setIsUploading(true);
    setConnectionError(undefined);
    try {
      let target = await loadOrCreateCorpus(corpus?.corpus_id);
      if (target.recreated) clearAnswer();

      let updated: ApiCorpus;
      try {
        updated = await uploadAndLoadCorpus(target.corpus.corpus_id, supported);
      } catch (error) {
        if (!isCorpusNotFound(error)) throw error;
        target = await loadOrCreateCorpus(target.corpus.corpus_id);
        clearAnswer();
        updated = await uploadAndLoadCorpus(target.corpus.corpus_id, supported);
      }

      setCorpus(updated);
      setTransientDocuments(unsupportedRows);
      clearAnswer();
    } catch (error) {
      setTransientDocuments([
        ...unsupportedRows,
        ...indexingRows.map((document) => ({ ...document, status: "failed" as const })),
      ]);
      const message = apiErrorMessage(error);
      if (error instanceof RagApiError && error.status === 0) {
        setConnectionError(message);
        setUploadError(unsupportedMessage);
      } else {
        setUploadError(unsupportedMessage ? `${unsupportedMessage} ${message}` : message);
      }
    } finally {
      setIsUploading(false);
    }
  }

  async function groundAnswer(questionId?: string) {
    if ((demo ? !questionId : !question.trim()) || isGrounding || isUploading) return;
    if (!corpus?.indexed || corpus.document_count === 0) {
      setQueryError("Add and index at least one document before asking a question.");
      return;
    }

    setIsGrounding(true);
    setQueryError(undefined);
    setSelectedEvidenceId(undefined);
    try {
      const response = demo && questionId
        ? await queryGuidedQuestion(corpus.corpus_id, questionId)
        : await queryCorpus(corpus.corpus_id, question, "none");
      const nextAnswer = createAnswerView(response);
      setAnswer(nextAnswer);
      setSelectedClaimId(nextAnswer.claims[0]?.id);
    } catch (error) {
      if (isCorpusNotFound(error)) {
        try {
          const loaded = await loadOrCreateCorpus(corpus.corpus_id);
          setCorpus(loaded.corpus);
          clearAnswer();
          setMode("documents");
          setUploadError(
            "The backend corpus was reset. A new empty corpus is ready for documents.",
          );
        } catch (recoveryError) {
          const message = apiErrorMessage(recoveryError);
          setQueryError(message);
          setConnectionError(message);
        }
      } else {
        const message = apiErrorMessage(error);
        if (error instanceof RagApiError && error.status === 0) {
          setConnectionError(message);
          setQueryError(undefined);
        } else {
          setQueryError(message);
        }
      }
    } finally {
      setIsGrounding(false);
    }
  }

  async function resetDemo() {
    if (!corpus || isUploading || isGrounding || isConnecting) return;
    setIsConnecting(true);
    setConnectionError(undefined);
    try {
      try {
        await deleteCorpus(corpus.corpus_id);
      } catch (error) {
        if (!isCorpusNotFound(error)) throw error;
      }
      setCorpus(null);
      clearAnswer();
      setTransientDocuments([]);
      setUploadError(undefined);
      setQueryError(undefined);
      setQuestion("");
      setMode("documents");
      await connectCorpus();
    } catch (error) {
      setConnectionError(apiErrorMessage(error));
    } finally {
      setIsConnecting(false);
    }
  }

  const indexedCount = corpus?.indexed ? corpus.document_count : 0;
  const chunkCount = corpus?.chunk_count ?? 0;
  const askDisabled =
    isConnecting || isUploading || Boolean(connectionError) || !corpus?.indexed || !corpus.document_count || Boolean(demo && !chunkCount);

  return (
    <div className={styles.workspaceShell}>
      <ProductHeader
        indexedCount={indexedCount}
        chunkCount={chunkCount}
        isConnecting={isConnecting}
        hasError={Boolean(connectionError)}
      />
      <WorkflowContext mode={mode} onModeChange={changeMode} />
      {demo ? (
        <div className={styles.demoNotice}>
          <span>Demo Mode · Real retrieval and reranking · No-key extractive answers</span>
          <button type="button" onClick={() => void resetDemo()} disabled={!corpus || isConnecting || isUploading || isGrounding}>Reset demo</button>
        </div>
      ) : null}

      <div className={styles.liveRegion} aria-live="polite" aria-atomic="true">
        {isConnecting
          ? "Connecting to the document corpus."
          : isUploading
            ? "Uploading, processing & indexing documents."
            : isGrounding
              ? "Grounding answer…"
              : connectionError || `${indexedCount} documents indexed.`}
      </div>

      {mode === "documents" ? (
        <DocumentsMode
          demo={demo}
          documents={documents}
          documentCount={corpus?.document_count ?? 0}
          chunkCount={chunkCount}
          indexed={Boolean(corpus?.indexed)}
          isUploading={isUploading}
          isConnecting={isConnecting}
          connectionError={connectionError}
          uploadError={uploadError}
          onFilesSelected={handleFilesSelected}
          onOpenAsk={() => setMode("ask")}
          onRetryConnection={() => void connectCorpus(corpus?.corpus_id)}
        />
      ) : (
        <main id="workspace-main" className={styles.askMode}>
          <QuestionComposer
            guidedQuestions={demo?.guided_questions}
            onGuidedQuestion={(id) => void groundAnswer(id)}
            question={question}
            examples={exampleQuestions}
            isGrounding={isGrounding}
            disabled={askDisabled}
            onQuestionChange={setQuestion}
            onSubmit={() => void groundAnswer()}
          />

          {connectionError ? (
            <div className={styles.inlineError} role="alert">
              <span>{connectionError}</span>
              <button type="button" onClick={() => void connectCorpus(corpus?.corpus_id)}>
                Retry connection
              </button>
            </div>
          ) : null}
          {queryError ? <p className={styles.inlineError} role="alert">{queryError}</p> : null}

          {answer ? (
            <GroundedAnswer
              answer={answer.answer}
              claims={answer.claims}
              citationLabelById={answer.citationLabelById}
              selectedClaimId={selectedClaimId ?? ""}
              selectedEvidence={selectedEvidence}
              evidenceOptions={evidenceOptions}
              evidenceHeadingRef={evidenceHeadingRef}
              onSelectClaim={(claimId) => {
                setSelectedClaimId(claimId);
                setSelectedEvidenceId(undefined);
              }}
              onSelectEvidence={openEvidence}
              onSwitchEvidence={(evidenceId, focusEvidence) => {
                setSelectedEvidenceId(evidenceId);
                shouldFocusEvidenceRef.current = focusEvidence;
              }}
              onCloseEvidence={closeEvidence}
            />
          ) : (
            <section className={styles.answerEmptyState} aria-label="Grounded answer">
              <span className={styles.eyebrow}>Grounded answer</span>
              <p>
                {corpus?.document_count
                  ? "Ask a question to create a grounded answer with inspectable evidence."
                  : "Add documents before asking your first question."}
              </p>
            </section>
          )}
        </main>
      )}
    </div>
  );
}
