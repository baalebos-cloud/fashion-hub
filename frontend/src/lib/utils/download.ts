/** Triggers a browser file download for a URL the backend already
 * generated (e.g. an invoice PDF's signed URL) — never constructs or
 * signs URLs client-side. */
export function downloadFromUrl(url: string, filename?: string): void {
  const link = document.createElement("a");
  link.href = url;
  if (filename) link.download = filename;
  link.rel = "noopener noreferrer";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}
