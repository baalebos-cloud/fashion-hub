import { useEffect, useState } from "react";
import { describeRoute } from "@/lib/utils/route";
import { deliveryRequestsApi } from "@/api/delivery-requests.api";
import { Avatar } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { DateTimeDisplay } from "@/components/common/DateTimeDisplay";
import { VerificationBadge } from "@/components/profile/VerificationBadge";
import { formatNaira } from "@/lib/formatters/currency";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import type { SellerDispatchView } from "@/types/dispatch";

const VEHICLE: Record<string, string> = { bike: "Motorbike", car: "Car", van: "Van", foot: "On foot" };
const REFRESH_MS = 15_000;

/**
 * Seller's view after requesting a courier: the suggested fare and live rider
 * offers (cheapest first) to choose from. Riders can also claim instantly at
 * the suggested fare, which ends the bidding.
 */
export function DispatchOffers({ orderId, refreshKey = 0, onAssigned }: {
  orderId: string; refreshKey?: number; onAssigned?: () => void;
}) {
  const [view, setView] = useState<SellerDispatchView | null>(null);
  const [tick, setTick] = useState(0);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    deliveryRequestsApi.sellerDispatch(orderId)
      .then((data) => { if (active) setView(Array.isArray(data?.offers) ? data : null); })
      .catch(() => {});
    const timer = window.setTimeout(() => setTick((t) => t + 1), REFRESH_MS);
    return () => { active = false; window.clearTimeout(timer); };
  }, [orderId, refreshKey, tick]);

  if (!view?.request) return null;
  const { request, offers } = view;

  async function accept(offerId: string) {
    setBusy(offerId);
    setError(null);
    try {
      await deliveryRequestsApi.acceptOffer(offerId);
      onAssigned?.();
    } catch (err) {
      setError(getDisplayErrorMessage(err, "That offer couldn't be accepted."));
    } finally {
      setBusy(null);
      setTick((t) => t + 1);
    }
  }

  if (request.status !== "requested") {
    return (
      <Card className="p-4">
        <h2 className="text-sm font-medium text-ink">Rider assigned</h2>
        <p className="mt-1 text-xs text-ink-soft">Follow progress in the delivery journey below.</p>
      </Card>
    );
  }

  return (
    <Card className="flex flex-col gap-3 p-4" role="region" aria-label="Rider offers">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-medium text-ink">Finding a rider</h2>
          <p className="text-xs text-ink-soft">
            Suggested fare {formatNaira(request.suggested_fare)}
            {describeRoute(request.route, request.approx_road_km) && ` · ${describeRoute(request.route, request.approx_road_km)}`}.
            A rider can accept it instantly, or send their own offer for you to choose.
          </p>
        </div>
        <span className="relative mt-1 flex h-2.5 w-2.5 shrink-0" aria-hidden="true">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-brass opacity-60" />
          <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-brass" />
        </span>
      </div>

      {offers.length === 0
        ? <p className="text-sm text-ink-soft">No offers yet. This updates every 15 seconds.</p>
        : (
          <ul className="flex flex-col gap-2">
            {offers.map((offer) => (
              <li key={offer.id} className="flex flex-col gap-3 rounded-lg border border-line p-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-center gap-3">
                  <Avatar name={offer.rider.first_name} src={offer.rider.photo_url} />
                  <div>
                    <div className="flex items-center gap-1.5">
                      <span className="font-medium text-ink">{offer.rider.first_name}</span>
                      {offer.rider.is_verified && <VerificationBadge />}
                    </div>
                    <p className="text-xs text-ink-soft">
                      {[offer.rider.vehicle_type ? VEHICLE[offer.rider.vehicle_type] ?? offer.rider.vehicle_type : null,
                        offer.rider.rating > 0 ? `★ ${offer.rider.rating.toFixed(1)}` : null,
                        `${offer.rider.completed_deliveries} deliveries`].filter(Boolean).join(" · ")}
                    </p>
                  </div>
                </div>
                <div className="flex items-center justify-between gap-3 sm:justify-end">
                  <div className="text-right">
                    <p className="font-medium text-ink">{formatNaira(offer.amount)}</p>
                    <p className="text-xs text-ink-soft">
                      {offer.eta_to_pickup_minutes} min to pickup · expires <DateTimeDisplay value={offer.expires_at} format="relative" />
                    </p>
                  </div>
                  <Button size="sm" onClick={() => void accept(offer.id)} isLoading={busy === offer.id} disabled={busy !== null}>
                    Accept
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      {error && <p role="alert" className="text-xs text-thread">{error}</p>}
    </Card>
  );
}
