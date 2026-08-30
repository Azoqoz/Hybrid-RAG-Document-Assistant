import { Fragment, type RefObject } from "react";
import { ClaimRow } from "./ClaimRow";
import { EvidenceStage } from "./EvidenceStage";
import type { Claim, Evidence } from "./types";
import styles from "./rag-workspace.module.css";

type GroundedAnswerProps = {
  claims: Claim[];
  selectedClaimId: string;
  selectedEvidence?: Evidence;
  evidenceOptions: Evidence[];
  evidenceHeadingRef: RefObject<HTMLHeadingElement | null>;
  onSelectClaim: (claimId: string) => void;
  onSelectEvidence: (
    claimId: string,
    evidenceId: string,
    trigger: HTMLButtonElement,
  ) => void;
  onSwitchEvidence: (evidenceId: string) => void;
  onCloseEvidence: () => void;
};

export function GroundedAnswer({
  claims,
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
        <span className={styles.eyebrow}>Grounded answer</span>
        <h2 id="answer-heading">Hybrid retrieval balances meaning with exact language.</h2>
      </header>

      <div className={styles.claimList}>
        {claims.map((claim) => (
          <Fragment key={claim.id}>
            <ClaimRow
              claim={claim}
              selected={claim.id === selectedClaimId}
              selectedEvidenceId={selectedEvidence?.id}
              onSelectClaim={() => onSelectClaim(claim.id)}
              onSelectEvidence={(evidenceId, trigger) =>
                onSelectEvidence(claim.id, evidenceId, trigger)
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
    </section>
  );
}
