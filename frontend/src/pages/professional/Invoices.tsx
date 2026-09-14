import { useEffect, useState } from "react";
import { useOrders } from "@/hooks/use-orders";
import { invoicesApi } from "@/api/invoices.api";
import { InvoiceCard } from "@/components/invoices/InvoiceCard";
import { EmptyState } from "@/components/ui/empty-state";
import { professionalRoutes } from "@/config/routes.config";
import type { Invoice } from "@/types/invoice";

export default function Invoices() {
  const { orders } = useOrders();
  const [invoices, setInvoices] = useState<Invoice[]>([]);

  useEffect(() => {
    Promise.all(orders.map((o) => invoicesApi.getByOrderId(o.id).catch(() => null))).then((results) =>
      setInvoices(results.filter((i): i is Invoice => i !== null))
    );
  }, [orders]);

  if (invoices.length === 0) return <EmptyState title="No invoices yet" />;

  return (
    <div>
      <h1 className="mb-6 font-display text-xl text-ink">Invoices</h1>
      <div className="flex flex-col gap-3">
        {invoices.map((invoice) => (
          <InvoiceCard key={invoice.id} invoice={invoice} detailsPath={`${professionalRoutes.invoices}/${invoice.id}`} />
        ))}
      </div>
    </div>
  );
}
