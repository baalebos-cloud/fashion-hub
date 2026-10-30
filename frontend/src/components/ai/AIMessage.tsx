import { cn } from "@/lib/utils/cn";
import type { AIChatTurn } from "@/types/ai";
import type { ReactNode } from "react";

// Hide internal route strings in assistant prose, including parenthesized routes.
// Navigation labels remain visible; customer messages are not modified.
function cleanAssistantText(content: string): string {
  return content
    .replace(/\s*[（(][\s\u00a0\u202f]*\/app\/[^)）\r\n]*[)）]/g, "")
    .replace(/\/app\/[A-Za-z0-9_:/.-]+/g, "")
    .replace(/[ \t]{2,}/g, " ");
}

// Render a deliberately small Markdown subset as React text nodes, never HTML.
function formatInline(value: string): ReactNode[] {
  return value.split(/(\*\*[^*]+\*\*)/g).map((part, index) =>
    part.startsWith("**") && part.endsWith("**")
      ? <strong key={index} className="font-semibold">{part.slice(2, -2)}</strong>
      : part
  );
}

function AssistantBody({ content }: { content: string }) {
  const lines = content.split(/\r?\n/);
  const blocks: ReactNode[] = [];
  let list: { ordered: boolean; items: string[] } | null = null;

  function flushList(key: number) {
    if (!list) return;
    const items = list.items.map((item, index) => <li key={index}>{formatInline(item)}</li>);
    blocks.push(list.ordered
      ? <ol key={key} className="my-1 list-decimal space-y-1 pl-5">{items}</ol>
      : <ul key={key} className="my-1 list-disc space-y-1 pl-5">{items}</ul>);
    list = null;
  }

  lines.forEach((line, index) => {
    const trimmed = line.trim();
    const numbered = trimmed.match(/^\d+[.)]\s+(.+)$/);
    const bulleted = trimmed.match(/^[-*]\s+(.+)$/);
    if (numbered || bulleted) {
      const ordered = Boolean(numbered);
      if (list && list.ordered !== ordered) flushList(index);
      if (!list) list = { ordered, items: [] };
      list.items.push((numbered || bulleted)![1]);
    } else {
      flushList(index);
      if (trimmed.startsWith("|") && trimmed.endsWith("|")) {
        // Avoid displaying a raw Markdown table in a narrow chat bubble.
        const cells = trimmed.slice(1, -1).split("|").map((cell) => cell.trim());
        if (!cells.every((cell) => /^:?-{2,}:?$/.test(cell))) {
          blocks.push(<p key={index} className="my-1">{formatInline(cells.join(" · "))}</p>);
        }
      } else if (trimmed) {
        const value = trimmed.replace(/^#{1,3}\s+/, "");
        blocks.push(<p key={index} className="my-1">{formatInline(value)}</p>);
      }
    }
  });
  flushList(lines.length);
  return <div className="space-y-1.5">{blocks}</div>;
}

export function AIMessage({ turn }: { turn: AIChatTurn }) {
  const isUser = turn.role === "user";

  return (
    <div className={cn("flex", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[90%] break-words rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed",
          isUser
            ? "whitespace-pre-wrap rounded-br-md bg-thread text-paper"
            : "rounded-bl-md border border-line bg-paper text-ink"
        )}
      >
        {isUser ? turn.content : <AssistantBody content={cleanAssistantText(turn.content)} />}
      </div>
    </div>
  );
}
