import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api/client";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { getDisplayErrorMessage } from "@/lib/utils/errors";

interface EmailStatus {
  ready: boolean;
  provider: string;
  problem: string | null;
  from?: string;
  unverified_accounts: number;
  emails_waiting: number;
  last_error: string | null;
}

/** Admin: is outgoing email working, and send a fresh confirmation link to everyone who never confirmed. */
export function EmailDeliveryCard() {
  const [status, setStatus] = useState<EmailStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      setStatus((await apiClient.get<EmailStatus>("/admin/email/status")).data);
    } catch {
      setError("Couldn't check email delivery.");
    }
  }

  useEffect(() => { void load(); }, []);

  async function sendAll() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const { data } = await apiClient.post<{ queued: number }>("/admin/email/verification-backfill");
      setMessage(`Sending a new confirmation link to ${data.queued} ${data.queued === 1 ? "person" : "people"}. This runs in the background.`);
      await load();
    } catch (err) {
      setError(getDisplayErrorMessage(err, "Couldn't start sending."));
    } finally {
      setBusy(false);
    }
  }

  if (!status && !error) return null;
  return (
    <Card className="mb-6 flex flex-col gap-2 p-4" role="region" aria-label="Email delivery">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-medium text-ink">Email confirmation</h2>
          {status && (
            <p className={status.ready ? "text-xs text-ink-soft" : "text-xs font-medium text-thread"}>
              {status.ready ? `Sending from ${status.from} via ${status.provider}.` : `Email isn't working: ${status.problem}`}
            </p>
          )}
        </div>
        {status && (
          <Button onClick={() => void sendAll()} isLoading={busy}
            disabled={busy || !status.ready || status.unverified_accounts === 0}>
            Email everyone who hasn't confirmed ({status.unverified_accounts})
          </Button>
        )}
      </div>
      {status && status.emails_waiting > 0 && (
        <p className="text-xs text-ink-soft">{status.emails_waiting} confirmation or reset emails are waiting to be sent.</p>
      )}
      {status?.last_error && (
        <p className="rounded-lg bg-muslin px-3 py-2 text-xs text-thread">
          Last refusal from the email provider: {status.last_error}
        </p>
      )}
      {message && <p role="status" className="text-xs text-ink">{message}</p>}
      {error && <p role="alert" className="text-xs text-thread">{error}</p>}
    </Card>
  );
}
