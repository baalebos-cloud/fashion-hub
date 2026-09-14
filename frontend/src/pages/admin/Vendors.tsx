import { useState } from "react";
import { Table, type Column } from "@/components/ui/table";
import { VerificationBadge } from "@/components/profile/VerificationBadge";
import { EmptyState } from "@/components/ui/empty-state";
import type { Vendor } from "@/types/vendor";

/** Requires `GET /admin/vendors`. See Users.tsx. */
export default function Vendors() {
  const [vendors] = useState<Vendor[]>([]);
  if (vendors.length === 0) return <EmptyState title="No vendors to show" />;

  const columns: Column<Vendor>[] = [
    { header: "Business", render: (v) => v.business_name },
    { header: "Verified", render: (v) => (v.is_verified ? <VerificationBadge /> : "—") },
    { header: "Rating", render: (v) => `★ ${v.average_rating.toFixed(1)}` },
  ];

  return (
    <div>
      <h1 className="mb-6 font-display text-xl text-ink">Vendors</h1>
      <Table columns={columns} rows={vendors} />
    </div>
  );
}
