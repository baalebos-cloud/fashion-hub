import { useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import "./seam-assistant.css";
import { useSeamAssistant } from "./SeamAssistantContext";
import { useSeamChat } from "./useSeamChat";

const SPARKLE = (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <path
      d="M12 2L14.2 9.2 21 12l-6.8 2.8L12 22l-2.2-7.2L3 12l6.8-2.8L12 2z"
      fill="currentColor"
    />
  </svg>
);

const CLOSE_ICON = (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
  </svg>
);

const SEND_ICON = (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <path d="M4 12l16-8-6 8 6 8-16-8z" fill="currentColor" />
  </svg>
);

const ROLE_LABEL = {
  customer: "here to help you shop and track orders",
  tailor: "here to help with orders and materials",
  designer: "here to help with orders and your portfolio",
  vendor: "here to help manage your storefront",
  delivery_partner: "here to help with deliveries",
};

export function SeamAssistantWidget() {
  const { isOpen, close, toggle, role, apiBaseUrl, getAuthToken, quickPrompts, pendingPrompt, consumePendingPrompt } =
    useSeamAssistant();
  const { messages, sendMessage, isSending, error } = useSeamChat({ apiBaseUrl, getAuthToken });

  const threadRef = useRef(null);
  const inputRef = useRef(null);

  // Keyboard: Escape closes the panel from anywhere inside it.
  useEffect(() => {
    if (!isOpen) return;
    const onKeyDown = (e) => {
      if (e.key === "Escape") close();
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [isOpen, close]);

  // Focus the composer whenever the panel opens.
  useEffect(() => {
    if (isOpen) {
      const id = setTimeout(() => inputRef.current?.focus(), 220);
      return () => clearTimeout(id);
    }
  }, [isOpen]);

  // Always scroll to the newest message.
  useEffect(() => {
    threadRef.current?.scrollTo({ top: threadRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, isSending]);

  // A prompt requested programmatically elsewhere in the app (e.g. an
  // "Ask Seam" link on an order page) is sent as soon as the panel opens.
  useEffect(() => {
    if (isOpen && pendingPrompt) {
      sendMessage(pendingPrompt);
      consumePendingPrompt();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, pendingPrompt]);

  const handleSubmit = (e) => {
    e.preventDefault();
    const value = inputRef.current?.value ?? "";
    sendMessage(value);
    if (inputRef.current) inputRef.current.value = "";
  };

  const handleChipClick = (prompt) => {
    sendMessage(prompt);
  };

  return createPortal(
    <div className="seam-root" aria-live="polite">
      <button
        type="button"
        className={`seam-launcher ${isOpen ? "seam-open" : ""}`}
        onClick={toggle}
        aria-expanded={isOpen}
        aria-controls="seam-panel"
        aria-label="Open Seam, the Fashion Hub assistant"
      >
        <span className="seam-launcher-mark">{SPARKLE}</span>
        <span className="seam-launcher-label">Ask Seam</span>
      </button>

      <section
        id="seam-panel"
        role="dialog"
        aria-modal="false"
        aria-label="Seam assistant"
        className={`seam-panel ${isOpen ? "seam-visible" : ""}`}
      >
        <header className="seam-header">
          <span className="seam-header-mark">{SPARKLE}</span>
          <div className="seam-header-text">
            <div className="seam-header-name">Seam</div>
            <div className="seam-header-subtitle">{ROLE_LABEL[role] ?? ROLE_LABEL.customer}</div>
          </div>
          <button type="button" className="seam-icon-button" onClick={close} aria-label="Close assistant">
            {CLOSE_ICON}
          </button>
        </header>

        <div className="seam-thread" ref={threadRef}>
          {messages.length === 0 && (
            <div className="seam-empty">
              <div className="seam-empty-title">Lost, or just curious?</div>
              <p className="seam-empty-body">
                Ask about an order, a tailor, or how something in Fashion Hub works. Seam only tells you where to go —
                it never moves money or changes an order for you.
              </p>
              <div className="seam-chip-row">
                {quickPrompts.map((prompt) => (
                  <button key={prompt} type="button" className="seam-chip" onClick={() => handleChipClick(prompt)}>
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((message) => (
            <div key={message.id} className={`seam-message ${message.role === "user" ? "seam-from-user" : "seam-from-assistant"}`}>
              <div className="seam-bubble">{message.content}</div>
            </div>
          ))}

          {isSending && (
            <div className="seam-message seam-from-assistant">
              <div className="seam-bubble">
                <span className="seam-typing" aria-label="Seam is typing">
                  <span />
                  <span />
                  <span />
                </span>
              </div>
            </div>
          )}

          {error && <div className="seam-error">{error}</div>}
        </div>

        <form className="seam-composer" onSubmit={handleSubmit}>
          <div className="seam-composer-row">
            <textarea
              ref={inputRef}
              className="seam-composer-input"
              rows={1}
              placeholder="Ask Seam anything about Fashion Hub…"
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit(e);
                }
              }}
            />
            <button type="submit" className="seam-send-button" disabled={isSending} aria-label="Send message">
              {SEND_ICON}
            </button>
          </div>
          <div className="seam-footnote">Seam can point you to the right page — it can't see other people's orders.</div>
        </form>
      </section>
    </div>,
    document.body
  );
}
