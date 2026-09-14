import { useAIStore } from "@/store/ai.store";

/**
 * The single hook every AI component (AIAssistant, AIChatWindow, AIInput,
 * AIQuickActions, AIHelpButton) reads from. Because it's backed by a
 * global Zustand store rather than component state, calling this hook
 * from two different places (e.g. the floating widget AND an inline
 * "Ask Seam" link on an order page) yields the same open/closed state and
 * the same conversation — which is what makes the assistant one continuous
 * experience rather than a new chat every time it's opened.
 */
export function useAI() {
  const isOpen = useAIStore((s) => s.isOpen);
  const turns = useAIStore((s) => s.turns);
  const isSending = useAIStore((s) => s.isSending);
  const error = useAIStore((s) => s.error);
  const pendingPrompt = useAIStore((s) => s.pendingPrompt);
  const open = useAIStore((s) => s.open);
  const close = useAIStore((s) => s.close);
  const toggle = useAIStore((s) => s.toggle);
  const openWithPrompt = useAIStore((s) => s.openWithPrompt);
  const sendMessage = useAIStore((s) => s.sendMessage);
  const reset = useAIStore((s) => s.reset);

  return { isOpen, turns, isSending, error, pendingPrompt, open, close, toggle, openWithPrompt, sendMessage, reset };
}
