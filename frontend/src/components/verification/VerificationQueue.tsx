import { useEffect, useState } from "react";
import { endReviewWindow, hasReviewWindow, verificationApi } from "@/api/verification.api";
import { isApiError } from "@/lib/api/errors";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Modal } from "@/components/ui/modal";
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

const RULE_LABEL: Record<"kyc" | "kyb", Record<string, string>> = {
  kyc: {
    record_found: "NIN record found",
    name_matches: "Name matches the NIN record",
    date_of_birth_matches: "Date of birth matches the NIN record",
    profile_photo: "Has a profile photo",
    nin_not_used_elsewhere: "NIN not used on another account",
    document_readable: "Document is a clear identity document",
    document_name_matches: "Name on the document matches the account",
    document_date_of_birth_matches: "Date of birth on the document matches",
    document_nin_matches: "NIN on the document matches",
    document_not_expired: "Document hasn't expired",
    document_not_edited: "Document shows no signs of editing",
    selfie_matches_nin: "Live selfie matches the NIN record photo",
    profile_photo_matches_nin: "Profile photo matches the NIN record photo",
  },
  kyb: {
    record_found: "CAC record found",
    company_active: "Company is active on the CAC register",
    business_name_matches: "Business name matches the CAC record",
    identity_verified: "Owner's identity (NIN) is verified",
    owner_listed: "Owner is listed as a director, proprietor or shareholder",
    profile_photo: "Has a profile photo",
    registration_not_used_elsewhere: "Registration number not used on another account",
  },
};

/** Why a check wasn't approved automatically. */
function AutoChecks({ checks, kind }: { checks: Record<string, boolean>; kind: "kyc" | "kyb" }) {
  const failed = Object.entries(checks).filter(([, ok]) => !ok);
  if (failed.length === 0) return null;
  return (
    <div className="rounded-control border border-line bg-paper px-3 py-2 text-[13px]">
      <p className="font-semibold text-ink">Not approved automatically because:</p>
      <ul className="mt-1 list-disc pl-5 text-ink-soft">
        {failed.map(([key]) => <li key={key}>{RULE_LABEL[kind][key] ?? key}: no</li>)}
      </ul>
    </div>
  );
}

function QueueCard({ item, kind, onDone }: { item: VerificationQueueItem; kind: "kyc" | "kyb"; onDone: () => void }) {
  // Tailora's document note pre-fills the note to the applicant; the reviewer can edit it.
  const [reason, setReason] = useState(item.document_checked ? item.document_note ?? "" : "");
  const [busy, setBusy] = useState<"approve" | "reject" | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Set when a decision is waiting on a fresh authenticator code.
  const [asking, setAsking] = useState<boolean | null>(null);
  const [code, setCode] = useState("");

  async function submit(approve: boolean) {
    setBusy(approve ? "approve" : "reject");
    setError(null);
    try {
      await verificationApi.review(kind, item.id, approve, reason);
      onDone();
    } catch (err) {
      if (isApiError(err) && err.code === "step_up_required") {
        endReviewWindow();
        setAsking(approve);
        setError("Your review window has ended. Enter a new code.");
      } else {
        setError(getDisplayErrorMessage(err, "The decision couldn't be saved."));
      }
    } finally {
      setBusy(null);
    }
  }

  async function decide(approve: boolean) {
    if (!approve && !reason.trim()) { setError("Add a reason so the applicant knows what to fix."); return; }
    if (!hasReviewWindow()) { setError(null); setCode(""); setAsking(approve); return; }
    await submit(approve);
  }

  async function confirmCode() {
    if (asking === null) return;
    const approve = asking;
    setBusy(approve ? "approve" : "reject");
    setError(null);
    try {
      await verificationApi.openReviewWindow(code);
    } catch (err) {
      setBusy(null);
      setCode("");
      setError(getDisplayErrorMessage(err, "That code didn't work. Enter the newest code from your authenticator app."));
      return;
    }
    setAsking(null);
    setCode("");
    await submit(approve);
  }

  const [viewing, setViewing] = useState<{ url: string; type: string; label: string } | null>(null);
  const [checking, setChecking] = useState(false);
  const [note, setNote] = useState<string | null>(item.document_note ?? null);
  const [noteChecked, setNoteChecked] = useState(item.document_checked ?? false);
  const [checks, setChecks] = useState(item.auto_checks ?? null);

  async function open(documentId: string, label: string) {
    setError(null);
    try { setViewing({ ...(await verificationApi.loadDocument(documentId)), label }); }
    catch (err) { setError(getDisplayErrorMessage(err, "The document couldn't be opened.")); }
  }

  function closeViewer() {
    if (viewing) URL.revokeObjectURL(viewing.url);
    setViewing(null);
  }

  async function runCheck() {
    setChecking(true);
    setError(null);
    try {
      const result = await verificationApi.checkDocument(item.id);
      setNote(result.document_note);
      setChecks(result.checks);
      setNoteChecked(result.checked);
      if (result.checked && !reason.trim()) setReason(result.document_note);
    } catch (err) {
      setError(getDisplayErrorMessage(err, "Tailora couldn't check the document. Try again."));
    } finally {
      setChecking(false);
    }
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
      {checks && <AutoChecks checks={checks} kind={kind} />}
      {kind === "kyc" && item.face && (
        <p className="text-[13px] text-ink-soft">
          Face match with the NIN photo:{" "}
          {[["Selfie", "selfie"], ["Profile photo", "profile_photo"]].map(([label, key]) => {
            const confidence = item.face?.[`${key}_confidence`];
            const problem = item.face?.[`${key}_problem`];
            return <span key={key} className="mr-3">{label} {confidence != null ? `${confidence}%` : `not checked (${problem ?? "no result"})`}</span>;
          })}
        </p>
      )}
      {kind === "kyc" && (note ? (
        <div className={noteChecked
          ? "rounded-control border border-indigo/30 bg-indigo-wash px-3 py-2 text-[13px] text-ink"
          : "rounded-control border border-warning/30 bg-warning-wash px-3 py-2 text-[13px] text-ink"}>
          <p className="font-semibold">Tailora's document check</p>
          <p className="mt-1 text-ink-soft">{note}</p>
          {!noteChecked && item.documents.length > 0 && (
            <Button size="sm" variant="secondary" className="mt-2" isLoading={checking} onClick={() => void runCheck()}>
              Try the check again
            </Button>
          )}
        </div>
      ) : item.documents.length > 0 && (
        <Button size="sm" variant="secondary" className="self-start" isLoading={checking} onClick={() => void runCheck()}>
          Check document with Tailora
        </Button>
      ))}
      <div className="flex flex-wrap gap-2">
        {item.documents.length === 0 && <span className="text-xs text-thread">No documents attached.</span>}
        {item.documents.map((doc, i) => (
          <Button key={doc.id} size="sm" variant="secondary" onClick={() => void open(doc.id, doc.type === "selfie" ? "Selfie" : `Document ${i + 1}`)}>
            {doc.type === "selfie" ? "View selfie" : `View document ${i + 1}`}
          </Button>
        ))}
      </div>
      <label className="flex flex-col gap-1.5 text-sm font-semibold text-ink">
        Note to applicant (required to reject or to override a name mismatch)
        <textarea value={reason} onChange={(e) => setReason(e.target.value)} rows={2} maxLength={1000}
          className="w-full rounded-control border border-line-strong bg-surface px-3 py-2 text-base font-normal text-ink focus:border-indigo focus:outline-none" />
        <span className="text-[13px] font-normal text-ink-soft">Saved to the audit log with your decision.</span>
      </label>
      {asking !== null && (
        <div className="flex flex-col gap-2 rounded-control border border-indigo/30 bg-indigo-wash p-3">
          <label htmlFor={`code-${item.id}`} className="text-sm font-semibold text-ink">
            Code from your authenticator app
          </label>
          <div className="flex flex-wrap gap-2">
            <input id={`code-${item.id}`} inputMode="numeric" autoComplete="one-time-code" maxLength={6} value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
              className="min-h-11 w-32 rounded-control border border-line-strong bg-surface px-3 font-mono text-lg tracking-widest text-ink focus:border-indigo focus:outline-none" />
            <Button size="sm" variant={asking ? "primary" : "danger"} disabled={code.length !== 6 || busy !== null}
              isLoading={busy !== null} onClick={() => void confirmCode()}>
              {asking ? "Confirm and approve" : "Confirm and reject"}
            </Button>
            <Button size="sm" variant="ghost" disabled={busy !== null} onClick={() => { setAsking(null); setCode(""); setError(null); }}>Cancel</Button>
          </div>
          <p className="text-[13px] text-ink-soft">One code covers your decisions for the next 5 minutes.</p>
        </div>
      )}
      {error && <p role="alert" className="text-sm text-thread">{error}</p>}
      {asking === null && (
        <p className="text-[13px] text-ink-soft">
          Approving or rejecting asks for the 6-digit code from your authenticator app (the one you use to sign in as admin).
        </p>
      )}
      <div className="flex gap-2">
        <Button size="sm" onClick={() => void decide(true)} isLoading={busy === "approve" && asking === null} disabled={busy !== null || asking !== null}>Approve</Button>
        <Button size="sm" variant="danger" onClick={() => void decide(false)} isLoading={busy === "reject" && asking === null} disabled={busy !== null || asking !== null}>Reject</Button>
      </div>
      <Modal isOpen={viewing !== null} onClose={closeViewer} title={viewing?.label} className="max-w-3xl">
        {viewing && (viewing.type.startsWith("image/")
          ? <img src={viewing.url} alt={`${item.applicant_name}'s ${viewing.label.toLowerCase()}`} className="max-h-[70vh] w-full rounded-control object-contain" />
          : viewing.type === "application/pdf"
            ? <iframe src={viewing.url} title={viewing.label} className="h-[70vh] w-full rounded-control border border-line" />
            : <p className="text-sm text-ink-soft">This file type can't be shown here.</p>)}
        <div className="mt-3 flex justify-end">
          <Button size="sm" variant="secondary" onClick={closeViewer}>Close</Button>
        </div>
      </Modal>
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
