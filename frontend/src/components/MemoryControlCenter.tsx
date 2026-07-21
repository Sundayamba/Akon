import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";

import {
  getMemoryHealth,
  getApiErrorMessage,
  previewMemoryRecall,
} from "../lib/api";
import type {
  MemoryHealth,
  MemoryItem,
  MemoryRecallPreview,
} from "../types";

type MemoryControlCenterProps = {
  token: string | null;
  memories: MemoryItem[];
  onError: (message: string) => void;
  onStatus: (message: string) => void;
  onRefresh: () => Promise<unknown>;
};

function formatMemoryType(memoryType: string): string {
  return memoryType.replace(/_/g, " ");
}

function MemoryControlCenter({
  token,
  memories,
  onError,
  onStatus,
  onRefresh,
}: MemoryControlCenterProps) {
  const [health, setHealth] = useState<MemoryHealth | null>(null);
  const [previewQuery, setPreviewQuery] = useState(
    "What do you remember about my current projects?",
  );
  const [preview, setPreview] = useState<MemoryRecallPreview | null>(null);
  const [isHealthLoading, setIsHealthLoading] = useState(false);
  const [isPreviewLoading, setIsPreviewLoading] = useState(false);

  const memoryFingerprint = useMemo(
    () =>
      memories
        .map(
          (memory) =>
            `${memory.id}:${memory.updated_at}:${memory.consent_state}:${memory.confidence}:${memory.sensitivity}`,
        )
        .join("|"),
    [memories],
  );

  const memoriesById = useMemo(
    () => new Map(memories.map((memory) => [memory.id, memory])),
    [memories],
  );

  const reviewMemories = useMemo(() => {
    if (!health) {
      return [];
    }

    return health.review_recommended_memory_ids
      .map((memoryId) => memoriesById.get(memoryId))
      .filter((memory): memory is MemoryItem => Boolean(memory));
  }, [health, memoriesById]);

  useEffect(() => {
    if (!token) {
      setHealth(null);
      return;
    }

    let isCurrent = true;

    async function loadHealth() {
      setIsHealthLoading(true);

      try {
        const authToken = token;

        if (!authToken) {
          return;
        }

        const result = await getMemoryHealth(authToken);

        if (isCurrent) {
          setHealth(result);
        }
      } catch (error) {
        if (isCurrent) {
          onError(getApiErrorMessage(error, "Could not load memory health."));
        }
      } finally {
        if (isCurrent) {
          setIsHealthLoading(false);
        }
      }
    }

    void loadHealth();

    return () => {
      isCurrent = false;
    };
  }, [token, memoryFingerprint, onError]);

  async function handlePreview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!token || !previewQuery.trim()) {
      return;
    }

    setIsPreviewLoading(true);
    setPreview(null);

    try {
      const result = await previewMemoryRecall(
        token,
        previewQuery.trim(),
        5,
      );

      setPreview(result);
      onStatus(
        result.matched_count
          ? `Recall preview found ${result.matched_count} relevant ${result.matched_count === 1 ? "memory" : "memories"}.`
          : "Recall preview found no relevant active memory.",
      );

      await onRefresh();
    } catch (error) {
      onError(getApiErrorMessage(error, "Could not preview memory recall."));
    } finally {
      setIsPreviewLoading(false);
    }
  }

  function handleReviewMemory(memoryId: string) {
    const target = document.getElementById(`memory-card-${memoryId}`);

    if (!target) {
      onStatus("Open Saved memory below to review this item.");
      return;
    }

    target.scrollIntoView({
      behavior: "smooth",
      block: "center",
    });

    target.classList.add("memory-review-focus");

    window.setTimeout(() => {
      target.classList.remove("memory-review-focus");
    }, 1800);
  }

  return (
    <section className="context-card memory-control-center">
      <div className="card-header">
        <p className="eyebrow">Memory intelligence</p>
        <h2>Control center</h2>
        <p>
          See the health of Akon's memory and preview what would be recalled
          before it influences a reply.
        </p>
      </div>

      <div className="memory-health-grid" aria-live="polite">
        <div>
          <strong>{health?.active_count ?? memories.length}</strong>
          <span>Active</span>
        </div>
        <div>
          <strong>{health?.explicit_count ?? 0}</strong>
          <span>Approved</span>
        </div>
        <div>
          <strong>{health?.review_recommended_count ?? 0}</strong>
          <span>Review</span>
        </div>
        <div>
          <strong>{health?.duplicate_group_count ?? 0}</strong>
          <span>Duplicates</span>
        </div>
      </div>

      <div className="memory-health-note">
        <span className={isHealthLoading ? "pulse-status" : ""}>
          {isHealthLoading ? "Checking memory health..." : "Consent-aware health scan"}
        </span>
        {health && (
          <small>
            {health.high_sensitivity_count} sensitive ·{" "}
            {health.low_confidence_count} low confidence ·{" "}
            {health.implicit_count} implicit consent
          </small>
        )}
      </div>

      {reviewMemories.length > 0 && (
        <div className="memory-review-queue">
          <div className="memory-control-subheader">
            <strong>Recommended review</strong>
            <span>{reviewMemories.length}</span>
          </div>

          {reviewMemories.slice(0, 3).map((memory) => (
            <button
              className="memory-review-item"
              key={memory.id}
              type="button"
              onClick={() => handleReviewMemory(memory.id)}
            >
              <span>{formatMemoryType(memory.memory_type)}</span>
              <p>{memory.content}</p>
              <small>
                {memory.consent_state} · {memory.confidence} confidence ·{" "}
                {memory.sensitivity} sensitivity
              </small>
            </button>
          ))}

          {reviewMemories.length > 3 && (
            <small className="memory-review-overflow">
              +{reviewMemories.length - 3} more in Saved memory
            </small>
          )}
        </div>
      )}

      <form className="memory-preview-form" onSubmit={handlePreview}>
        <label>
          Preview recall
          <textarea
            value={previewQuery}
            maxLength={2000}
            placeholder="Ask what Akon would remember about a topic..."
            onChange={(event) => setPreviewQuery(event.target.value)}
          />
        </label>

        <button
          disabled={isPreviewLoading || !previewQuery.trim()}
          type="submit"
        >
          {isPreviewLoading ? "Checking..." : "Preview matched memory"}
        </button>
      </form>

      {preview && (
        <div className="memory-preview-results">
          <div className="memory-control-subheader">
            <strong>Recall result</strong>
            <span>{preview.matched_count} matched</span>
          </div>

          {preview.matches.length === 0 ? (
            <p className="empty-state">
              No active memory met the relevance threshold.
            </p>
          ) : (
            preview.matches.map((match) => (
              <article
                className={
                  match.sensitivity === "high"
                    ? "memory-match-card sensitive"
                    : "memory-match-card"
                }
                key={match.id}
              >
                <div className="memory-match-header">
                  <strong>{formatMemoryType(match.memory_type)}</strong>
                  <span>Score {match.relevance_score}</span>
                </div>

                <p>{match.content}</p>

                <ul>
                  {match.reasons.map((reason) => (
                    <li key={reason}>{reason}</li>
                  ))}
                </ul>

                <small>
                  {match.consent_state} consent · {match.confidence} confidence ·{" "}
                  {match.sensitivity} sensitivity
                </small>
              </article>
            ))
          )}

          <p className="memory-privacy-note">{preview.privacy_note}</p>
        </div>
      )}
    </section>
  );
}

export default MemoryControlCenter;
