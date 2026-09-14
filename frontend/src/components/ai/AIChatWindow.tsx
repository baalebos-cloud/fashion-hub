import { useEffect, useRef } from "react";
import { useAI } from "@/hooks/use-ai";
import { AIMessage } from "./AIMessage";
import { AIInput } from "./AIInput";
import { AIQuickActions } from "./AIQuickActions";
import type { UserRole } from "@/types/auth";

const SPARKLE = (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <path d="M12 2L14.2 9.2 21 12l-6.8 2.8L12 22l-2.2-7.2L3 12l6.8-2.8L12 2z" fill="currentColor" />
  </svg>
);

const CLOSE_ICON = (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
  </svg>
);

const ROLE_SUBTITLE: Record<string, string> = {
  customer: "here to help you shop and track orders",
  tailor: "here to help with orders and materials",
  designer: "here to help with orders and your portfolio",
  vendor: "here to help manage your storefront",
  delivery_partner: "here to help with deliveries",
  admin: "here to help you manage the platform",
};

/**
 * The chat panel itself. Mounted by AIAssistant.tsx alongside AIHelpButton
 * — this component doesn't decide whether it's visible; it just renders
 * according to `isOpen` from the shared useAI() store, so opening it from
 * a completely different page (via AskSeamLink-style triggers elsewhere)
 * produces the exact same panel with the same ongoing conversation.
 */
export function AIChatWindow({ role }: { role: UserRole }) {
  const { isOpen, turns, isSending, error, pendingPrompt, close, sendMessage } = useAI();
  const threadRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;
    const onKeyDown = (e: KeyboardEvent) => e.key === "Escape" && close();
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [isOpen, close]);

  useEffect(() => {
    threadRef.current?.scrollTo({ top: threadRef.current.scrollHeight, behavior: "smooth" });
  }, [turns, isSending]);

  useEffect(() => {
    if (isOpen && pendingPrompt) {
      sendMessage(pendingPrompt);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, pendingPrompt]);

  return (
    <section
      id="ai-assistant-panel"
      role="dialog"
      aria-modal="false"
      aria-label="Seam assistant"
      className="fixed bottom-6 right-6 z-[2147483000] flex h-[min(620px,calc(100vh-48px))] w-[380px] max-w-[calc(100vw-32px)] origin-bottom-right flex-col overflow-hidden rounded-[20px] border border-line bg-muslin shadow-[0_24px_60px_rgba(28,34,48,0.32)] transition-all duration-200 sm:max-w-[calc(100vw-24px)]"
      style={{
        transform: isOpen ? "scale(1) translateY(0)" : "scale(0.9) translateY(12px)",
        opacity: isOpen ? 1 : 0,
        pointerEvents: isOpen ? "auto" : "none",
      }}
    >
      <header className="flex flex-shrink-0 items-center gap-3 bg-ink px-4 py-3.5 text-paper">
        <span className="flex h-[30px] w-[30px] flex-shrink-0 items-center justify-center rounded-full bg-brass text-ink">
          {SPARKLE}
        </span>
        <div className="min-w-0 flex-1">
          <div className="font-display text-[17px] font-semibold leading-tight">Seam</div>
          <div className="truncate text-xs text-paper/70">{ROLE_SUBTITLE[role]}</div>
        </div>
        <button
          type="button"
          onClick={close}
          aria-label="Close assistant"
          className="flex h-[30px] w-[30px] flex-shrink-0 items-center justify-center rounded-lg text-paper/75 transition-colors hover:bg-white/10 hover:text-paper"
        >
          {CLOSE_ICON}
        </button>
      </header>

      <div ref={threadRef} className="flex flex-1 flex-col gap-3 overflow-y-auto p-4">
        {turns.length === 0 && (
          <div className="my-auto">
            <div className="font-display text-[19px] text-ink">Lost, or just curious?</div>
            <p className="mt-1.5 max-w-[30ch] text-[13.5px] leading-relaxed text-ink-soft">
              Ask about an order, a tailor, or how something in Fashion Hub works. Seam only tells you where to go —
              it never moves money or changes an order for you.
            </p>
            <AIQuickActions role={role} onSelect={sendMessage} />
          </div>
        )}

        {turns.map((turn) => (
          <AIMessage key={turn.id} turn={turn} />
        ))}

        {isSending && (
          <div className="flex justify-start">
            <div className="rounded-2xl rounded-bl-md border border-line bg-paper px-3.5 py-3">
              <span className="inline-flex gap-1" aria-label="Seam is typing">
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-ink-soft [animation-delay:-0.3s]" />
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-ink-soft [animation-delay:-0.15s]" />
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-ink-soft" />
              </span>
            </div>
          </div>
        )}

        {error && (
          <div className="rounded-lg border border-[#eac9c2] bg-[#fbeceA] px-3 py-2 text-xs text-thread">{error}</div>
        )}
      </div>

      <AIInput onSend={sendMessage} isSending={isSending} autoFocus={isOpen} />
    </section>
  );
}
