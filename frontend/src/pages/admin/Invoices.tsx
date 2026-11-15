import { AdminListPage } from "@/components/admin/AdminListPage";
import { InvoiceStatus } from "@/components/invoices/InvoiceStatus";
import { formatCurrency } from "@/lib/formatters/currency";
import { adminListsApi, type AdminInvoice } from "@/api/admin-lists.api";

const date = (v: string | null) => (v ? new Date(v).toLocaleDateString("en-NG") : "—");

export default function Invoices() {
  return (
    <AdminListPage<AdminInvoice>
      title="Invoices"
      load={adminListsApi.invoices}
      emptyTitle="No invoices to show"
      intro="An invoice is issued for every order once its payment is confirmed."
      columns={[
        { header: "Invoice", render: (i) => <span className="font-mono">{i.invoice_number}</span> },
        { header: "Customer", render: (i) => i.issued_to ?? "—" },
        { header: "Seller", render: (i) => i.issued_by ?? "—" },
        { header: "Total", render: (i) => formatCurrency(i.total_amount, i.currency) },
        { header: "Status", render: (i) => <InvoiceStatus status={i.payment_status} /> },
        { header: "Ordered", render: (i) => date(i.order_date) },
      ]}
    />
  );
}
