import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { dashboardApi } from "@/api/dashboard.api";
import { deliveryPartnersApi } from "@/api/delivery-partners.api";
import { Card } from "@/components/ui/card";
import { Greeting } from "@/components/common/Greeting";
import { QuickActions } from "@/components/common/QuickActions";
import { DeliveryStatusBadge } from "@/components/delivery/DeliveryStatusBadge";
import { RiderStatusCard } from "@/components/delivery/RiderStatusCard";
import { RiderRoute } from "@/components/delivery/RiderRoute";
import { deliveryRoutes } from "@/config/routes.config";
import { formatNaira } from "@/lib/formatters/currency";
import type { DashboardSummaryCard } from "@/types/dashboard";
import type { Delivery } from "@/types/delivery";

export default function Dashboard() {
  const [summary, setSummary] = useState<DashboardSummaryCard[]>([]);
  const [active, setActive] = useState<Delivery[]>([]);

  useEffect(() => {
    dashboardApi.getSummary().then(setSummary).catch(() => setSummary([]));
    deliveryPartnersApi.activeDeliveries().then(setActive).catch(() => setActive([]));
  }, []);

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6">
      <Greeting subtitle="Your deliveries at a glance." />
      <RiderStatusCard />
      <RiderRoute />

      {active.length > 0 && (
        <section aria-labelledby="active-heading" className="flex flex-col gap-3">
          <h2 id="active-heading" className="text-sm font-medium text-ink-soft">Current job</h2>
          {active.map((delivery) => (
            <Link key={delivery.id} to={deliveryRoutes.details(delivery.id)}>
              <Card className="flex items-center justify-between gap-3 p-4 transition-colors hover:border-brass">
                <div>
                  <p className="font-medium text-ink">Delivery for order {delivery.order_id.slice(0, 8).toUpperCase()}</p>
                  <p className="text-xs text-ink-soft">Fare {formatNaira(delivery.delivery_fee)} · tap for route and handover</p>
                </div>
                <DeliveryStatusBadge status={delivery.status} />
              </Card>
            </Link>
          ))}
        </section>
      )}

      <QuickActions actions={[
        { label: "Find jobs", description: "Accept or offer a fare", to: deliveryRoutes.requests },
        { label: "Active deliveries", description: "Pickup, route, handover", to: deliveryRoutes.active },
        { label: "Earnings", description: "What you've made", to: deliveryRoutes.earnings },
        { label: "Verification", description: "Identity and status", to: deliveryRoutes.verification },
      ]} />

      {summary.length > 0 && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {summary.map((card) => (
            <Card key={card.label} className="p-4">
              <div className="text-xs text-ink-soft">{card.label}</div>
              <div className="mt-1 text-xl font-medium text-ink">{card.value}</div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
