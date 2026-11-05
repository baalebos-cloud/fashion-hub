import { useState } from "react";
import { adminDispatchApi, type DeliveryEvent } from "@/api/admin-dispatch.api";
import { DateTimeDisplay } from "@/components/common/DateTimeDisplay";

const LABELS: Record<string, string> = {
  pickup_code_issued: "Pickup code issued to seller",
  pickup_verification_failed: "Wrong pickup code entered",
  picked_up: "Package collected",
  handover_code_issued: "Handover code issued to buyer",
  handover_verification_failed: "Wrong handover code entered",
  delivered: "Delivered",
  rider_released: "Rider released by dispatch",
  rider_reassigned: "Moved to another rider",
};

function describe(event: DeliveryEvent): string {
  const label = LABELS[event.event_type] ?? event.event_type.replaceAll("_", " ");
  const details = event.details ?? {};
  const extra = [
    typeof details.package_count === "number" ? `${details.package_count} package${details.package_count === 1 ? "" : "s"}` : null,
    details.reason === "rotated" ? "new code requested" : details.reason === "expired" ? "previous code expired" : null,
    details.reason === "locked" ? "too many attempts" : null,
  ].filter(Boolean);
  return extra.length ? `${label} · ${extra.join(" · ")}` : label;
}

/** Admin-only audit trail for one run. Codes themselves are never recorded. */
export function DeliveryEventLog({ deliveryId }: { deliveryId: string }) {
  const [events, setEvents] = useState<DeliveryEvent[] | null>(null);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function toggle() {
    const next = !open;
    setOpen(next);
    if (!next) return;
    setError(null);
    try {
      setEvents(await adminDispatchApi.events(deliveryId));
    } catch {
      setError("Couldn't load the event log.");
    }
  }

  return (
    <div>
      <button type="button" onClick={() => void toggle()} aria-expanded={open}
        className="text-xs font-medium text-brass-deep underline">
        {open ? "Hide event log" : "Event log"}
      </button>
      {open && (
        <div className="mt-2">
          {error && <p role="alert" className="text-xs text-thread">{error}</p>}
          {!error && events === null && <p className="text-xs text-ink-soft">Loading…</p>}
          {events?.length === 0 && <p className="text-xs text-ink-soft">Nothing recorded yet.</p>}
          {events && events.length > 0 && (
            <ol className="flex flex-col gap-1 border-l border-line pl-3">
              {events.map((event) => (
                <li key={event.id} className="text-xs">
                  <span className={event.event_type.endsWith("_failed") ? "text-thread" : "text-ink"}>{describe(event)}</span>
                  <span className="ml-2 text-ink-soft"><DateTimeDisplay value={event.created_at} format="time" /></span>
                </li>
              ))}
            </ol>
          )}
        </div>
      )}
    </div>
  );
}
