type MessageContentProps = {
  content: string;
};

type ContentBlock =
  | {
      type: "paragraph";
      lines: string[];
    }
  | {
      type: "code";
      language: string | null;
      lines: string[];
    }
  | {
      type: "bulletList";
      items: string[];
    }
  | {
      type: "numberedList";
      items: string[];
    };

function isCodeFence(line: string): boolean {
  return line.trim().startsWith("```");
}

function getCodeFenceLanguage(line: string): string | null {
  const language = line.trim().replace(/^```/, "").trim();

  return language || null;
}

function isBulletLine(line: string): boolean {
  return /^[-*]\s+/.test(line.trim());
}

function isNumberedLine(line: string): boolean {
  return /^\d+[.)]\s+/.test(line.trim());
}

function cleanBulletLine(line: string): string {
  return line.trim().replace(/^[-*]\s+/, "");
}

function cleanNumberedLine(line: string): string {
  return line.trim().replace(/^\d+[.)]\s+/, "");
}

function parseContent(content: string): ContentBlock[] {
  const lines = content.replace(/\r\n/g, "\n").split("\n");
  const blocks: ContentBlock[] = [];

  let index = 0;

  while (index < lines.length) {
    const currentLine = lines[index];

    if (!currentLine.trim()) {
      index += 1;
      continue;
    }

    if (isCodeFence(currentLine)) {
      const language = getCodeFenceLanguage(currentLine);
      const codeLines: string[] = [];
      index += 1;

      while (index < lines.length && !isCodeFence(lines[index])) {
        codeLines.push(lines[index]);
        index += 1;
      }

      if (index < lines.length && isCodeFence(lines[index])) {
        index += 1;
      }

      blocks.push({
        type: "code",
        language,
        lines: codeLines,
      });

      continue;
    }

    if (isBulletLine(currentLine)) {
      const items: string[] = [];

      while (index < lines.length && isBulletLine(lines[index])) {
        items.push(cleanBulletLine(lines[index]));
        index += 1;
      }

      blocks.push({
        type: "bulletList",
        items,
      });

      continue;
    }

    if (isNumberedLine(currentLine)) {
      const items: string[] = [];

      while (index < lines.length && isNumberedLine(lines[index])) {
        items.push(cleanNumberedLine(lines[index]));
        index += 1;
      }

      blocks.push({
        type: "numberedList",
        items,
      });

      continue;
    }

    const paragraphLines: string[] = [];

    while (
      index < lines.length &&
      lines[index].trim() &&
      !isCodeFence(lines[index]) &&
      !isBulletLine(lines[index]) &&
      !isNumberedLine(lines[index])
    ) {
      paragraphLines.push(lines[index]);
      index += 1;
    }

    blocks.push({
      type: "paragraph",
      lines: paragraphLines,
    });
  }

  return blocks;
}

function renderInlineText(text: string) {
  const parts = text.split(/(`[^`]+`)/g);

  return parts.map((part, index) => {
    if (part.startsWith("`") && part.endsWith("`") && part.length > 2) {
      return <code key={`${part}-${index}`}>{part.slice(1, -1)}</code>;
    }

    return <span key={`${part}-${index}`}>{part}</span>;
  });
}

function MessageContent({ content }: MessageContentProps) {
  const blocks = parseContent(content);

  if (blocks.length === 0) {
    return <p className="message-paragraph">No content.</p>;
  }

  return (
    <div className="message-content">
      {blocks.map((block, index) => {
        if (block.type === "code") {
          return (
            <div className="message-code-block" key={`code-${index}`}>
              {block.language && <span>{block.language}</span>}
              <pre>
                <code>{block.lines.join("\n")}</code>
              </pre>
            </div>
          );
        }

        if (block.type === "bulletList") {
          return (
            <ul className="message-list-block" key={`bullet-${index}`}>
              {block.items.map((item, itemIndex) => (
                <li key={`${item}-${itemIndex}`}>{renderInlineText(item)}</li>
              ))}
            </ul>
          );
        }

        if (block.type === "numberedList") {
          return (
            <ol className="message-list-block" key={`numbered-${index}`}>
              {block.items.map((item, itemIndex) => (
                <li key={`${item}-${itemIndex}`}>{renderInlineText(item)}</li>
              ))}
            </ol>
          );
        }

        return (
          <p className="message-paragraph" key={`paragraph-${index}`}>
            {renderInlineText(block.lines.join(" "))}
          </p>
        );
      })}
    </div>
  );
}

export default MessageContent;