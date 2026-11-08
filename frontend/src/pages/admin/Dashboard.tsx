import { useEffect, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { dashboardApi, type CommerceSummary } from "@/api/dashboard.api";
import { adminOperationsApi, type AdminOperations } from "@/api/admin-operations.api";
import { adminDispatchApi, type AdminDispatchBoard } from "@/api/admin-dispatch.api";
import { adminSecurityApi, type ActivitySummary } from "@/api/admin-security.api";
import { verificationApi } from "@/api/verification.api";
import { DateTimeDisplay } from "@/components/common/DateTimeDisplay";
import type { VerificationQueueItem } from "@/types/verification";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/error-state";
import { SkeletonRows } from "@/components/ui/skeleton";
import { adminRoutes } from "@/config/routes.config";
import { cn } from "@/lib/utils/cn";

const ROLE_LABEL: Record<string, string> = {
  customer: "Customers", tailor: "Tailors", designer: "Designers", vendor: "Vendors", delivery_partner: "Riders",
};
const ISSUE_LABEL: Record<string, string> = {
  CUSTOMER_UNREACHABLE: "Customer unreachable", WRONG_ADDRESS: "Wrong address", PACKAGE_DAMAGED: "Package damaged",
  TRAFFIC_ACCIDENT_DELAY: "Traffic or accident delay", RECIPIENT_REJECTED: "Recipient rejected", VEHICLE_BREAKDOWN: "Vehicle breakdown",
};
const humanize = (s: string) => s.replace(/[._]/g, " ").replace(/^\w/, (c) => c.toUpperCase());

function Tile({ label, value, hint, to, alert }: { label: string; value: number | null; hint: string; to: string; alert: boolean }) {
  return (
    <Link to={to} className={cn("flex flex-col gap-1 rounded-card border bg-surface p-4 transition-colors hover:border-indigo",
      alert ? "border-thread/40" : "border-line")}>
      <span className="text-[13px] text-ink-soft">{label}</span>
      <span className={cn("font-display text-3xl", alert ? "text-thread" : "text-ink")}>{value ?? "—"}</span>
      <span className="text-xs text-ink-soft">{value == null ? "Couldn't load" : hint}</span>
    </Link>
  );
}

function HealthRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <li className="flex items-center justify-between gap-3 py-2 text-sm">
      <span className="text-ink">{label}</span>
      {children}
    </li>
  );
}

/** Admin overview: what needs a decision now, the verification queue, and read-only platform switches. */
export default function Dashboard() {
  const [ops, setOps] = useState<AdminOperations | null>(null);
  const [opsLoading, setOpsLoading] = useState(true);
  const [opsError, setOpsError] = useState(false);
  const [opsRevision, setOpsRevision] = useState(0);
  const [board, setBoard] = useState<AdminDispatchBoard | null>(null);
  const [security, setSecurity] = useState<ActivitySummary | null>(null);
  const [commerce, setCommerce] = useState<CommerceSummary | null>(null);
  const [checks, setChecks] = useState<Array<VerificationQueueItem & { kind: "kyc" | "kyb" }> | null>(null);

  useEffect(() => {
    let active = true;
    setOpsLoading(true); setOpsError(false);
    adminOperationsApi.operations()
      .then((data) => { if (active) setOps(data); })
      .catch(() => { if (active) setOpsError(true); })
      .finally(() => { if (active) setOpsLoading(false); });
    return () => { active = false; };
  }, [opsRevision]);

  useEffect(() => {
    // Each source loads on its own, so one failing doesn't blank the whole page.
    adminDispatchApi.board().then(setBoard).catch(() => setBoard(null));
    adminSecurityApi.summary().then(setSecurity).catch(() => setSecurity(null));
    dashboardApi.getCommerceSummary().then(setCommerce).catch(() => setCommerce(null));
  }, []);

  useEffect(() => {
    let active = true;
    Promise.all([verificationApi.queue("kyc"), verificationApi.queue("kyb")])
      .then(([kyc, kyb]) => {
        if (!active) return;
        const all = [...kyc.map((x) => ({ ...x, kind: "kyc" as const })), ...kyb.map((x) => ({ ...x, kind: "kyb" as const }))];
        setChecks(all.sort((a, b) => a.submitted_at.localeCompare(b.submitted_at)));
      })
      .catch(() => { if (active) setChecks(null); });
    return () => { active = false; };
  }, [opsRevision]);

  const pendingChecks = ops ? ops.verification.kyc_pending.length + ops.verification.kyb_pending.length : null;
  const openIssues = ops ? ops.delivery_issues.filter((x) => x.status !== "RESOLVED") : [];
  const topIp = security?.top_failed_ips[0];

  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-col gap-1">
          <h1 className="font-display text-3xl text-ink">Overview</h1>
          <p className="text-sm text-ink-soft">What needs a decision now. Every action here is written to the audit log.</p>
        </div>
        <Button variant="secondary" disabled={opsLoading} onClick={() => setOpsRevision((n) => n + 1)}>Refresh</Button>
      </div>

      <section aria-label="Needs your attention" className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Tile label="Verification" value={pendingChecks} to={(ops?.verification.kyc_pending.length ?? 0) > 0 || !ops ? adminRoutes.kyc : adminRoutes.kyb} alert={(pendingChecks ?? 0) > 0}
          hint={ops ? `${ops.verification.kyc_pending.length} identity · ${ops.verification.kyb_pending.length} business` : ""} />
        <Tile label="No rider yet" value={board?.unassigned_count ?? null} to={adminRoutes.deliveries} alert={(board?.unassigned_count ?? 0) > 0}
          hint={board ? `${board.available_verified_riders} verified rider${board.available_verified_riders === 1 ? "" : "s"} online` : ""} />
        <Tile label="Rider issues" value={board?.open_issue_count ?? null} to={adminRoutes.deliveries} alert={(board?.open_issue_count ?? 0) > 0}
          hint={openIssues[0] ? ISSUE_LABEL[openIssues[0].type] ?? humanize(openIssues[0].type) : "Nothing reported"} />
        <Tile label="Failed sign-ins (24 h)" value={security?.failed_sign_ins_24h ?? null} to={adminRoutes.security}
          alert={(security?.failed_sign_ins_24h ?? 0) >= 10}
          hint={topIp ? `${topIp.attempts} from one address` : "No repeated failures"} />
      </section>

      {opsLoading && !ops && <SkeletonRows rows={3} label="Loading the overview" onRetry={() => setOpsRevision((n) => n + 1)} />}
      {!opsLoading && opsError && (
        <ErrorState title="Couldn't load the overview" description="Check your connection and administrator access, then try again."
          onRetry={() => setOpsRevision((n) => n + 1)} />
      )}

      {ops && (
        <div className="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
          <div className="flex flex-col gap-6">
            <section aria-label="Waiting for verification" className="flex flex-col gap-3">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h2 className="font-display text-2xl text-ink">Waiting for verification</h2>
                <span className="flex gap-4 text-sm font-semibold">
                  <Link to={adminRoutes.kyc} className="text-indigo">Identity checks</Link>
                  <Link to={adminRoutes.kyb} className="text-indigo">Business checks</Link>
                </span>
              </div>
              {checks === null && <p className="text-sm text-ink-soft">The review queue couldn't be loaded. Open Identity checks or Business checks.</p>}
              {checks?.length === 0 && (
                <p className="rounded-card border border-dashed border-line-strong bg-surface p-6 text-center text-sm text-ink-soft">No checks waiting.</p>
              )}
              {checks && checks.length > 0 && (
                <ul className="flex flex-col divide-y divide-line overflow-hidden rounded-card border border-line bg-surface">
                  {checks.slice(0, 6).map((item) => (
                    <li key={`${item.kind}-${item.id}`}>
                      <Link to={item.kind === "kyc" ? adminRoutes.kyc : adminRoutes.kyb}
                        className="flex flex-wrap items-center gap-x-4 gap-y-1.5 p-4 transition-colors hover:bg-paper">
                        <span className="flex min-w-0 flex-1 flex-col">
                          <span className="truncate font-semibold text-ink">{item.business_name ?? item.applicant_name}</span>
                          <span className="text-[13px] text-ink-soft">
                            {ROLE_LABEL[item.applicant_role]?.replace(/s$/, "") ?? humanize(item.applicant_role)} · {item.kind === "kyc" ? "identity (NIN)" : "business (CAC)"} ·{" "}
                            submitted <DateTimeDisplay value={item.submitted_at} format="relative" />
                          </span>
                        </span>
                        {!item.registry_checked ? <Badge tone="warning">Check by hand</Badge>
                          : item.name_match === false ? <Badge tone="danger">Name mismatch</Badge>
                          : <Badge tone="success">Name matched</Badge>}
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section aria-label="Recent admin activity" className="flex flex-col gap-3">
              <div className="flex items-baseline justify-between">
                <h2 className="font-display text-2xl text-ink">Recent activity</h2>
                <Link to={adminRoutes.auditLogs} className="text-sm font-semibold text-indigo">Audit log</Link>
              </div>
              {ops.audit_events.length === 0 ? (
                <p className="text-sm text-ink-soft">Nothing recorded yet.</p>
              ) : (
                <ul className="flex flex-col divide-y divide-line overflow-hidden rounded-card border border-line bg-surface">
                  {ops.audit_events.slice(0, 8).map((event) => (
                    <li key={event.id} className="px-4 py-2.5 text-sm text-ink">{humanize(event.action)}</li>
                  ))}
                </ul>
              )}
            </section>
          </div>

          <div className="flex flex-col gap-6">
            <section aria-label="Platform switches" className="flex flex-col gap-1 rounded-card border border-line bg-surface p-4">
              <h2 className="font-semibold text-ink">Platform switches</h2>
              <ul className="flex flex-col divide-y divide-line">
                <HealthRow label="Payments">
                  {ops.financial_controls.production_payments_enabled ? <Badge tone="success">On</Badge> : <Badge tone="neutral">Switched off</Badge>}
                </HealthRow>
                <HealthRow label="Ledger">
                  {ops.financial_controls.ledger_balanced ? <Badge tone="success">Balanced</Badge> : <Badge tone="danger">Needs investigation</Badge>}
                </HealthRow>
                <HealthRow label="Auto-offers to riders">
                  {board == null ? <span className="text-[13px] text-ink-soft">Couldn't load</span>
                    : board.auto_offers_enabled ? <Badge tone="success">On</Badge> : <Badge tone="neutral">Switched off</Badge>}
                </HealthRow>
              </ul>
              <p className="pt-1 text-xs text-ink-soft">Read-only. These change only in the backend settings.</p>
            </section>

            <section aria-label="People" className="flex flex-col gap-2 rounded-card border border-line bg-surface p-4">
              <div className="flex items-baseline justify-between">
                <h2 className="font-semibold text-ink">Active accounts</h2>
                <Link to={adminRoutes.users} className="text-sm font-semibold text-indigo">Users</Link>
              </div>
              <dl className="grid grid-cols-2 gap-x-4 gap-y-2">
                {Object.entries(ops.marketplace).map(([role, count]) => (
                  <div key={role} className="flex flex-col">
                    <dt className="text-[13px] text-ink-soft">{ROLE_LABEL[role] ?? humanize(role)}</dt>
                    <dd className="font-mono text-lg text-ink">{count.toLocaleString()}</dd>
                  </div>
                ))}
              </dl>
            </section>

            {commerce && (
              <section aria-label="Verified payments" className="flex flex-col gap-2 rounded-card border border-line bg-surface p-4">
                <h2 className="font-semibold text-ink">Verified payments</h2>
                <dl className="grid grid-cols-2 gap-4">
                  <div><dt className="text-[13px] text-ink-soft">Count</dt><dd className="font-mono text-lg text-ink">{commerce.verified_count}</dd></div>
                  <div><dt className="text-[13px] text-ink-soft">Volume</dt><dd className="font-mono text-lg text-ink">₦{Number(commerce.verified_volume_ngn).toLocaleString("en-NG")}</dd></div>
                </dl>
                <p className="text-xs text-ink-soft">{commerce.note}</p>
              </section>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
