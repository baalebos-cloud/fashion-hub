import { create } from "zustand";
import { aiApi } from "@/api/ai.api";
import type { AIChatTurn } from "@/types/ai";

interface AIState {
  isOpen: boolean;
  conversationId: string | null;
  turns: AIChatTurn[];
  isSending: boolean;
  error: string | null;
  pendingPrompt: string | null;

  open: () => void;
  close: () => void;
  toggle: () => void;
  /** Opens the panel AND immediately sends a prompt — this is what
   * AskSeamLink-style contextual triggers elsewhere in the app call, so
   * "Ask about this order" links can hand off straight into a question. */
  openWithPrompt: (prompt: string) => void;
  sendMessage: (content: string) => Promise<void>;
  reset: () => void;
}

/**
 * Deliberately a global store, not component-local `useState`: the
 * assistant's conversation must survive the panel being closed and
 * reopened from a completely different page (see components/ai/AIAssistant.tsx),
 * which is the whole point of it being "available throughout the
 * application rather than existing on one isolated page."
 */
export const useAIStore = create<AIState>((set, get) => ({
  isOpen: false,
  conversationId: null,
  turns: [],
  isSending: false,
  error: null,
  pendingPrompt: null,

  open: () => set({ isOpen: true }),
  close: () => set({ isOpen: false }),
  toggle: () => set({ isOpen: !get().isOpen }),

  openWithPrompt: (prompt) => set({ isOpen: true, pendingPrompt: prompt }),

  sendMessage: async (content) => {
    const trimmed = content.trim();
    if (!trimmed || get().isSending) return;

    set((state) => ({
      turns: [...state.turns, { id: `user-${Date.now()}`, role: "user", content: trimmed }],
      isSending: true,
      error: null,
      pendingPrompt: null,
    }));

    try {
      const result = await aiApi.sendMessage(get().conversationId, trimmed);
      set((state) => ({
        conversationId: result.conversation_id,
        turns: [...state.turns, { id: `assistant-${Date.now()}`, role: "assistant", content: result.answer }],
      }));
    } catch (err) {
      set({ error: err instanceof Error ? err.message : "Seam couldn't respond just now." });
    } finally {
      set({ isSending: false });
    }
  },

  reset: () => set({ conversationId: null, turns: [], error: null }),
}));
