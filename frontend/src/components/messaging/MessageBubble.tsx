import { cn } from "@/lib/utils/cn";
import { DateTimeDisplay } from "@/components/common/DateTimeDisplay";
import type { ChatMessage } from "@/types/message";

export function MessageBubble({ message, isOwn }: { message: ChatMessage; isOwn: boolean }) {
  return (
    <div className={cn("flex", isOwn ? "justify-end" : "justify-start")}>
      <div className={cn("max-w-[75%] rounded-2xl px-3.5 py-2.5 text-sm", isOwn ? "rounded-br-md bg-ink text-paper" : "rounded-bl-md border border-line bg-paper text-ink")}>
        {message.body}
        <div className={cn("mt-1 text-[10px]", isOwn ? "text-paper/60" : "text-ink-soft/70")}>
          <DateTimeDisplay value={message.created_at} format="relative" />
        </div>
      </div>
    </div>
  );
}
