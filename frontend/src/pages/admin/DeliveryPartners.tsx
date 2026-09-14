import { useState } from "react";
import { Table, type Column } from "@/components/ui/table";
import { VerificationBadge } from "@/components/profile/VerificationBadge";
import { EmptyState } from "@/components/ui/empty-state";
import type { DeliveryPartner } from "@/types/delivery";

/** Requires `GET /admin/delivery-partners`. See Users.tsx. */
export default function DeliveryPartners() {
  const [partners] = useState<DeliveryPartner[]>([]);
  if (partners.length === 0) return <EmptyState title="No delivery partners to show" />;

  const columns: Column<DeliveryPartner>[] = [
    { header: "Vehicle", render: (p) => p.vehicle_type ?? "—" },
    { header: "Verified", render: (p) => (p.is_verified ? <VerificationBadge /> : "—") },
    { header: "Available", render: (p) => (p.is_available ? "Yes" : "No") },
  ];

  return (
    <div>
      <h1 className="mb-6 font-display text-xl text-ink">Delivery partners</h1>
      <Table columns={columns} rows={partners} />
    </div>
  );
}
