import { Link } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { InvoiceStatus } from "./InvoiceStatus";
import { formatCurrency } from "@/lib/formatters/currency";
import type { Invoice } from "@/types/invoice";

export function InvoiceCard({ invoice, detailsPath }: { invoice: Invoice; detailsPath: string }) {
  return (
    <Link to={detailsPath}>
      <Card className="flex items-center justify-between transition-colors hover:border-brass">
        <div>
          <div className="font-medium text-ink">{invoice.invoice_number}</div>
          <div className="text-xs text-ink-soft">{formatCurrency(invoice.total_amount, invoice.currency)}</div>
        </div>
        <InvoiceStatus status={invoice.payment_status} />
      </Card>
    </Link>
  );
}
