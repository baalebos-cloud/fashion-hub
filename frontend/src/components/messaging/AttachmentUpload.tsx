import { useRef } from "react";
import { uploadFile } from "@/lib/storage/file-storage";

export function AttachmentUpload({ onUploaded }: { onUploaded: (url: string) => void }) {
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleChange() {
    const file = inputRef.current?.files?.[0];
    if (!file) return;
    const { url } = await uploadFile("/messages/attachments", file);
    onUploaded(url);
  }

  return (
    <button type="button" onClick={() => inputRef.current?.click()} className="text-ink-soft hover:text-ink" aria-label="Attach a file">
      <input ref={inputRef} type="file" className="hidden" onChange={handleChange} />
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M21 12.5l-8.5 8.5a4 4 0 01-5.7-5.7l9-9a2.7 2.7 0 013.8 3.8l-9 9a1.3 1.3 0 01-1.9-1.9l8.1-8.1" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
      </svg>
    </button>
  );
}
