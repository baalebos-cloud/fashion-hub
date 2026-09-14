import { useRef, type FormEvent, type KeyboardEvent } from "react";

const SEND_ICON = (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <path d="M4 12l16-8-6 8 6 8-16-8z" fill="currentColor" />
  </svg>
);

export interface AIInputProps {
  onSend: (content: string) => void;
  isSending: boolean;
  autoFocus?: boolean;
}

export function AIInput({ onSend, isSending, autoFocus }: AIInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const value = textareaRef.current?.value ?? "";
    if (!value.trim()) return;
    onSend(value);
    if (textareaRef.current) textareaRef.current.value = "";
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex-shrink-0 border-t border-line bg-muslin p-2.5 pb-3">
      <div className="flex items-end gap-2 rounded-2xl border border-line bg-paper py-1.5 pl-3.5 pr-1.5 focus-within:border-brass">
        <textarea
          ref={textareaRef}
          rows={1}
          autoFocus={autoFocus}
          placeholder="Ask Seam anything about Fashion Hub…"
          onKeyDown={handleKeyDown}
          className="max-h-24 flex-1 resize-none border-none bg-transparent py-1.5 text-sm text-ink outline-none placeholder:text-ink-soft/60"
        />
        <button
          type="submit"
          disabled={isSending}
          aria-label="Send message"
          className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-brass text-ink transition-colors hover:bg-brass-deep disabled:opacity-40"
        >
          {SEND_ICON}
        </button>
      </div>
      <p className="mt-2 text-center text-[10.5px] text-ink-soft">
        Seam can point you to the right page — it can&apos;t see other people&apos;s orders.
      </p>
    </form>
  );
}
