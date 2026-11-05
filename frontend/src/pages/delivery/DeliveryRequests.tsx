import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { deliveryRequestsApi } from "@/api/delivery-requests.api";
import { deliveryRoutes } from "@/config/routes.config";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { DateTimeDisplay } from "@/components/common/DateTimeDisplay";
import { EmptyState } from "@/components/ui/empty-state";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import { formatNaira as naira } from "@/lib/formatters/currency";
import type { DispatchJob } from "@/types/dispatch";
import { ReservedJobs } from "@/components/dispatch/ReservedJobs";

const REFRESH_MS = 20_000;

function OfferForm({ job, onSent }: { job: DispatchJob; onSent: () => void }) {
  const [amount, setAmount] = useState(String(Math.round(job.my_offer?.amount ?? job.suggested_fare)));
  const [minutes, setMinutes] = useState(String(job.my_offer?.eta_to_pickup_minutes ?? 10));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const value = Number(amount);
    const eta = Number(minutes);
    if (!Number.isFinite(value) || value < job.offer_min || value > job.offer_max) {
      setError(`Offer between ${naira(job.offer_min)} and ${naira(job.offer_max)}.`);
      return;
    }
    if (!Number.isInteger(eta) || eta < 1 || eta > 120) {
      setError("Minutes to pickup must be between 1 and 120.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await deliveryRequestsApi.makeOffer(job.id, value, eta);
      onSent();
    } catch (err) {
      setError(getDisplayErrorMessage(err, "Your offer couldn't be sent."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form noValidate onSubmit={(e) => void submit(e)} className="mt-3 grid grid-cols-2 gap-2 rounded-lg bg-muslin p-3">
      <label className="text-xs text-ink-soft">
        Your fare (₦)
        <input type="number" inputMode="numeric" step="50" min={job.offer_min} max={job.offer_max} value={amount}
          onChange={(e) => setAmount(e.target.value)}
          className="mt-1 w-full rounded-lg border border-line bg-paper px-3 py-2 text-sm text-ink focus:border-brass focus:outline-none" />
      </label>
      <label className="text-xs text-ink-soft">
        Minutes to pickup
        <input type="number" inputMode="numeric" min={1} max={120} value={minutes}
          onChange={(e) => setMinutes(e.target.value)}
          className="mt-1 w-full rounded-lg border border-line bg-paper px-3 py-2 text-sm text-ink focus:border-brass focus:outline-none" />
      </label>
      <p className="col-span-2 text-[11px] text-ink-soft">Allowed: {naira(job.offer_min)} – {naira(job.offer_max)}. Offers expire after 10 minutes.</p>
      {error && <p role="alert" className="col-span-2 text-xs text-thread">{error}</p>}
      <Button type="submit" size="sm" className="col-span-2" isLoading={busy}>
        {job.my_offer?.status === "pending" ? "Update offer" : "Send offer"}
      </Button>
    </form>
  );
}

function JobCard({ job, busy, onClaim, onChanged }: {
  job: DispatchJob; busy: boolean; onClaim: () => void; onChanged: () => void;
}) {
  const [offering, setOffering] = useState(false);
  const pending = job.my_offer?.status === "pending";

  async function withdraw() {
    try { await deliveryRequestsApi.withdrawOffer(job.id); } finally { onChanged(); }
  }

  return (
    <Card className="p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-display text-2xl text-ink">{naira(job.suggested_fare)}</p>
          <p className="text-xs text-ink-soft">
            Suggested fare{job.approx_road_km != null && ` · ≈ ${job.approx_road_km.toFixed(1)} km`}
          </p>
        </div>
        <DateTimeDisplay value={job.posted_at} format="relative" className="text-xs text-ink-soft" />
      </div>

      <ol className="mt-3 space-y-1.5 text-sm text-ink" aria-label="Route">
        <li className="flex items-center gap-2"><span className="h-2 w-2 rounded-full bg-brass" aria-hidden="true" />
          Pickup · {job.pickup_area ?? "Area shared after assignment"}</li>
        <li className="flex items-center gap-2"><span className="h-2 w-2 rounded-full bg-ink" aria-hidden="true" />
          Drop-off · {job.dropoff_area ?? "Area shared after assignment"}</li>
      </ol>

      {pending && (
        <p role="status" className="mt-3 rounded-lg bg-[#fbf0dd] px-3 py-2 text-xs text-[#8a5f1f]">
          Your offer of {naira(job.my_offer!.amount)} ({job.my_offer!.eta_to_pickup_minutes} min to pickup) is waiting for the seller.
        </p>
      )}
      {job.my_offer?.status === "declined" && (
        <p className="mt-3 text-xs text-ink-soft">Your last offer wasn't chosen or expired. You can offer again.</p>
      )}

      <div className="mt-3 grid grid-cols-2 gap-2">
        <Button size="sm" onClick={onClaim} isLoading={busy} disabled={busy}>Accept {naira(job.suggested_fare)}</Button>
        {pending
          ? <Button size="sm" variant="secondary" onClick={() => void withdraw()}>Withdraw offer</Button>
          : <Button size="sm" variant="secondary" onClick={() => setOffering((v) => !v)} aria-expanded={offering}>
              {offering ? "Close" : "Offer your fare"}
            </Button>}
      </div>
      {(offering || pending) && !busy && (
        <OfferForm job={job} onSent={() => { setOffering(false); onChanged(); }} />
      )}
    </Card>
  );
}

export default function DeliveryRequests() {
  const navigate = useNavigate();
  const [items, setItems] = useState<DispatchJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const refresh = () => setRefreshKey((key) => key + 1);

  useEffect(() => {
    let active = true;
    deliveryRequestsApi.available().then((data) => {
      if (active) { setItems(data); setError(null); }
    }).catch((err: unknown) => {
      if (active) setError(getDisplayErrorMessage(err));
    }).finally(() => {
      if (active) setLoading(false);
    });
    const timer = window.setTimeout(refresh, REFRESH_MS);
    return () => { active = false; window.clearTimeout(timer); };
  }, [refreshKey]);

  async function claim(requestId: string) {
    setBusy(requestId);
    setError(null);
    try {
      const delivery = await deliveryRequestsApi.accept(requestId);
      navigate(deliveryRoutes.details(delivery.id));
    } catch (err) {
      setError(getDisplayErrorMessage(err));
      refresh();
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-4">
        <h1 className="font-display text-xl text-ink">Delivery jobs</h1>
        <Button variant="secondary" size="sm" onClick={refresh}>Refresh</Button>
      </div>
      <p className="text-sm text-ink-soft">
        Accept a job at the suggested fare, or offer your own fare and pickup time. Exact addresses and contacts are shared once you're assigned.
      </p>
      <ReservedJobs onAccepted={(delivery) => navigate(deliveryRoutes.details(delivery.id))} onChanged={refresh} />
      {loading && <p role="status">Checking for delivery jobs…</p>}
      {error && <p role="alert" className="text-thread">{error}</p>}
      {!loading && !error && items.length === 0 && (
        <EmptyState title="No delivery jobs right now" description="This page refreshes on its own every 20 seconds." />
      )}
      <div className="grid gap-4 md:grid-cols-2">
        {items.map((job) => (
          <JobCard key={job.id} job={job} busy={busy === job.id}
            onClaim={() => void claim(job.id)} onChanged={refresh} />
        ))}
      </div>
    </div>
  );
}
