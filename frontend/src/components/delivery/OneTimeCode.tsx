import { useEffect, useState } from "react";
import { DateTimeDisplay } from "@/components/common/DateTimeDisplay";
import { getDisplayErrorMessage } from "@/lib/utils/errors";

/**
 * Shows a one-time six-digit code with its expiry and a "new code" action. When the code
 * lapses it fetches the replacement automatically, so the holder never reads out a dead code.
 */
export function OneTimeCode({ label, hint, load, rotate }: {
  label: string;
  hint: string;
  load: () => Promise<{ code: string; expiresAt: string }>;
  rotate: () => Promise<{ code: string; expiresAt: string }>;
}) {
  const [current, setCurrent] = useState<{ code: string; expiresAt: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(action: () => Promise<{ code: string; expiresAt: string }>) {
    setBusy(true);
    setError(null);
    try {
      setCurrent(await action());
    } catch (err) {
      setCurrent(null);
      setError(getDisplayErrorMessage(err, "The code is unavailable right now."));
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => { void run(load); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!current) return;
    const wait = new Date(current.expiresAt).getTime() - Date.now();
    const timer = window.setTimeout(() => void run(load), Math.max(1000, wait + 500));
    return () => window.clearTimeout(timer);
  }, [current]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="rounded-lg bg-muslin px-3 py-3" role="region" aria-label={label}>
      <p className="text-xs text-ink-soft">{label}</p>
      {current ? (
        <>
          <p className="font-display text-3xl tracking-[0.3em] text-ink" data-testid="one-time-code">{current.code}</p>
          <p className="text-xs text-ink-soft">
            Works once. Expires <DateTimeDisplay value={current.expiresAt} format="relative" />.
          </p>
        </>
      ) : !error && <p className="text-sm text-ink-soft">Loading code…</p>}
      <p className="mt-1 text-xs text-ink-soft">{hint}</p>
      <button type="button" disabled={busy} onClick={() => void run(rotate)}
        className="mt-2 text-xs font-medium text-brass-deep underline disabled:opacity-50">
        Get a new code
      </button>
      {error && <p role="alert" className="mt-1 text-xs text-thread">{error}</p>}
    </div>
  );
}
