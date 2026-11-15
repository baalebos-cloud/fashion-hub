import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { dashboardApi } from "@/api/dashboard.api";
import { deliveryPartnersApi } from "@/api/delivery-partners.api";
import { deliveriesApi } from "@/api/deliveries.api";
import { DeliveryCard } from "@/components/delivery/DeliveryCard";
import { Card } from "@/components/ui/card";
import { Greeting } from "@/components/common/Greeting";
import { Button } from "@/components/ui/button";
import { DeliveryStatusBadge } from "@/components/delivery/DeliveryStatusBadge";
import { RiderStatusCard } from "@/components/delivery/RiderStatusCard";
import { RiderRoute } from "@/components/delivery/RiderRoute";
import { deliveryRoutes } from "@/config/routes.config";
import { formatNaira } from "@/lib/formatters/currency";
import type { DashboardSummaryCard } from "@/types/dashboard";
import type { Delivery } from "@/types/delivery";

const RECENT_COUNT = 5;

export default function Dashboard() {
  const [summary, setSummary] = useState<DashboardSummaryCard[]>([]);
  const [active, setActive] = useState<Delivery[]>([]);
  // null while loading or if it failed: the section stays hidden rather than claiming "none yet".
  const [recent, setRecent] = useState<Delivery[] | null>(null);

  useEffect(() => {
    dashboardApi.getSummary().then(setSummary).catch(() => setSummary([]));
    deliveryPartnersApi.activeDeliveries().then(setActive).catch(() => setActive([]));
    deliveriesApi.myHistory(1, RECENT_COUNT)
      .then((rows) => setRecent(Array.isArray(rows) ? rows : null))
      .catch(() => setRecent(null));
  }, []);

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6">
      <Greeting subtitle="Your deliveries at a glance." />
      <RiderStatusCard />

      <section aria-labelledby="active-heading" className="flex flex-col gap-3">
        <h2 id="active-heading" className="text-[13px] font-semibold uppercase tracking-wide text-ink-soft">Current job</h2>
        {active.length === 0 && (
          <div className="flex flex-col items-start gap-3 rounded-card border border-dashed border-line-strong bg-surface p-5">
            <p className="text-sm text-ink-soft">No job in progress. Go online and pick one from the job board.</p>
            <Link to={deliveryRoutes.requests}><Button>Find jobs</Button></Link>
          </div>
        )}
        {active.map((delivery) => (
          <Card key={delivery.id} className="flex flex-col gap-3 border-indigo/40 p-5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <DeliveryStatusBadge status={delivery.status} />
              <span className="font-mono text-sm text-ink-soft">Order {delivery.order_id.slice(0, 8).toUpperCase()}</span>
            </div>
            <p className="text-sm text-ink-soft">Fare <span className="font-mono font-semibold text-ink">{formatNaira(delivery.delivery_fee)}</span> · route and handover inside</p>
            <Link to={deliveryRoutes.details(delivery.id)}><Button size="lg" className="w-full">Open job</Button></Link>
          </Card>
        ))}
        {active.length > 0 && (
          <Link to={deliveryRoutes.requests} className="self-start text-sm font-semibold text-indigo">Find more jobs</Link>
        )}
      </section>

      <RiderRoute />

      {recent && (
        <section aria-labelledby="recent-heading" className="flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <h2 id="recent-heading" className="text-[13px] font-semibold uppercase tracking-wide text-ink-soft">Recently completed</h2>
            {recent.length > 0 && <Link to={deliveryRoutes.history} className="text-sm font-semibold text-indigo">See all</Link>}
          </div>
          {recent.length === 0
            ? <p className="text-sm text-ink-soft">Jobs you finish show up here, with the fare for each.</p>
            : recent.map((delivery) => (
              <DeliveryCard key={delivery.id} delivery={delivery} detailsPath={deliveryRoutes.details(delivery.id)} />
            ))}
        </section>
      )}

      {summary.length > 0 && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {summary.map((card) => (
            <Card key={card.label} className="p-4">
              <div className="text-[13px] text-ink-soft">{card.label}</div>
              <div className="mt-1 font-display text-2xl text-ink">{card.value}</div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
