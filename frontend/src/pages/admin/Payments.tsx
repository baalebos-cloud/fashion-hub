import { useState } from "react";
import { Table, type Column } from "@/components/ui/table";
import { EmptyState } from "@/components/ui/empty-state";
import { formatCurrency } from "@/lib/formatters/currency";

interface PaymentRow {
  id: string;
  order_number: string;
  amount: number;
  currency: string;
  status: string;
}

/** Requires `GET /admin/payments`. See Users.tsx. */
export default function Payments() {
  const [payments] = useState<PaymentRow[]>([]);
  if (payments.length === 0) return <EmptyState title="No payments to show" />;

  const columns: Column<PaymentRow>[] = [
    { header: "Order", render: (p) => p.order_number },
    { header: "Amount", render: (p) => formatCurrency(p.amount, p.currency) },
    { header: "Status", render: (p) => p.status },
  ];

  return (
    <div>
      <h1 className="mb-6 font-display text-xl text-ink">Payments</h1>
      <Table columns={columns} rows={payments} />
    </div>
  );
}
