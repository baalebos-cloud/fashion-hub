import { useState } from "react";
import { apiClient } from "@/lib/api/client";
import { formatNaira } from "@/lib/formatters/currency";
import { DispatchAction } from "./DispatchAction";

interface CourierQuote {
  courier: string; name: string; available: boolean; reason?: string;
  quote_id?: string; amount_ngn?: number; eta_minutes?: number | null;
}

/** Dispatcher: price this job with outside courier companies and book one (audited). */
export function CourierCompanies({ requestId, onBooked }: { requestId: string; onBooked: () => void }) {
  const [open, setOpen] = useState(false);
  const [quotes, setQuotes] = useState<CourierQuote[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setError(null);
    setQuotes(null);
    try {
      setQuotes((await apiClient.get<CourierQuote[]>(`/admin/dispatch/requests/${requestId}/courier-quotes`)).data);
    } catch {
      setError("Couldn't get courier prices.");
    }
  }

  return (
    <div>
      <button type="button" aria-expanded={open} className="min-h-11 self-start text-[13px] font-semibold text-indigo"
        onClick={() => { const next = !open; setOpen(next); if (next) void load(); }}>
        {open ? "Hide courier companies" : "Courier companies"}
      </button>
      {open && (
        <div className="mt-2 flex flex-col gap-2">
          {error && <p role="alert" className="text-xs text-thread">{error}</p>}
          {!error && quotes === null && <p className="text-xs text-ink-soft">Getting prices…</p>}
          {quotes?.length === 0 && <p className="text-xs text-ink-soft">No courier companies are switched on.</p>}
          {quotes?.map((quote) => (
            <div key={quote.courier} className="rounded-lg border border-line p-2 text-xs">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <span className="font-medium text-ink">{quote.name}</span>
                {quote.available
                  ? <span className="tabular-nums text-ink">{formatNaira(quote.amount_ngn ?? 0)}{quote.eta_minutes ? ` · ~${quote.eta_minutes} min` : ""}</span>
                  : <span className="text-ink-soft">{quote.reason}</span>}
              </div>
              {quote.available && quote.quote_id && (
                <div className="mt-1">
                  <DispatchAction label="Book" confirmLabel={`Book ${quote.name}`}
                    onConfirm={async (reason) => {
                      await apiClient.post(`/admin/dispatch/requests/${requestId}/courier-booking`,
                        { courier: quote.courier, quote_id: quote.quote_id, reason });
                      onBooked();
                    }} />
                </div>
              )}
            </div>
          ))}
          <p className="text-xs text-ink-soft">The price is recorded on the delivery; nothing is charged or paid from here.</p>
        </div>
      )}
    </div>
  );
}
