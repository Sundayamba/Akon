import { useEffect, useRef } from "react";
import type { FormEvent, KeyboardEvent } from "react";
import "./ChatComposer.css";

type ChatComposerProps = {
  value: string;
  isLoading: boolean;
  onChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onStop: () => void;
  onKeyDown: (event: KeyboardEvent<HTMLTextAreaElement>) => void;
};

const MAX_TEXTAREA_HEIGHT = 192;

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

        <div className="composer-footer">
          <span className="composer-helper">
            Enter to send · Shift + Enter for a new line
          </span>

          <div className="composer-actions">
            {isLoading && (
              <button
                className="stop-button"
                type="button"
                onClick={onStop}
              >
                Stop
              </button>
            )}

            <button disabled={isLoading || !hasText} type="submit">
              {isLoading ? "Sending..." : "Send"}
            </button>
          </div>
        </div>
      </div>
    </form>
  );
}

export default ChatComposer;