import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useOrders } from "@/hooks/use-orders";
import { OrderList } from "@/components/orders/OrderList";
import { dashboardApi } from "@/api/dashboard.api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Greeting } from "@/components/common/Greeting";
import { QuickActions } from "@/components/common/QuickActions";
import { customerRoutes } from "@/config/routes.config";
import type { DashboardSummaryCard } from "@/types/dashboard";

export default function Dashboard() {
  const { orders, isLoading } = useOrders();
  const [summary, setSummary] = useState<DashboardSummaryCard[]>([]);

  useEffect(() => {
    dashboardApi.getSummary().then(setSummary).catch(() => setSummary([]));
  }, []);

  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <Greeting subtitle="Track your orders or start something new." />
        <Link to={customerRoutes.findProfessionals} className="hidden sm:block"><Button>Find a professional</Button></Link>
      </div>

      <QuickActions actions={[
        { label: "Find a tailor", description: "Verified tailors near you", to: customerRoutes.findProfessionals },
        { label: "Measurements", description: "Type them or use photos", to: customerRoutes.measurements },
        { label: "My orders", description: "Track every step", to: customerRoutes.orders },
        { label: "Messages", description: "Chat with your tailor", to: customerRoutes.messages },
      ]} />

      {summary.length > 0 && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {summary.map((card) => (
            <Card key={card.label}>
              <div className="text-xs text-ink-soft">{card.label}</div>
              <div className="mt-1 text-xl font-medium text-ink">{card.value}</div>
            </Card>
          ))}
        </div>
      )}

      <div>
        <h2 className="mb-3 text-sm font-medium text-ink-soft">Recent orders</h2>
        {!isLoading && orders.length === 0 && (
          <p className="rounded-card border border-dashed border-line p-6 text-center text-sm text-ink-soft">
            No orders yet. Find a verified tailor or designer to get started.
          </p>
        )}
        {!isLoading && orders.length > 0 && <OrderList orders={orders.slice(0, 5)} detailsPathFor={customerRoutes.orderDetails} />}
      </div>
    </div>
  );
}
