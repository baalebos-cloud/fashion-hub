export interface AISendMessagePayload {
  conversation_id: string | null;
  content: string;
}

export interface AISendMessageResponse {
  conversation_id: string;
  answer: string;
}

export interface AIConversationSummary {
  id: string;
  title: string | null;
  created_at: string;
}

/** Client-side chat turn — distinct from the wire payload above because it
 * carries local-only fields (id for React keys, optimistic pending state). */
export interface AIChatTurn {
  id: string;
  role: "user" | "assistant";
  content: string;
  pending?: boolean;
}
