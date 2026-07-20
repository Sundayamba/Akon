import { useEffect, useRef } from "react";
import type { FormEvent, KeyboardEvent } from "react";
import "./ChatComposer.css";

type ChatComposerProps = {
  value: string;
  isLoading: boolean;
  activityLabel?: string | null;
  onChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onStop: () => void;
  onKeyDown: (event: KeyboardEvent<HTMLTextAreaElement>) => void;
};

const MAX_TEXTAREA_HEIGHT = 96;

function resizeTextarea(textarea: HTMLTextAreaElement | null): void {
  if (!textarea) {
    return;
  }

  textarea.style.height = "auto";
  textarea.style.height = `${Math.min(textarea.scrollHeight, MAX_TEXTAREA_HEIGHT)}px`;
}

function ChatComposer({
  value,
  isLoading,
  activityLabel,
  onChange,
  onSubmit,
  onStop,
  onKeyDown,
}: ChatComposerProps) {
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const hasText = value.trim().length > 0;

  useEffect(() => {
    resizeTextarea(textareaRef.current);
  }, [value]);

  return (
    <form className="chat-composer" onSubmit={onSubmit}>
      <div className="composer-input-shell">
        <textarea
          ref={textareaRef}
          value={value}
          rows={1}
          placeholder="Message Akon..."
          aria-label="Message Akon"
          disabled={isLoading}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={onKeyDown}
        />

        <button
          className="composer-send-button"
          aria-label="Send message"
          disabled={isLoading || !hasText}
          type="submit"
          title="Send"
        >
          {"\u2191"}
        </button>
      </div>

      {isLoading && (
        <div className="composer-meta-row">
          <span>{activityLabel || "Akon is responding"}...</span>

          <button className="composer-stop-button" type="button" onClick={onStop}>
            Stop
          </button>
        </div>
      )}
    </form>
  );
}

export default ChatComposer;