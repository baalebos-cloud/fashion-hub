import { create } from "zustand";
import { messagesApi } from "@/api/messages.api";
import type { ChatMessage, Conversation } from "@/types/message";

interface MessagingState {
  conversations: Conversation[];
  activeConversationId: string | null;
  messages: ChatMessage[];
  isLoading: boolean;
  /** Bumped by reset(); replies that started before it are dropped. */
  generation: number;

  fetchConversations: () => Promise<void>;
  openConversation: (conversationId: string) => Promise<void>;
  sendMessage: (body: string) => Promise<void>;
  reset: () => void;
}

export const useMessagingStore = create<MessagingState>((set, get) => ({
  conversations: [],
  activeConversationId: null,
  messages: [],
  isLoading: false,
  generation: 0,

  fetchConversations: async () => {
    const generation = get().generation;
    set({ isLoading: true });
    try {
      const conversations = await messagesApi.listConversations();
      if (get().generation === generation) set({ conversations });
    } finally {
      if (get().generation === generation) set({ isLoading: false });
    }
  },

  openConversation: async (conversationId) => {
    const generation = get().generation;
    set({ activeConversationId: conversationId, isLoading: true });
    try {
      const messages = await messagesApi.listMessages(conversationId);
      if (get().generation === generation && get().activeConversationId === conversationId) set({ messages });
    } finally {
      if (get().generation === generation) set({ isLoading: false });
    }
  },

  sendMessage: async (body) => {
    const generation = get().generation;
    const conversationId = get().activeConversationId;
    if (!conversationId) return;
    const message = await messagesApi.send(conversationId, body);
    if (get().generation === generation && get().activeConversationId === conversationId) {
      set({ messages: [...get().messages, message] });
    }
  },

  reset: () => set((s) => ({
    conversations: [], activeConversationId: null, messages: [], isLoading: false, generation: s.generation + 1,
  })),
}));
