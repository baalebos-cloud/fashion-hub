import { create } from "zustand";
import { messagesApi } from "@/api/messages.api";
import type { ChatMessage, Conversation } from "@/types/message";

interface MessagingState {
  conversations: Conversation[];
  activeConversationId: string | null;
  messages: ChatMessage[];
  isLoading: boolean;

  fetchConversations: () => Promise<void>;
  openConversation: (conversationId: string) => Promise<void>;
  sendMessage: (body: string) => Promise<void>;
}

export const useMessagingStore = create<MessagingState>((set, get) => ({
  conversations: [],
  activeConversationId: null,
  messages: [],
  isLoading: false,

  fetchConversations: async () => {
    set({ isLoading: true });
    try {
      const conversations = await messagesApi.listConversations();
      set({ conversations });
    } finally {
      set({ isLoading: false });
    }
  },

  openConversation: async (conversationId) => {
    set({ activeConversationId: conversationId, isLoading: true });
    try {
      const messages = await messagesApi.listMessages(conversationId);
      set({ messages });
    } finally {
      set({ isLoading: false });
    }
  },

  sendMessage: async (body) => {
    const conversationId = get().activeConversationId;
    if (!conversationId) return;
    const message = await messagesApi.send(conversationId, body);
    set({ messages: [...get().messages, message] });
  },
}));
