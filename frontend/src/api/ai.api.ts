import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { AIConversationSummary, AISendMessageResponse } from "@/types/ai";

/**
 * The frontend contract for the global AI assistant (see
 * components/ai/AIAssistant.tsx). Matches
 * backend/app/api/v1/ai_navigation.py one-to-one.
 */
export const aiApi = {
  async sendMessage(conversationId: string | null, content: string): Promise<AISendMessageResponse> {
    const response = await apiClient.post<AISendMessageResponse>(endpoints.ai.sendMessage, {
      conversation_id: conversationId,
      content,
    });
    return response.data;
  },

  async listConversations(): Promise<AIConversationSummary[]> {
    const response = await apiClient.get<AIConversationSummary[]>(endpoints.ai.conversations);
    return response.data;
  },

  async sendFeedback(aiMessageId: string, wasHelpful: boolean): Promise<void> {
    await apiClient.post(endpoints.ai.feedback, { ai_message_id: aiMessageId, was_helpful: wasHelpful });
  },
};
