import { createPortal } from "react-dom";

import { authRoutes } from "@/config/routes.config";

const SPARKLE = (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <path d="M12 2L14.2 9.2 21 12l-6.8 2.8L12 22l-2.2-7.2L3 12l6.8-2.8L12 2z" fill="currentColor" />
  </svg>
);

/**
 * A visible-but-inert stand-in for Seam on public pages. It looks like
 * the real launcher (same mark, same corner) so the assistant doesn't
 * feel like it "appears out of nowhere" after signing in — but it can't
 * open a chat panel, because there's no authenticated user yet for the
 * backend's `/ai/navigation/messages` endpoint to scope a conversation to
 * (see backend/app/api/v1/ai_navigation.py::send_message, which requires
 * get_current_user).
 *
 * Clicking it goes straight to login rather than pretending to open a
 * panel that would immediately fail on the first message.
 */
export function AIPublicTeaser() {
  return createPortal(
    <a
      href={authRoutes.login}
      aria-label="Sign in to chat with Seam, the Fashion Hub assistant"
      className="fixed bottom-6 right-6 z-[2147483000] flex items-center gap-2.5 rounded-full border border-black/5 bg-ink px-[18px] py-3 pl-3.5 text-paper shadow-[0_10px_30px_rgba(28,34,48,0.28)] transition-all hover:-translate-y-0.5 hover:shadow-[0_14px_36px_rgba(28,34,48,0.34)]"
    >
      <span className="flex h-6.5 w-6.5 items-center justify-center rounded-full bg-brass text-ink">{SPARKLE}</span>
      <span className="text-sm font-medium">Sign in to ask Seam</span>
    </a>,
    document.body
  );
}
