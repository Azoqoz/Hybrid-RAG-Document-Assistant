import { useState, type RefObject } from "react";
import { RetrievalDisclosure } from "./RetrievalDisclosure";
import type { Evidence } from "./types";
import styles from "./rag-workspace.module.css";

type EvidenceStageProps = {
  evidence: Evidence;
  evidenceOptions: Evidence[];
  headingRef: RefObject<HTMLHeadingElement | null>;
  onSelectEvidence: (evidenceId: string) => void;
  onClose: () => void;
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
            Evidence {evidence.id}
          </h3>
        </div>
        <button className={styles.closeEvidence} type="button" onClick={onClose}>
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
                  aria-label={`Show evidence ${option.id}`}
                  onClick={() => {
                    setShowContext(false);
                    onSelectEvidence(option.id);
                  }}
                >
                  {option.id}
                </button>
              ))}
            </div>
          ) : null}
        </aside>

        <div className={styles.passageColumn}>
          <blockquote className={styles.evidencePassage}>
            {evidence.passageLead}
            <mark>{evidence.passageHighlight}</mark>
            {evidence.passageTail}
          </blockquote>

          {showContext ? (
            <div className={styles.surroundingContext}>
              <span>Surrounding context</span>
              <p>{evidence.surroundingContext}</p>
            </div>
          ) : null}

          <button
            className={styles.contextAction}
            type="button"
            aria-expanded={showContext}
            onClick={() => setShowContext((current) => !current)}
          >
            {showContext ? "Hide surrounding context" : "Show surrounding context"}
            <span aria-hidden="true">{showContext ? "−" : "+"}</span>
          </button>

          <RetrievalDisclosure key={evidence.id} retrieval={evidence.retrieval} />
        </div>
      </div>
    </section>
  );
}
