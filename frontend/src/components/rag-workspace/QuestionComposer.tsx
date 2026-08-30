import type { FormEvent } from "react";
import styles from "./rag-workspace.module.css";

type QuestionComposerProps = {
  question: string;
  examples: string[];
  isGrounding: boolean;
  disabled: boolean;
  onQuestionChange: (question: string) => void;
  onSubmit: () => void;
};

export function QuestionComposer({
  question,
  examples,
  isGrounding,
  disabled,
  onQuestionChange,
  onSubmit,
}: QuestionComposerProps) {
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit();
  }

  return (
    <section className={styles.composerSection} aria-labelledby="ask-heading">
      <div className={styles.composerHeading}>
        <div>
          <span className={styles.eyebrow}>Ask documents</span>
          <h1 id="ask-heading">Ask your documents.</h1>
        </div>
      </div>

      <form className={styles.composer} onSubmit={handleSubmit}>
        <label htmlFor="corpus-question">Ask across all indexed documents</label>
        <div className={styles.composerRow}>
          <textarea
            id="corpus-question"
            rows={2}
            value={question}
            onChange={(event) => onQuestionChange(event.target.value)}
          />
          <button type="submit" disabled={disabled || isGrounding || !question.trim()}>
            {isGrounding ? "Grounding answer…" : "Ground answer"}
            {!isGrounding ? <span aria-hidden="true">↗</span> : null}
          </button>
        </div>
      </form>

      <div className={styles.exampleQuestions} aria-label="Example questions">
        <span>Try</span>
        {examples.map((example) => (
          <button type="button" key={example} onClick={() => onQuestionChange(example)}>
            {example}
          </button>
        ))}
      </div>
    </section>
  );
}
