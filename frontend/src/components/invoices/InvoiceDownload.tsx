import { Button } from "@/components/ui/button";
import { downloadFromUrl } from "@/lib/utils/download";

export function InvoiceDownload({ pdfUrl, invoiceNumber }: { pdfUrl?: string | null; invoiceNumber: string }) {
  if (!pdfUrl) return null;
  return (
    <Button variant="secondary" onClick={() => downloadFromUrl(pdfUrl, `${invoiceNumber}.pdf`)}>
      Download PDF
    </Button>
  );
}
