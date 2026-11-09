import { useRef, useState } from "react";
import { uploadFile } from "@/lib/storage/file-storage";
import { getDisplayErrorMessage } from "@/lib/utils/errors";

export function AttachmentUpload({ onUploaded }: { onUploaded: (url: string) => void }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleChange() {
    const file = inputRef.current?.files?.[0];
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const { url } = await uploadFile("/messages/attachments", file);
      onUploaded(url);
    } catch (failure) {
      setError(getDisplayErrorMessage(failure, "The attachment couldn't be sent. Try again."));
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <span className="relative inline-flex items-center">
      <button type="button" onClick={() => inputRef.current?.click()} disabled={busy}
        className="text-ink-soft hover:text-ink disabled:opacity-50" aria-label={busy ? "Sending attachment" : "Attach a file"}>
        <input ref={inputRef} type="file" className="hidden" onChange={() => void handleChange()} />
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path d="M21 12.5l-8.5 8.5a4 4 0 01-5.7-5.7l9-9a2.7 2.7 0 013.8 3.8l-9 9a1.3 1.3 0 01-1.9-1.9l8.1-8.1" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
        </svg>
      </button>
      {error && <span role="alert" className="absolute bottom-full left-0 mb-1 w-56 rounded bg-surface p-2 text-xs text-thread shadow">{error}</span>}
    </span>
  );
}
