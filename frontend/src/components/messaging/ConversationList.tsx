import { cn } from "@/lib/utils/cn";
import { EmptyState } from "@/components/ui/empty-state";
import type { Conversation } from "@/types/message";

export function ConversationList({ conversations, activeId, onSelect }: { conversations: Conversation[]; activeId: string | null; onSelect: (id: string) => void }) {
  if (conversations.length === 0) {
    return <EmptyState title="No conversations yet" />;
  }

  return (
    <div className="flex flex-col">
      {conversations.map((conversation) => (
        <button
          key={conversation.id}
          onClick={() => onSelect(conversation.id)}
          className={cn("border-b border-line px-3 py-3 text-left text-sm last:border-0", activeId === conversation.id ? "bg-muslin" : "hover:bg-muslin/50")}
        >
          Conversation {conversation.id.slice(0, 8)}
        </button>
      ))}
    </div>
  );
}
