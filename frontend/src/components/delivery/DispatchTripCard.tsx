import type { DeliveryTrip, DispatchWaypoint } from "@/types/delivery";
import type { CallParty } from "@/types/call";
import { CallButton } from "@/components/calls/CallButton";

/** Display directions only when the backend supplied complete, validated pins. */
export function mapsDestination(point: DispatchWaypoint): string | null {
  if (point.latitude == null || point.longitude == null ||
      !Number.isFinite(point.latitude) || !Number.isFinite(point.longitude) ||
      Math.abs(point.latitude) > 90 || Math.abs(point.longitude) > 180) return null;
  return `https://www.google.com/maps/dir/?api=1&destination=${point.latitude},${point.longitude}`;
}

function Waypoint({ title, point, orderId, party }: { title: string; point: DispatchWaypoint; orderId: string; party: CallParty }) {
  const directions = mapsDestination(point);
  return (
    <div className="rounded-card border border-line p-4">
      <h3 className="text-sm font-semibold text-ink">{title}</h3>
      <p className="mt-1 text-sm text-ink">{point.address || "Address unavailable"}</p>
      {(point.lga || point.landmark || point.nearest_bus_stop) && (
        <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-xs">
          {point.lga && <><dt className="text-ink-soft">LGA</dt><dd className="text-ink">{point.lga}</dd></>}
          {point.landmark && <><dt className="text-ink-soft">Landmark</dt><dd className="text-ink">{point.landmark}</dd></>}
          {point.nearest_bus_stop && <><dt className="text-ink-soft">Bus stop</dt><dd className="text-ink">{point.nearest_bus_stop}</dd></>}
        </dl>
      )}
      {point.delivery_instructions && (
        <p className="mt-2 rounded bg-muslin px-2 py-1 text-xs text-ink">Note: {point.delivery_instructions}</p>
      )}
      {point.contact_name && <p className="mt-1 text-sm text-ink-soft">{point.contact_name}</p>}
      <div className="mt-3 flex flex-wrap gap-3 text-sm">
        {directions && <a href={directions} target="_blank" rel="noopener noreferrer" className="text-brass-deep underline">Navigate with Google Maps</a>}
      </div>
      {point.can_call && (
        <div className="mt-3">
          <CallButton orderId={orderId} party={party} label={party === "seller" ? "Call pickup contact" : "Call customer"} />
        </div>
      )}
      {!directions && <p className="mt-2 text-xs text-ink-soft">This stop needs a confirmed GPS pin for navigation.</p>}
    </div>
  );
}

export function DispatchTripCard({ trip }: { trip: DeliveryTrip }) {
  return (
    <section className="space-y-3" aria-label="Delivery itinerary">
      <Waypoint title="Pickup point" point={trip.pickup} orderId={trip.order_id} party="seller" />
      <Waypoint title="Customer drop-off" point={trip.dropoff} orderId={trip.order_id} party="buyer" />
      {trip.straight_line_km != null && <p className="text-xs text-ink-soft">
        Approximately {trip.straight_line_km.toFixed(1)} km straight-line distance.
        This is not a driving distance, route ETA or delivery fee estimate.
      </p>}
    </section>
  );
}
