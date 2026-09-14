import { useRef, type FormEvent, type KeyboardEvent } from "react";

export function MessageInput({ onSend }: { onSend: (body: string) => void }) {
  const inputRef = useRef<HTMLInputElement>(null);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const value = inputRef.current?.value ?? "";
    if (!value.trim()) return;
    onSend(value);
    if (inputRef.current) inputRef.current.value = "";
  }

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") handleSubmit(e);
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-2 border-t border-line p-3">
      <input
        ref={inputRef}
        onKeyDown={handleKeyDown}
        placeholder="Type a message…"
        className="flex-1 rounded-lg border border-line px-3 py-2 text-sm focus:border-brass focus:outline-none"
      />
      <button type="submit" className="rounded-lg bg-ink px-4 py-2 text-sm text-paper">Send</button>
    </form>
  );
}
