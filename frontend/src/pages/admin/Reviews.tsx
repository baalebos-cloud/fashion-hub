import { AdminListPage } from "@/components/admin/AdminListPage";
import { adminListsApi, type AdminReview } from "@/api/admin-lists.api";

const date = (v: string | null) => (v ? new Date(v).toLocaleDateString("en-NG") : "—");

export default function Reviews() {
  return (
    <AdminListPage<AdminReview>
      title="Reviews"
      load={adminListsApi.reviews}
      emptyTitle="No reviews to show"
      intro="Low ratings are the ones worth reading first: they often point to a sizing, quality or delivery problem."
      filters={[{ label: "All", params: {} }, { label: "2 stars or less", params: { max_score: 2 } }]}
      columns={[
        { header: "Rating", render: (r) => (r.score != null ? `★ ${r.score.toFixed(1)}` : "—") },
        { header: "Comment", render: (r) => <span className="line-clamp-3 max-w-md">{r.comment || "—"}</span> },
        { header: "From", render: (r) => r.reviewer ?? "—" },
        { header: "About", render: (r) => r.reviewee ?? "—" },
        { header: "Order", render: (r) => <span className="font-mono">{r.order_number ?? "—"}</span> },
        { header: "Date", render: (r) => date(r.created_at) },
      ]}
    />
  );
}
