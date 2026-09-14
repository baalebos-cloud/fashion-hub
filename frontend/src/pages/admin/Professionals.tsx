import { useState } from "react";
import { Link } from "react-router-dom";
import { Table, type Column } from "@/components/ui/table";
import { VerificationBadge } from "@/components/profile/VerificationBadge";
import { EmptyState } from "@/components/ui/empty-state";
import { adminRoutes } from "@/config/routes.config";
import type { Professional } from "@/types/professional";

/** Requires `GET /admin/professionals`. See Users.tsx. */
export default function Professionals() {
  const [professionals] = useState<Professional[]>([]);
  if (professionals.length === 0) return <EmptyState title="No professionals to show" />;

  const columns: Column<Professional>[] = [
    { header: "Studio", render: (p) => p.business_name ?? "—" },
    { header: "Type", render: (p) => p.professional_type },
    { header: "Verified", render: (p) => (p.is_verified ? <VerificationBadge /> : "—") },
    { header: "", render: (p) => <Link to={adminRoutes.kyc} className="text-brass-deep hover:underline">Review</Link> },
  ];

  return (
    <div>
      <h1 className="mb-6 font-display text-xl text-ink">Professionals</h1>
      <Table columns={columns} rows={professionals} />
    </div>
  );
}
