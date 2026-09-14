import { cn } from "@/lib/utils/cn";
import type { AIChatTurn } from "@/types/ai";

export function AIMessage({ turn }: { turn: AIChatTurn }) {
  const isUser = turn.role === "user";

  return (
    <div className={cn("flex", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[82%] whitespace-pre-wrap break-words rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed",
          isUser
            ? "rounded-br-md bg-thread text-paper"
            : "rounded-bl-md border border-line bg-paper text-ink"
        )}
      >
        {turn.content}
      </div>
    </div>
  );
}
