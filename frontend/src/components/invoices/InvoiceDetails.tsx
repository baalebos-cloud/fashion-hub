import { InvoicePreview } from "./InvoicePreview";
import { InvoiceDownload } from "./InvoiceDownload";
import { InvoiceStatus } from "./InvoiceStatus";
import { formatCurrency } from "@/lib/formatters/currency";
import type { Invoice } from "@/types/invoice";

export function InvoiceDetails({ invoice }: { invoice: Invoice }) {
  return (
    <div className="mx-auto flex max-w-xl flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="font-display text-xl text-ink">{invoice.invoice_number}</h1>
        <InvoiceStatus status={invoice.payment_status} />
      </div>

      <div className="rounded-card border border-line p-4 text-sm">
        <div className="flex justify-between py-1"><span className="text-ink-soft">Subtotal</span><span>{formatCurrency(invoice.subtotal, invoice.currency)}</span></div>
        <div className="flex justify-between py-1"><span className="text-ink-soft">Delivery fee</span><span>{formatCurrency(invoice.delivery_fee, invoice.currency)}</span></div>
        <div className="flex justify-between py-1"><span className="text-ink-soft">Tax</span><span>{formatCurrency(invoice.tax_amount, invoice.currency)}</span></div>
        <div className="flex justify-between py-1"><span className="text-ink-soft">Discount</span><span>-{formatCurrency(invoice.discount_amount, invoice.currency)}</span></div>
        <div className="flex justify-between border-t border-line pt-2 font-medium text-ink"><span>Total</span><span>{formatCurrency(invoice.total_amount, invoice.currency)}</span></div>
      </div>

      <InvoiceDownload pdfUrl={invoice.pdf_url} invoiceNumber={invoice.invoice_number} />
      <InvoicePreview pdfUrl={invoice.pdf_url} />
    </div>
  );
}
