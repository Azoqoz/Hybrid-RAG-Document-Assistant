import type { RetrievalMetadata } from "./types";
import styles from "./rag-workspace.module.css";

type RetrievalDisclosureProps = {
  retrieval: RetrievalMetadata;
};

export function RetrievalDisclosure({ retrieval }: RetrievalDisclosureProps) {
  return (
    <details className={styles.retrievalDisclosure}>
      <summary>
        <span className={styles.retrievalSummary}>
          Retrieved by semantic + BM25 fusion · reranked #{retrieval.rerankPosition}
        </span>
        <span className={styles.retrievalPrompt}>Why this passage?</span>
      </summary>
      <div className={styles.retrievalDetails}>
        <p>
          These values are labeled independently because the retrieval methods do not
          share a guaranteed comparable scale.
        </p>
        <dl>
          <div>
            <dt>Semantic score</dt>
            <dd>{retrieval.semanticScore.toFixed(2)}</dd>
          </div>
          <div>
            <dt>BM25 score</dt>
            <dd>{retrieval.bm25Score.toFixed(2)}</dd>
          </div>
          <div>
            <dt>Hybrid score</dt>
            <dd>{retrieval.hybridScore.toFixed(2)}</dd>
          </div>
          <div>
            <dt>Rerank position</dt>
            <dd>#{retrieval.rerankPosition}</dd>
          </div>
          {typeof retrieval.rerankScore === "number" ? (
            <div>
              <dt>Reranker score</dt>
              <dd>{retrieval.rerankScore.toFixed(2)}</dd>
            </div>
          ) : null}
        </dl>
      </div>
    </details>
  );
}
