import { Fragment, type RefObject } from "react";
import { ClaimRow } from "./ClaimRow";
import { EvidenceStage } from "./EvidenceStage";
import type { Claim, Evidence } from "./types";
import styles from "./rag-workspace.module.css";

type GroundedAnswerProps = {
  claims: Claim[];
  answer: string;
  citationLabelById: Record<string, string>;
  selectedClaimId: string;
  selectedEvidence?: Evidence;
  evidenceOptions: Evidence[];
  evidenceHeadingRef: RefObject<HTMLHeadingElement | null>;
  onSelectClaim: (claimId: string) => void;
  onSelectEvidence: (
    claimId: string,
    evidenceId: string,
    trigger: HTMLButtonElement,
    focusEvidence: boolean,
  ) => void;
  onSwitchEvidence: (evidenceId: string, focusEvidence: boolean) => void;
  onCloseEvidence: (restoreFocus: boolean) => void;
};

export function GroundedAnswer({
  claims,
  answer,
  citationLabelById,
  selectedClaimId,
  selectedEvidence,
  evidenceOptions,
  evidenceHeadingRef,
  onSelectClaim,
  onSelectEvidence,
  onSwitchEvidence,
  onCloseEvidence,
}: GroundedAnswerProps) {
  return (
    <section className={styles.answerSection} aria-labelledby="answer-heading">
      <header className={styles.answerHeader}>
        <h2 id="answer-heading">Grounded answer</h2>
      </header>

      {claims.length ? (
        <div className={styles.claimList}>
          {claims.map((claim) => (
            <Fragment key={claim.id}>
              <ClaimRow
                claim={claim}
                selected={claim.id === selectedClaimId}
                selectedEvidenceId={selectedEvidence?.id}
                citationLabelById={citationLabelById}
                onSelectClaim={() => onSelectClaim(claim.id)}
                onSelectEvidence={(evidenceId, trigger, focusEvidence) =>
                  onSelectEvidence(claim.id, evidenceId, trigger, focusEvidence)
                }
              />
              {claim.id === selectedClaimId && selectedEvidence ? (
                <EvidenceStage
                  evidence={selectedEvidence}
                  evidenceOptions={evidenceOptions}
                  headingRef={evidenceHeadingRef}
                  onSelectEvidence={onSwitchEvidence}
                  onClose={onCloseEvidence}
                />
              ) : null}
            </Fragment>
          ))}
        </div>
      ) : (
        <p className={styles.answerFallback}>{answer}</p>
      )}
    </section>
  );
}
