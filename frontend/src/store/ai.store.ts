import { create } from "zustand";
import { aiApi } from "@/api/ai.api";
import { useAuthStore } from "@/store/auth.store";
import type { AIChatTurn } from "@/types/ai";

interface AIState {
  isOpen: boolean;
  conversationId: string | null;
  turns: AIChatTurn[];
  isSending: boolean;
  error: string | null;
  pendingPrompt: string | null;
  accountId: string | null;
  generation: number;

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
  accountId: null,
  generation: 0,

  open: () => set({ isOpen: true }),
  close: () => set({ isOpen: false }),
  toggle: () => set({ isOpen: !get().isOpen }),

  openWithPrompt: (prompt) => set({ isOpen: true, pendingPrompt: prompt }),

  sendMessage: async (content) => {
    const trimmed = content.trim();
    const accountId = useAuthStore.getState().user?.id ?? null;
    if (!accountId || !useAuthStore.getState().isAuthenticated || !trimmed || get().isSending) return;
    if (get().accountId !== accountId) get().reset();
    const generation = get().generation;
    set({ accountId });

    set((state) => ({
      turns: [...state.turns, { id: `user-${Date.now()}`, role: "user", content: trimmed }],
      isSending: true,
      error: null,
      pendingPrompt: null,
    }));

    try {
      const result = await aiApi.sendMessage(get().conversationId, trimmed);
      if (get().generation !== generation || useAuthStore.getState().user?.id !== accountId) return;
      set((state) => ({
        conversationId: result.conversation_id,
        turns: [...state.turns, { id: `assistant-${Date.now()}`, role: "assistant", content: result.answer }],
      }));
    } catch (err) {
      if (get().generation === generation && useAuthStore.getState().user?.id === accountId) {
        set({ error: err instanceof Error ? err.message : "Tailora couldn't respond just now." });
      }
    } finally {
      if (get().generation === generation) set({ isSending: false });
    }
  },

  reset: () => set((s) => ({ isOpen: false, conversationId: null, turns: [], error: null, pendingPrompt: null, isSending: false, accountId: null, generation: s.generation + 1 })),
}));

// Reset synchronously on identity changes, including logout and token restoration.
// In-flight replies are discarded by the generation check above.
useAuthStore.subscribe((state, previous) => {
  if ((state.user?.id ?? null) !== (previous.user?.id ?? null) ||
      (previous.isAuthenticated && !state.isAuthenticated)) {
    useAIStore.getState().reset();
  }
});
