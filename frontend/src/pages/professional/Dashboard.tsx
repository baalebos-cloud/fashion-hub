import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useOrders } from "@/hooks/use-orders";
import { OrderList } from "@/components/orders/OrderList";
import { dashboardApi } from "@/api/dashboard.api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { professionalRoutes } from "@/config/routes.config";
import type { DashboardSummaryCard } from "@/types/dashboard";

export default function Dashboard() {
  const { orders, isLoading } = useOrders();
  const [summary, setSummary] = useState<DashboardSummaryCard[]>([]);

  useEffect(() => {
    dashboardApi.getSummary().then(setSummary).catch(() => setSummary([]));
  }, []);

  const pending = orders.filter((o) => o.status === "paid" || o.status === "accepted" || o.status === "in_production");

  return (
    <div className="flex flex-col gap-8">
      <div className="flex items-center justify-between">
        <h1 className="font-display text-xl text-ink">Overview</h1>
        <Link to={professionalRoutes.vendorMarketplace}><Button variant="secondary">Browse materials</Button></Link>
      </div>

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
        <h2 className="mb-3 text-sm font-medium text-ink-soft">Needs your attention</h2>
        {!isLoading && <OrderList orders={pending} detailsPathFor={professionalRoutes.orderDetails} />}
      </div>
    </div>
  );
}
