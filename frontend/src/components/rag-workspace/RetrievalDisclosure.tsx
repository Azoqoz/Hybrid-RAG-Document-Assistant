import type { RetrievalMetadata } from "./types";
import styles from "./rag-workspace.module.css";

type RetrievalDisclosureProps = {
  retrieval: RetrievalMetadata;
};

export function RetrievalDisclosure({ retrieval }: RetrievalDisclosureProps) {
  const metrics = [
    ["Semantic score", retrieval.semanticScore],
    ["BM25 score", retrieval.bm25Score],
    ["Hybrid score", retrieval.hybridScore],
    ["Reranker score", retrieval.rerankScore],
  ] as const;
  const availableMetrics = metrics.flatMap(([label, value]) =>
    typeof value === "number" ? [{ label, value }] : [],
  );

  return (
    <details className={styles.retrievalDisclosure}>
      <summary>
        <span className={styles.retrievalSummary}>
          Retrieved by semantic + BM25 fusion
          {typeof retrieval.rerankPosition === "number"
            ? ` · reranked #${retrieval.rerankPosition}`
            : ""}
        </span>
        <span className={styles.retrievalPrompt}>Why this passage?</span>
      </summary>
      <div className={styles.retrievalDetails}>
        <p>
          These values are labeled independently because the retrieval methods do not
          share a guaranteed comparable scale.
        </p>
        <dl>
          {availableMetrics.map(({ label, value }) => (
            <div key={label}>
              <dt>{label}</dt>
              <dd>{value.toFixed(2)}</dd>
            </div>
          ))}
          {typeof retrieval.rerankPosition === "number" ? (
            <div>
              <dt>Rerank position</dt>
              <dd>#{retrieval.rerankPosition}</dd>
            </div>
          ) : null}
        </dl>
      </div>
    </details>
  );
}
