import type { MemoryRecallMatch } from "../types";

type UsedMemoryDisclosureProps = {
  memories: MemoryRecallMatch[];
};

function formatMemoryType(memoryType: string): string {
  return memoryType.replace(/_/g, " ");
}

function UsedMemoryDisclosure({
  memories,
}: UsedMemoryDisclosureProps) {
  if (memories.length === 0) {
    return null;
  }

  return (
    <details className="used-memory-disclosure">
      <summary>
        <span aria-hidden="true">◉</span>
        Akon used {memories.length} saved{" "}
        {memories.length === 1 ? "memory" : "memories"}
      </summary>

      <div className="used-memory-list">
        {memories.map((memory) => (
          <article
            className={
              memory.sensitivity === "high"
                ? "used-memory-item sensitive"
                : "used-memory-item"
            }
            key={memory.id}
          >
            <div>
              <strong>{formatMemoryType(memory.memory_type)}</strong>
              <span>Relevance {memory.relevance_score}</span>
            </div>

            <p>{memory.content}</p>

            <ul>
              {memory.reasons.map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </ul>

            <small>
              {memory.consent_state} consent · {memory.confidence} confidence ·{" "}
              {memory.sensitivity} sensitivity
            </small>
          </article>
        ))}
      </div>
    </details>
  );
}

export default UsedMemoryDisclosure;
