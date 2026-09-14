import { useState } from "react";
import { Table, type Column } from "@/components/ui/table";
import { DeliveryStatusBadge } from "@/components/delivery/DeliveryStatusBadge";
import { EmptyState } from "@/components/ui/empty-state";
import type { Delivery } from "@/types/delivery";

/** Requires `GET /admin/deliveries`, ideally surfacing the stale-tracking
 * flag from backend/app/workers/tracking_tasks.py::check_stale_tracking_task
 * so ops can spot deliveries whose GPS has gone quiet. */
export default function Deliveries() {
  const [deliveries] = useState<Delivery[]>([]);
  if (deliveries.length === 0) return <EmptyState title="No deliveries to show" />;

  const columns: Column<Delivery>[] = [
    { header: "Order", render: (d) => d.order_id.slice(0, 8) },
    { header: "Status", render: (d) => <DeliveryStatusBadge status={d.status} /> },
  ];

  return (
    <div>
      <h1 className="mb-6 font-display text-xl text-ink">Deliveries</h1>
      <Table columns={columns} rows={deliveries} />
    </div>
  );
}
