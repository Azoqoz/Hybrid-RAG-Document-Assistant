import { useState, type RefObject } from "react";
import { RetrievalDisclosure } from "./RetrievalDisclosure";
import type { Evidence } from "./types";
import styles from "./rag-workspace.module.css";

type EvidenceStageProps = {
  evidence: Evidence;
  evidenceOptions: Evidence[];
  headingRef: RefObject<HTMLHeadingElement | null>;
  onSelectEvidence: (evidenceId: string, focusEvidence: boolean) => void;
  onClose: (restoreFocus: boolean) => void;
};

export function EvidenceStage({
  evidence,
  evidenceOptions,
  headingRef,
  onSelectEvidence,
  onClose,
}: EvidenceStageProps) {
  const [showContext, setShowContext] = useState(false);

  return (
    <section
      className={styles.evidenceStage}
      aria-labelledby="evidence-heading"
      data-evidence-id={evidence.id}
    >
      <header className={styles.evidenceStageHeader}>
        <div>
          <span className={styles.evidenceKicker}>Inspect evidence</span>
          <h3 id="evidence-heading" ref={headingRef} tabIndex={-1}>
            Evidence {evidence.displayId}
          </h3>
        </div>
        <button
          className={styles.closeEvidence}
          type="button"
          onClick={(event) => onClose(event.detail === 0)}
        >
          Close evidence <span aria-hidden="true">×</span>
        </button>
      </header>

      <div className={styles.evidenceLayout}>
        <aside className={styles.sourceIdentity} aria-label="Selected source">
          <h4>
            {evidence.filename} <span aria-hidden="true">·</span> {evidence.fileType}
          </h4>
          <p>
            Chunk {evidence.chunkId}
            {evidence.location ? ` · ${evidence.location}` : ""}
          </p>

          {evidenceOptions.length > 1 ? (
            <div className={styles.passageSwitcher} aria-label="Supporting passages">
              {evidenceOptions.map((option) => (
                <button
                  type="button"
                  key={option.id}
                  aria-pressed={option.id === evidence.id}
                  aria-label={`Show evidence ${option.displayId}`}
                  onClick={(event) => {
                    setShowContext(false);
                    onSelectEvidence(option.id, event.detail === 0);
                  }}
                >
                  {option.displayId}
                </button>
              ))}
            </div>
          ) : null}
        </aside>

        <div className={styles.passageColumn}>
          <blockquote className={styles.evidencePassage}>{evidence.snippet}</blockquote>

          {showContext && evidence.surroundingContext ? (
            <div className={styles.surroundingContext}>
              <span>Surrounding context</span>
              <p>{evidence.surroundingContext}</p>
            </div>
          ) : null}

          {evidence.surroundingContext ? (
            <button
              className={styles.contextAction}
              type="button"
              aria-expanded={showContext}
              onClick={() => setShowContext((current) => !current)}
            >
              {showContext ? "Hide surrounding context" : "Show surrounding context"}
              <span aria-hidden="true">{showContext ? "−" : "+"}</span>
            </button>
          ) : null}

          <RetrievalDisclosure key={evidence.id} retrieval={evidence.retrieval} />
        </div>
      </div>
    </section>
  );
}
