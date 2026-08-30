import type { KeyboardEvent, Ref } from "react";
import styles from "./rag-workspace.module.css";

type EvidenceFlagProps = {
  displayLabel: string;
  selected: boolean;
  buttonRef?: Ref<HTMLButtonElement>;
  onSelect: (trigger: HTMLButtonElement, focusEvidence: boolean) => void;
  onKeyDown?: (event: KeyboardEvent<HTMLButtonElement>) => void;
};

export function EvidenceFlag({
  displayLabel,
  selected,
  buttonRef,
  onSelect,
  onKeyDown,
}: EvidenceFlagProps) {
  return (
    <button
      className={selected ? styles.evidenceFlagSelected : styles.evidenceFlag}
      type="button"
      ref={buttonRef}
      aria-label={`Inspect evidence ${displayLabel}`}
      aria-pressed={selected}
      onClick={(event) => onSelect(event.currentTarget, event.detail === 0)}
      onKeyDown={onKeyDown}
    >
      {displayLabel}
    </button>
  );
}
