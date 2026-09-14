import { useEffect, useRef } from "react";
import { useMessages } from "@/hooks/use-messages";
import { useAuth } from "@/hooks/use-auth";
import { ConversationList } from "./ConversationList";
import { MessageBubble } from "./MessageBubble";
import { MessageInput } from "./MessageInput";
import { EmptyState } from "@/components/ui/empty-state";

export function ChatWindow() {
  const { user } = useAuth();
  const { conversations, activeConversationId, messages, openConversation, sendMessage } = useMessages();
  const threadRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    threadRef.current?.scrollTo({ top: threadRef.current.scrollHeight });
  }, [messages]);

  return (
    <div className="flex h-[560px] overflow-hidden rounded-card border border-line">
      <div className="w-56 flex-shrink-0 overflow-y-auto border-r border-line">
        <ConversationList conversations={conversations} activeId={activeConversationId} onSelect={openConversation} />
      </div>
      <div className="flex flex-1 flex-col">
        {!activeConversationId ? (
          <EmptyState title="Select a conversation" />
        ) : (
          <>
            <div ref={threadRef} className="flex flex-1 flex-col gap-2 overflow-y-auto p-4">
              {messages.map((message) => (
                <MessageBubble key={message.id} message={message} isOwn={message.sender_user_id === user?.id} />
              ))}
            </div>
            <MessageInput onSend={sendMessage} />
          </>
        )}
      </div>
    </div>
  );
}
