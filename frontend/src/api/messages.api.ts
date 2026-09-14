import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { ChatMessage, Conversation } from "@/types/message";

export const messagesApi = {
  async listConversations(): Promise<Conversation[]> {
    const response = await apiClient.get<Conversation[]>(endpoints.messages.conversations);
    return response.data;
  },

  async listMessages(conversationId: string): Promise<ChatMessage[]> {
    const response = await apiClient.get<ChatMessage[]>(endpoints.messages.inConversation(conversationId));
    return response.data;
  },

  async send(conversationId: string, body: string): Promise<ChatMessage> {
    const response = await apiClient.post<ChatMessage>(endpoints.messages.inConversation(conversationId), { body });
    return response.data;
  },
};
