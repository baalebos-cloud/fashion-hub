export function InvoicePreview({ pdfUrl }: { pdfUrl?: string | null }) {
  if (!pdfUrl) {
    return <p className="text-sm text-ink-soft">Your invoice PDF is being generated and will appear here shortly.</p>;
  }
  return <iframe src={pdfUrl} title="Invoice preview" className="h-[600px] w-full rounded-card border border-line" />;
}
