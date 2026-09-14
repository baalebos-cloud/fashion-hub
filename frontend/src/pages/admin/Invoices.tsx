import { useState } from "react";
import { Table, type Column } from "@/components/ui/table";
import { InvoiceStatus } from "@/components/invoices/InvoiceStatus";
import { EmptyState } from "@/components/ui/empty-state";
import { formatCurrency } from "@/lib/formatters/currency";
import type { Invoice } from "@/types/invoice";

/** Requires `GET /admin/invoices`. See Users.tsx. */
export default function Invoices() {
  const [invoices] = useState<Invoice[]>([]);
  if (invoices.length === 0) return <EmptyState title="No invoices to show" />;

  const columns: Column<Invoice>[] = [
    { header: "Invoice", render: (i) => i.invoice_number },
    { header: "Total", render: (i) => formatCurrency(i.total_amount, i.currency) },
    { header: "Status", render: (i) => <InvoiceStatus status={i.payment_status} /> },
  ];

  return (
    <div>
      <h1 className="mb-6 font-display text-xl text-ink">Invoices</h1>
      <Table columns={columns} rows={invoices} />
    </div>
  );
}
