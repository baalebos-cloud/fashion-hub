import { useAI } from "@/hooks/use-ai";

const SPARKLE = (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <path d="M12 2L14.2 9.2 21 12l-6.8 2.8L12 22l-2.2-7.2L3 12l6.8-2.8L12 2z" fill="currentColor" />
  </svg>
);

/**
 * The floating "Ask Seam" launcher pinned to the corner of the viewport —
 * this is the piece that makes the assistant feel like part of the app
 * shell rather than a page. Rendered exclusively from AIAssistant.tsx,
 * which mounts it via a portal so it sits above every route.
 */
export function AIHelpButton() {
  const { isOpen, toggle } = useAI();

  return (
    <button
      type="button"
      onClick={toggle}
      aria-expanded={isOpen}
      aria-controls="ai-assistant-panel"
      aria-label="Open Seam, the Fashion Hub assistant"
      className="fixed bottom-6 right-6 z-[2147483000] flex items-center gap-2.5 rounded-full border border-black/5 bg-ink px-[18px] py-3 pl-3.5 text-paper shadow-[0_10px_30px_rgba(28,34,48,0.28)] transition-all hover:-translate-y-0.5 hover:shadow-[0_14px_36px_rgba(28,34,48,0.34)] data-[open=true]:pointer-events-none data-[open=true]:scale-95 data-[open=true]:opacity-0"
      data-open={isOpen}
    >
      <span className="flex h-6.5 w-6.5 items-center justify-center rounded-full bg-brass text-ink">{SPARKLE}</span>
      <span className="text-sm font-medium">Ask Seam</span>
    </button>
  );
}
