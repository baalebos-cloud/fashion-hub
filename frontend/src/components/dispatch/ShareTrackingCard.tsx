import { useEffect, useState } from "react";
import { trackingLinksApi, type CreatedShareLink, type ShareLinkSummary } from "@/api/tracking-links.api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { DateTimeDisplay } from "@/components/common/DateTimeDisplay";
import { getDisplayErrorMessage } from "@/lib/utils/errors";

/**
 * Lets the buyer share a delivery-only tracking link with whoever is receiving the
 * package (no Tailora account needed). The full link is shown once, when created.
 */
export function ShareTrackingCard({ orderId, orderNumber, allowCreate = true }: {
  orderId: string; orderNumber: string;
  /** False once the order is received/completed: existing links can still be turned off. */
  allowCreate?: boolean;
}) {
  const [links, setLinks] = useState<ShareLinkSummary[]>([]);
  const [created, setCreated] = useState<CreatedShareLink | null>(null);
  const [label, setLabel] = useState("");
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    trackingLinksApi.list(orderId).then((data) => setLinks(Array.isArray(data) ? data : [])).catch(() => setLinks([]));
  }, [orderId, tick]);

  async function create() {
    setBusy(true);
    setError(null);
    try {
      setCreated(await trackingLinksApi.create(orderId, label));
      setLabel("");
      setTick((t) => t + 1);
    } catch (err) {
      setError(getDisplayErrorMessage(err, "Couldn't create a tracking link."));
    } finally {
      setBusy(false);
    }
  }

  async function copy(url: string) {
    try { await navigator.clipboard.writeText(url); setCopied(true); window.setTimeout(() => setCopied(false), 2000); }
    catch { /* the link stays visible to copy by hand */ }
  }

  const active = links.filter((l) => l.active);
  if (!allowCreate && active.length === 0 && !created) return null;
  const whatsapp = created
    ? `https://wa.me/?text=${encodeURIComponent(`Track delivery ${orderNumber} on Tailora: ${created.url}`)}`
    : "";

  return (
    <Card role="region" aria-label="Share tracking" className="flex flex-col gap-3 p-4">
      <div>
        <h2 className="text-sm font-medium text-ink">Share tracking</h2>
        <p className="text-xs text-ink-soft">
          Someone else receiving the package? Send them a link to follow the delivery. They won't see your address,
          phone number, price or handover code, and you can switch the link off any time.
        </p>
      </div>

      {created ? (
        <div className="flex flex-col gap-2 rounded-lg bg-muslin p-3">
          <p className="text-xs text-ink-soft">Copy it now; for your security the full link is only shown once.</p>
          <code className="break-all text-sm text-ink" data-testid="share-url">{created.url}</code>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" onClick={() => void copy(created.url)}>{copied ? "Copied" : "Copy link"}</Button>
            <a href={whatsapp} target="_blank" rel="noopener noreferrer"
              className="inline-flex items-center rounded-lg border border-line px-3 py-1.5 text-sm font-medium text-ink hover:border-brass">
              Share to WhatsApp</a>
            <Button size="sm" variant="ghost" onClick={() => setCreated(null)}>Done</Button>
          </div>
        </div>
      ) : allowCreate && (
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
          <label className="flex-1 text-xs text-ink-soft">
            Who is it for? (optional, only you see this)
            <input value={label} onChange={(e) => setLabel(e.target.value)} maxLength={60} placeholder="e.g. Mum"
              className="mt-1 w-full rounded-lg border border-line bg-paper px-3 py-2 text-sm text-ink focus:border-brass focus:outline-none" />
          </label>
          <Button size="sm" onClick={() => void create()} isLoading={busy}>Create tracking link</Button>
        </div>
      )}
      {error && <p role="alert" className="text-xs text-thread">{error}</p>}

      {active.length > 0 && (
        <ul className="flex flex-col gap-2" aria-label="Active tracking links">
          {active.map((link) => (
            <li key={link.id} className="flex items-center justify-between gap-2 text-sm">
              <span className="min-w-0 text-ink">
                {link.label ?? "Tracking link"}
                <span className="block text-xs text-ink-soft">
                  Viewed {link.access_count} time{link.access_count === 1 ? "" : "s"} · works until{" "}
                  <DateTimeDisplay value={link.expires_at} format="date" />
                </span>
              </span>
              <Button size="sm" variant="ghost" onClick={async () => { await trackingLinksApi.revoke(orderId, link.id); setTick((t) => t + 1); }}>
                Turn off
              </Button>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
