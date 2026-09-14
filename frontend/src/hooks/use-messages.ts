import { useEffect } from "react";
import { useMessagingStore } from "@/store/messaging.store";

export function useMessages() {
  const { conversations, activeConversationId, messages, isLoading, fetchConversations, openConversation, sendMessage } =
    useMessagingStore();

  useEffect(() => {
    fetchConversations();
  }, [fetchConversations]);

  return { conversations, activeConversationId, messages, isLoading, openConversation, sendMessage };
}
