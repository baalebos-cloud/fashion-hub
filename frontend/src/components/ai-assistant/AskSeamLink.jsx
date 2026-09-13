import "./seam-assistant.css";
import { useSeamAssistant } from "./SeamAssistantContext";

/**
 * A contextual entry point into the same global assistant — this is what
 * keeps Seam from being "one isolated page." Drop this anywhere a person
 * might want help right where they are, pre-filled with the relevant
 * question, e.g. on an order's tracking section:
 *
 *   <AskSeamLink prompt="Why hasn't my order moved from Shipped?">
 *     Ask Seam about this order
 *   </AskSeamLink>
 */
export function AskSeamLink({ prompt, children = "Ask Seam" }) {
  const { openWithPrompt } = useSeamAssistant();

  return (
    <button type="button" className="seam-inline-trigger" onClick={() => openWithPrompt(prompt)}>
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M12 2L14.2 9.2 21 12l-6.8 2.8L12 22l-2.2-7.2L3 12l6.8-2.8L12 2z" fill="currentColor" />
      </svg>
      {children}
    </button>
  );
}
