import { createContext, useCallback, useContext, useMemo, useState } from "react";

/**
 * SeamAssistantContext
 *
 * Makes the assistant a property of the whole application shell, not a
 * single page. Mount <SeamAssistantProvider> once at the root layout
 * (wrapping the router), and any component anywhere in the tree can call
 * useSeamAssistant() to open the panel — pre-filled with a question, if
 * useful — without knowing anything about how the widget itself renders.
 *
 * Example: a "Need help with this order?" link on the order-detail page
 *   const { openWithPrompt } = useSeamAssistant();
 *   <button onClick={() => openWithPrompt("How do I track this order?")}>
 *     Ask Seam
 *   </button>
 */

const SeamAssistantContext = createContext(null);

// Static, per-role suggestions shown on first open. Keep this list in sync
// with the backend's ROLE_APP_MAP (app/integrations/ai/navigation_agent.py)
// so the assistant never suggests a question about a page the user's role
// can't reach.
const ROLE_QUICK_PROMPTS = {
  customer: ["Where can I track my order?", "How do I find a tailor near me?", "Where is my invoice?"],
  tailor: ["How do I accept an order?", "Where do I buy materials from a vendor?", "How does verification work?"],
  designer: ["How do I upload my portfolio?", "Where do I manage incoming orders?"],
  vendor: ["How do I add a new product?", "Where do I see incoming orders?"],
  delivery_partner: ["How do I accept a delivery request?", "Where do I update my availability?"],
};

export function SeamAssistantProvider({
  children,
  role = "customer",
  userName,
  apiBaseUrl = "/api/v1",
  getAuthToken,
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [pendingPrompt, setPendingPrompt] = useState(null);

  const open = useCallback(() => setIsOpen(true), []);
  const close = useCallback(() => setIsOpen(false), []);
  const toggle = useCallback(() => setIsOpen((prev) => !prev), []);

  const openWithPrompt = useCallback((prompt) => {
    setPendingPrompt(prompt);
    setIsOpen(true);
  }, []);

  const consumePendingPrompt = useCallback(() => {
    setPendingPrompt(null);
  }, []);

  const value = useMemo(
    () => ({
      isOpen,
      open,
      close,
      toggle,
      openWithPrompt,
      pendingPrompt,
      consumePendingPrompt,
      role,
      userName,
      apiBaseUrl,
      getAuthToken,
      quickPrompts: ROLE_QUICK_PROMPTS[role] ?? ROLE_QUICK_PROMPTS.customer,
    }),
    [isOpen, open, close, toggle, openWithPrompt, pendingPrompt, consumePendingPrompt, role, userName, apiBaseUrl, getAuthToken]
  );

  return <SeamAssistantContext.Provider value={value}>{children}</SeamAssistantContext.Provider>;
}

export function useSeamAssistant() {
  const ctx = useContext(SeamAssistantContext);
  if (!ctx) {
    throw new Error("useSeamAssistant must be used within a <SeamAssistantProvider>.");
  }
  return ctx;
}
