import { useRef } from "react";
import { EvidenceFlag } from "./EvidenceFlag";
import type { Claim } from "./types";
import styles from "./rag-workspace.module.css";

type ClaimRowProps = {
  claim: Claim;
  selected: boolean;
  selectedEvidenceId?: string;
  citationLabelById: Record<string, string>;
  onSelectClaim: () => void;
  onSelectEvidence: (
    evidenceId: string,
    trigger: HTMLButtonElement,
    focusEvidence: boolean,
  ) => void;
};

export function ClaimRow({
  claim,
  selected,
  selectedEvidenceId,
  citationLabelById,
  onSelectClaim,
  onSelectEvidence,
}: ClaimRowProps) {
  const flagRefs = useRef<Array<HTMLButtonElement | null>>([]);

  return (
    <article className={selected ? styles.claimSelected : styles.claimRow}>
      <span className={styles.claimNumber}>{claim.number}</span>
      <div className={styles.claimBody}>
        <button
          className={styles.claimText}
          type="button"
          aria-pressed={selected}
          onClick={onSelectClaim}
        >
          {claim.text}
        </button>
        <div className={styles.claimCitations}>
          <div className={styles.flagGroup} aria-label={`Evidence for claim ${claim.number}`}>
            {claim.citationIds.map((evidenceId, index) => (
              <EvidenceFlag
                key={evidenceId}
                displayLabel={citationLabelById[evidenceId] ?? evidenceId}
                selected={selected && selectedEvidenceId === evidenceId}
                buttonRef={(node) => {
                  flagRefs.current[index] = node;
                }}
                onSelect={(trigger, focusEvidence) =>
                  onSelectEvidence(evidenceId, trigger, focusEvidence)
                }
                onKeyDown={(event) => {
                  if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
                  event.preventDefault();
                  const direction = event.key === "ArrowRight" ? 1 : -1;
                  const next = (index + direction + claim.citationIds.length) % claim.citationIds.length;
                  flagRefs.current[next]?.focus();
                }}
              />
            ))}
          </div>
        </div>
      </div>
    </article>
  );
}
