import type { DeliveryTrip, DispatchWaypoint } from "@/types/delivery";

/** Display directions only when the backend supplied complete, validated pins. */
export function mapsDestination(point: DispatchWaypoint): string | null {
  if (point.latitude == null || point.longitude == null ||
      !Number.isFinite(point.latitude) || !Number.isFinite(point.longitude) ||
      Math.abs(point.latitude) > 90 || Math.abs(point.longitude) > 180) return null;
  return `https://www.google.com/maps/dir/?api=1&destination=${point.latitude},${point.longitude}`;
}

export function contactLinks(phone: string | null): { call: string; whatsapp: string } | null {
  if (!phone) return null;
  const cleaned = phone.replace(/[\s()-]/g, "");
  const digits = cleaned.startsWith("+") ? cleaned.slice(1) : cleaned;
  const normalized = digits.startsWith("0") && digits.length === 11 ? "234" + digits.slice(1) : digits;
  if (!/^\d{10,15}$/.test(normalized)) return null;
  return { call: "tel:+" + normalized, whatsapp: "https://wa.me/" + normalized };
}

function Waypoint({ title, point }: { title: string; point: DispatchWaypoint }) {
  const directions = mapsDestination(point);
  const links = contactLinks(point.contact_phone);
  return (
    <div className="rounded-card border border-line p-4">
      <h3 className="text-sm font-semibold text-ink">{title}</h3>
      <p className="mt-1 text-sm text-ink">{point.address || "Address unavailable"}</p>
      {point.contact_name && <p className="mt-1 text-sm text-ink-soft">{point.contact_name}</p>}
      <div className="mt-3 flex flex-wrap gap-3 text-sm">
        {directions && <a href={directions} target="_blank" rel="noopener noreferrer" className="text-brass-deep underline">Navigate with Google Maps</a>}
        {links && <a href={links.call} className="text-brass-deep underline">Call</a>}
        {links && <a href={links.whatsapp} target="_blank" rel="noopener noreferrer" className="text-brass-deep underline">WhatsApp</a>}
      </div>
      {!directions && <p className="mt-2 text-xs text-ink-soft">This stop needs a confirmed GPS pin for navigation.</p>}
    </div>
  );
}

export function DispatchTripCard({ trip }: { trip: DeliveryTrip }) {
  return (
    <section className="space-y-3" aria-label="Delivery itinerary">
      <Waypoint title="Pickup point" point={trip.pickup} />
      <Waypoint title="Customer drop-off" point={trip.dropoff} />
      {trip.straight_line_km != null && <p className="text-xs text-ink-soft">
        Approximately {trip.straight_line_km.toFixed(1)} km straight-line distance.
        This is not a driving distance, route ETA or delivery fee estimate.
      </p>}
    </section>
  );
}
