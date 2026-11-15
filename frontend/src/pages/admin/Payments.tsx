import { AdminListPage } from "@/components/admin/AdminListPage";
import { Badge } from "@/components/ui/badge";
import { formatCurrency } from "@/lib/formatters/currency";
import { adminListsApi, type AdminPayment } from "@/api/admin-lists.api";

const date = (v: string | null) => (v ? new Date(v).toLocaleDateString("en-NG") : "—");
const TONE: Record<string, "success" | "warning" | "neutral"> = { successful: "success", pending: "warning", initialized: "neutral", failed: "warning" };

export default function Payments() {
  return (
    <AdminListPage<AdminPayment>
      title="Payments"
      load={adminListsApi.payments}
      emptyTitle="No payments to show"
      intro="Every payment attempt, newest first. An order counts as paid only after the provider confirms it."
      filters={[{ label: "All", params: {} }, { label: "Successful", params: { status: "successful" } },
        { label: "Waiting", params: { status: "pending" } }, { label: "Started, not paid", params: { status: "initialized" } },
        { label: "Failed", params: { status: "failed" } }]}
      columns={[
        { header: "Order", render: (p) => <span className="flex flex-col"><span className="font-mono">{p.order_number}</span><span className="text-xs text-ink-soft">{p.order_type === "vendor_order" ? "Materials" : "Garment"}</span></span> },
        { header: "Buyer", render: (p) => p.buyer_name ?? "—" },
        { header: "Amount", render: (p) => formatCurrency(p.amount, p.currency) },
        { header: "Provider", render: (p) => <span className="capitalize">{p.provider}</span> },
        { header: "Status", render: (p) => <Badge tone={TONE[p.status] ?? "neutral"}>{p.status.replaceAll("_", " ")}</Badge> },
        { header: "Paid", render: (p) => date(p.paid_at) },
      ]}
    />
  );
}
