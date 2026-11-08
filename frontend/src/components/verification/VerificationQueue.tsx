import { useEffect, useState } from "react";
import { verificationApi } from "@/api/verification.api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { DateTimeDisplay } from "@/components/common/DateTimeDisplay";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import type { VerificationQueueItem } from "@/types/verification";

const ROLE: Record<string, string> = { tailor: "Tailor", designer: "Designer", vendor: "Vendor", delivery_partner: "Rider" };

function RegistryCheck({ item, kind }: { item: VerificationQueueItem; kind: "kyc" | "kyb" }) {
  const registry = kind === "kyc" ? "NIN record" : "CAC record";
  if (!item.registry_checked) {
    return <p className="rounded-control bg-warning-wash px-3 py-2 text-[13px] text-warning">
      {registry} couldn't be checked automatically (provider unavailable or not enabled). Compare the documents by hand.
    </p>;
  }
  return (
    <p className={item.name_match === false
      ? "rounded-control bg-danger-wash px-3 py-2 text-[13px] text-thread"
      : "rounded-control bg-success-wash px-3 py-2 text-[13px] text-success"}>
      {registry}: <span className="font-medium">{item.official_name}</span>
      {item.name_match === false ? " — doesn't match the name on the account. Approving needs an override note." : " — matches."}
    </p>
  );
}

function QueueCard({ item, kind, onDone }: { item: VerificationQueueItem; kind: "kyc" | "kyb"; onDone: () => void }) {
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState<"approve" | "reject" | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function decide(approve: boolean) {
    if (!approve && !reason.trim()) { setError("Add a reason so the applicant knows what to fix."); return; }
    setBusy(approve ? "approve" : "reject");
    setError(null);
    try {
      await verificationApi.review(kind, item.id, approve, reason);
      onDone();
    } catch (err) {
      setError(getDisplayErrorMessage(err, "The decision couldn't be saved."));
    } finally {
      setBusy(null);
    }
  }

  async function open(documentId: string) {
    try { await verificationApi.openDocument(documentId); }
    catch { setError("The document couldn't be opened."); }
  }

  return (
    <Card className="flex flex-col gap-3 p-5">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="font-semibold text-ink">{item.applicant_name}</p>
          <p className="text-[13px] text-ink-soft">
            {ROLE[item.applicant_role] ?? item.applicant_role}
            {item.business_name && ` · ${item.business_name}`}
            {item.registration && ` · ${item.registration}`}
          </p>
        </div>
        <span className="text-[13px] text-ink-soft">Submitted <DateTimeDisplay value={item.submitted_at} format="relative" /></span>
      </div>
      <RegistryCheck item={item} kind={kind} />
      <div className="flex flex-wrap gap-2">
        {item.documents.length === 0 && <span className="text-xs text-thread">No documents attached.</span>}
        {item.documents.map((doc, i) => (
          <Button key={doc.id} size="sm" variant="secondary" onClick={() => void open(doc.id)}>View document {i + 1}</Button>
        ))}
      </div>
      <label className="flex flex-col gap-1.5 text-sm font-semibold text-ink">
        Note to applicant (required to reject or to override a name mismatch)
        <textarea value={reason} onChange={(e) => setReason(e.target.value)} rows={2} maxLength={1000}
          className="w-full rounded-control border border-line-strong bg-surface px-3 py-2 text-base font-normal text-ink focus:border-indigo focus:outline-none" />
        <span className="text-[13px] font-normal text-ink-soft">Saved to the audit log with your decision.</span>
      </label>
      {error && <p role="alert" className="text-sm text-thread">{error}</p>}
      <div className="flex gap-2">
        <Button size="sm" onClick={() => void decide(true)} isLoading={busy === "approve"} disabled={busy !== null}>Approve</Button>
        <Button size="sm" variant="danger" onClick={() => void decide(false)} isLoading={busy === "reject"} disabled={busy !== null}>Reject</Button>
      </div>
    </Card>
  );
}

/** Admin review queue for open KYC or KYB submissions, oldest first. */
export function VerificationQueue({ kind }: { kind: "kyc" | "kyb" }) {
  const [items, setItems] = useState<VerificationQueueItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const title = kind === "kyc" ? "Identity checks" : "Business checks";

  useEffect(() => {
    let active = true;
    verificationApi.queue(kind).then((data) => { if (active) { setItems(data); setError(null); } })
      .catch((err) => { if (active) setError(getDisplayErrorMessage(err, "The review queue couldn't be loaded.")); });
    return () => { active = false; };
  }, [kind, tick]);

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-col gap-1">
          <h1 className="font-display text-3xl text-ink">{title}</h1>
          <p className="text-sm text-ink-soft">{kind === "kyc" ? "NIN for tailors, designers and riders." : "CAC registration for vendors and studios."} Oldest first.</p>
        </div>
        {items && <Badge tone={items.length > 0 ? "warning" : "neutral"}>{items.length} waiting</Badge>}
      </div>
      {error && <p role="alert" className="text-sm text-thread">{error}</p>}
      {items && items.length === 0 && <EmptyState title="Nothing to review" description="New submissions appear here, oldest first." />}
      {items?.map((item) => (
        <QueueCard key={item.id} item={item} kind={kind} onDone={() => setTick((t) => t + 1)} />
      ))}
    </div>
  );
}
