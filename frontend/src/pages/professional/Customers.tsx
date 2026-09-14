import { useMemo } from "react";
import { Link } from "react-router-dom";
import { useOrders } from "@/hooks/use-orders";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { professionalRoutes } from "@/config/routes.config";

export default function Customers() {
  const { orders, isLoading } = useOrders();

  const customerIds = useMemo(() => Array.from(new Set(orders.map((o) => o.id))), [orders]);

  if (isLoading) return null;

  if (customerIds.length === 0) {
    return <EmptyState title="No customers yet" description="Customers you've served will appear here." />;
  }

  return (
    <div>
      <h1 className="mb-6 font-display text-xl text-ink">Customers</h1>
      <div className="flex flex-col gap-3">
        {customerIds.map((id) => (
          <Link key={id} to={professionalRoutes.customerDetails(id)}>
            <Card className="transition-colors hover:border-brass">Customer {id.slice(0, 8)}</Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
