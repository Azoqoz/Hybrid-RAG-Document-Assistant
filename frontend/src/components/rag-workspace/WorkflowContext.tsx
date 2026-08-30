import type { WorkspaceMode } from "./types";
import styles from "./rag-workspace.module.css";

type WorkflowContextProps = {
  mode: WorkspaceMode;
  onModeChange: (mode: WorkspaceMode) => void;
};

export function WorkflowContext({ mode, onModeChange }: WorkflowContextProps) {
  return (
    <nav className={styles.workflowContext} aria-label="Primary workspace">
      <button
        className={mode === "documents" ? styles.workflowActive : undefined}
        type="button"
        aria-current={mode === "documents" ? "page" : undefined}
        onClick={() => onModeChange("documents")}
      >
        Documents
      </button>
      <span className={styles.workflowArrow} aria-hidden="true">→</span>
      <button
        className={mode === "ask" ? styles.workflowActive : undefined}
        type="button"
        aria-current={mode === "ask" ? "page" : undefined}
        onClick={() => onModeChange("ask")}
      >
        Ask documents
      </button>
    </nav>
  );
}
