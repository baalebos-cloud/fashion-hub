export interface ChatMessage {
  id: string;
  sender_user_id: string;
  body: string;
  is_read: boolean;
  created_at: string;
}

export interface Conversation {
  id: string;
  order_id?: string | null;
  status: "active" | "closed";
}
