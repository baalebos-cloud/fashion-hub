import { AdminListPage } from "@/components/admin/AdminListPage";
import { Badge } from "@/components/ui/badge";
import { adminListsApi, type AdminVendor } from "@/api/admin-lists.api";

const date = (v: string | null) => (v ? new Date(v).toLocaleDateString("en-NG") : "—");

export default function Vendors() {
  return (
    <AdminListPage<AdminVendor>
      title="Vendors"
      load={adminListsApi.vendors}
      emptyTitle="No vendors to show"
      filters={[{ label: "All", params: {} }, { label: "Verified", params: { verified: true } }, { label: "Awaiting verification", params: { verified: false } }]}
      columns={[
        { header: "Business", render: (v) => v.business_name },
        { header: "Owner", render: (v) => <span className="flex flex-col"><span>{v.owner_name ?? "—"}</span><span className="text-xs text-ink-soft">{v.owner_email}</span></span> },
        { header: "Status", render: (v) => v.is_verified ? <Badge tone="success">Verified</Badge> : <Badge tone="warning">Awaiting verification</Badge> },
        { header: "Products on sale", render: (v) => v.active_products },
        { header: "Rating", render: (v) => (v.average_rating ? `★ ${v.average_rating.toFixed(1)}` : "New") },
        { header: "Joined", render: (v) => date(v.created_at) },
      ]}
    />
  );
}
