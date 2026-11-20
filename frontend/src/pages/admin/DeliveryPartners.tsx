import { AdminListPage } from "@/components/admin/AdminListPage";
import { Badge } from "@/components/ui/badge";
import { adminListsApi, type AdminRider } from "@/api/admin-lists.api";

const date = (v: string | null) => (v ? new Date(v).toLocaleDateString("en-NG") : "—");

export default function DeliveryPartners() {
  return (
    <AdminListPage<AdminRider>
      title="Delivery partners"
      load={adminListsApi.riders}
      emptyTitle="No delivery partners to show"
      filters={[{ label: "All", params: {} }, { label: "Online now", params: { online: true } }, { label: "Awaiting verification", params: { verified: false } }]}
      columns={[
        { header: "Rider", render: (p) => <span className="flex flex-col"><span>{p.name ?? "—"}</span><span className="text-xs text-ink-soft">{p.email}</span></span> },
        { header: "Vehicle", render: (p) => p.vehicle_type ?? "—" },
        { header: "Status", render: (p) => p.is_verified ? <Badge tone="success">Verified</Badge> : <Badge tone="warning">Awaiting verification</Badge> },
        { header: "Online", render: (p) => (p.is_available ? "Yes" : "No") },
        { header: "Delivered", render: (p) => p.completed_deliveries },
        { header: "Rating", render: (p) => (p.average_rating ? `★ ${p.average_rating.toFixed(1)}` : "New") },
        { header: "Joined", render: (p) => date(p.created_at) },
      ]}
    />
  );
}
