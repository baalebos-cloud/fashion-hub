import { useCallback, useRef, useState } from "react";

/**
 * useSeamChat
 *
 * Talks to POST /api/v1/ai/navigation/messages (see
 * backend/app/api/v1/ai_navigation.py). Conversation state lives here, in
 * the client, but is backed by a real server-side conversation
 * (AIConversation/AIMessage) so history survives a page reload if you
 * later add GET /ai/navigation/conversations/{id}/messages hydration.
 */
export function useSeamChat({ apiBaseUrl, getAuthToken }) {
  const [messages, setMessages] = useState([]);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState(null);
  const conversationIdRef = useRef(null);

  const reset = useCallback(() => {
    setMessages([]);
    setError(null);
    conversationIdRef.current = null;
  }, []);

  const sendMessage = useCallback(
    async (content) => {
      const trimmed = content.trim();
      if (!trimmed || isSending) return;

      setError(null);
      setMessages((prev) => [...prev, { role: "user", content: trimmed, id: `local-${Date.now()}` }]);
      setIsSending(true);

      try {
        const token = typeof getAuthToken === "function" ? await getAuthToken() : null;

        const response = await fetch(`${apiBaseUrl}/ai/navigation/messages`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({
            conversation_id: conversationIdRef.current,
            content: trimmed,
          }),
        });

        if (!response.ok) {
          throw new Error(response.status === 401 ? "Please sign in to use the assistant." : "Seam couldn't respond just now.");
        }

        const data = await response.json();
        conversationIdRef.current = data.conversation_id;

        setMessages((prev) => [...prev, { role: "assistant", content: data.answer, id: `assistant-${Date.now()}` }]);
      } catch (err) {
        setError(err.message || "Something went wrong. Please try again.");
      } finally {
        setIsSending(false);
      }
    },
    [apiBaseUrl, getAuthToken, isSending]
  );

  return { messages, sendMessage, isSending, error, reset, conversationId: conversationIdRef.current };
}
