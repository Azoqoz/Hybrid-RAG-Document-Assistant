import type { KeyboardEvent, Ref } from "react";
import styles from "./rag-workspace.module.css";

type EvidenceFlagProps = {
  evidenceId: string;
  selected: boolean;
  buttonRef?: Ref<HTMLButtonElement>;
  onSelect: (trigger: HTMLButtonElement) => void;
  onKeyDown?: (event: KeyboardEvent<HTMLButtonElement>) => void;
};

export function EvidenceFlag({
  evidenceId,
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
      aria-label={`Inspect evidence ${evidenceId}`}
      aria-pressed={selected}
      onClick={(event) => onSelect(event.currentTarget)}
      onKeyDown={onKeyDown}
    >
      {evidenceId}
    </button>
  );
}
