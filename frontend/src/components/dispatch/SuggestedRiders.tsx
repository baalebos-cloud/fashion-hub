import { useState } from "react";
import { adminDispatchApi, type RiderSuggestion } from "@/api/admin-dispatch.api";
import { DispatchAction } from "./DispatchAction";

const VEHICLE: Record<string, string> = { bike: "Motorbike", car: "Car", van: "Van", foot: "On foot" };

/** Dispatcher view of the best riders for a waiting job, each with a score and the reasons.
 * Advisory: the dispatcher chooses, and every manual assignment needs a reason for the audit log. */
export function SuggestedRiders({ requestId, onAssigned }: { requestId: string; onAssigned: () => void }) {
  const [open, setOpen] = useState(false);
  const [rows, setRows] = useState<RiderSuggestion[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function toggle() {
    const next = !open;
    setOpen(next);
    if (!next) return;
    setError(null);
    setRows(null);
    try {
      setRows(await adminDispatchApi.candidates(requestId));
    } catch {
      setError("Couldn't load suggestions.");
    }
  }

  return (
    <div>
      <button type="button" onClick={() => void toggle()} aria-expanded={open} className="text-xs font-medium text-brass-deep underline">
        {open ? "Hide suggested riders" : "Suggested riders"}
      </button>
      {open && (
        <div className="mt-2 flex flex-col gap-2">
          {error && <p role="alert" className="text-xs text-thread">{error}</p>}
          {!error && rows === null && <p className="text-xs text-ink-soft">Ranking riders…</p>}
          {rows?.length === 0 && <p className="text-xs text-ink-soft">No eligible rider is online right now.</p>}
          {rows?.map((row, index) => (
            <div key={row.partner_id} className="rounded-lg border border-line p-2 text-xs">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <span className="font-medium text-ink">
                  {index + 1}. {row.first_name}
                  <span className="ml-1 font-normal text-ink-soft">{row.vehicle_type ? VEHICLE[row.vehicle_type] ?? row.vehicle_type : ""}</span>
                </span>
                <span className="tabular-nums text-ink" aria-label={`Score ${row.score} out of 100`}>{row.score}/100</span>
              </div>
              <p className="mt-0.5 text-ink-soft">{row.explanation}</p>
              <div className="mt-1">
                <DispatchAction label="Assign" confirmLabel={`Assign to ${row.first_name}`}
                  onConfirm={async (reason) => { await adminDispatchApi.assignWaiting(requestId, row.partner_id, reason); onAssigned(); }} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
