"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { DocumentsMode } from "./DocumentsMode";
import { GroundedAnswer } from "./GroundedAnswer";
import {
  claims,
  evidenceById,
  exampleQuestions,
  initialDocuments,
  initialQuestion,
} from "./mock-data";
import { ProductHeader } from "./ProductHeader";
import { QuestionComposer } from "./QuestionComposer";
import type { SourceDocument, WorkspaceMode } from "./types";
import { WorkflowContext } from "./WorkflowContext";
import styles from "./rag-workspace.module.css";

export function RagWorkspace() {
  const [mode, setMode] = useState<WorkspaceMode>("ask");
  const [documents, setDocuments] = useState<SourceDocument[]>(initialDocuments);
  const [question, setQuestion] = useState(initialQuestion);
  const [selectedClaimId, setSelectedClaimId] = useState("claim-02");
  const [selectedEvidenceId, setSelectedEvidenceId] = useState<string | undefined>("A·18");
  const [isGrounding, setIsGrounding] = useState(false);
  const evidenceHeadingRef = useRef<HTMLHeadingElement>(null);
  const returnFocusRef = useRef<HTMLButtonElement | null>(null);
  const shouldFocusEvidenceRef = useRef(false);

  const indexedCount = documents.filter((document) => document.status === "indexed").length;
  const chunkCount = documents.reduce((total, document) => total + document.chunkCount, 0);
  const selectedClaim = claims.find((claim) => claim.id === selectedClaimId) ?? claims[0];
  const selectedEvidence = selectedEvidenceId ? evidenceById[selectedEvidenceId] : undefined;
  const evidenceOptions = useMemo(
    () => selectedClaim.citationIds.map((id) => evidenceById[id]).filter(Boolean),
    [selectedClaim],
  );

  useEffect(() => {
    if (!shouldFocusEvidenceRef.current || !selectedEvidence) return;
    evidenceHeadingRef.current?.focus();
    shouldFocusEvidenceRef.current = false;
  }, [selectedEvidence]);

  function changeMode(nextMode: WorkspaceMode) {
    setMode(nextMode);
    if (nextMode === "documents") setSelectedEvidenceId(undefined);
  }

  function openEvidence(claimId: string, evidenceId: string, trigger: HTMLButtonElement) {
    returnFocusRef.current = trigger;
    setMode("ask");
    setSelectedClaimId(claimId);
    setSelectedEvidenceId(evidenceId);
    shouldFocusEvidenceRef.current = true;
  }

  function closeEvidence() {
    setSelectedEvidenceId(undefined);
    window.requestAnimationFrame(() => returnFocusRef.current?.focus());
  }

  function simulateIndexing() {
    setDocuments((current) =>
      current.map((document, index) =>
        index === current.length - 1
          ? { ...document, status: "indexing", progress: 64 }
          : document,
      ),
    );
    window.setTimeout(() => {
      setDocuments((current) =>
        current.map((document, index) =>
          index === current.length - 1 ? { ...document, progress: 84 } : document,
        ),
      );
    }, 500);
    window.setTimeout(() => {
      setDocuments((current) =>
        current.map((document, index) =>
          index === current.length - 1
            ? { ...document, status: "indexed", progress: 100 }
            : document,
        ),
      );
    }, 1200);
  }

  function groundAnswer() {
    if (!question.trim() || isGrounding) return;
    setIsGrounding(true);
    setSelectedEvidenceId(undefined);
    window.setTimeout(() => {
      setIsGrounding(false);
      setSelectedClaimId("claim-02");
    }, 900);
  }

  return (
    <div className={styles.workspaceShell}>
      <ProductHeader indexedCount={indexedCount} chunkCount={chunkCount} />
      <WorkflowContext
        mode={mode}
        onModeChange={changeMode}
      />

      <div className={styles.liveRegion} aria-live="polite" aria-atomic="true">
        {isGrounding ? "Grounding answer…" : `${indexedCount} documents indexed.`}
      </div>

      {mode === "documents" ? (
        <DocumentsMode
          documents={documents}
          onIndexDemo={simulateIndexing}
          onOpenAsk={() => changeMode("ask")}
        />
      ) : (
        <main id="workspace-main" className={styles.askMode}>
          <QuestionComposer
            question={question}
            examples={exampleQuestions}
            isGrounding={isGrounding}
            onQuestionChange={setQuestion}
            onSubmit={groundAnswer}
          />
          <GroundedAnswer
            claims={claims}
            selectedClaimId={selectedClaimId}
            selectedEvidence={selectedEvidence}
            evidenceOptions={evidenceOptions}
            evidenceHeadingRef={evidenceHeadingRef}
            onSelectClaim={(claimId) => {
              setSelectedClaimId(claimId);
              setSelectedEvidenceId(undefined);
            }}
            onSelectEvidence={openEvidence}
            onSwitchEvidence={(evidenceId) => {
              setSelectedEvidenceId(evidenceId);
              shouldFocusEvidenceRef.current = true;
            }}
            onCloseEvidence={closeEvidence}
          />
        </main>
      )}
    </div>
  );
}
