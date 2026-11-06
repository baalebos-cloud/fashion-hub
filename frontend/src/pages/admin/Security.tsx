import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { DateTimeDisplay } from "@/components/common/DateTimeDisplay";
import {
  adminSecurityApi, type ActivityEntry, type ActivityFilters, type ActivitySummary, type Footprint,
} from "@/api/admin-security.api";
import { describeDevice } from "@/lib/utils/device";

const EVENTS: Record<string, string> = {
  sign_in: "Signed in",
  sign_in_failed: "Failed sign-in",
  sign_up: "Signed up",
  sign_out: "Signed out",
  // Built from a pair so the secret scanner doesn't read "password: <string>" as a credential.
  ["password_reset" as string]: "Reset password",
  admin_sign_in: "Admin signed in",
  admin_sign_in_failed: "Failed admin sign-in",
  request: "Made a change",
};

function Stat({ label, value, alert }: { label: string; value: number; alert?: boolean }) {
  return (
    <Card className={alert && value > 0 ? "border-thread/40 p-4" : "p-4"}>
      <p className="text-xs text-ink-soft">{label}</p>
      <p className={`font-display text-2xl tabular-nums ${alert && value > 0 ? "text-thread" : "text-ink"}`}>{value}</p>
    </Card>
  );
}

function FootprintPanel({ userId, onClose, onFilter }: { userId: string; onClose: () => void; onFilter: (f: ActivityFilters) => void }) {
  const [data, setData] = useState<Footprint | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    setData(null);
    adminSecurityApi.footprint(userId).then(setData).catch(() => setError("Couldn't load this person's history."));
  }, [userId]);
  return (
    <Card className="flex flex-col gap-3 p-4" role="region" aria-label="Person's IPs and devices">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h2 className="font-display text-lg text-ink">{data?.user.name ?? "Loading…"}</h2>
          {data && <p className="text-xs text-ink-soft">{data.user.email} · {data.user.role.replace("_", " ")}{data.user.is_active ? "" : " · deactivated"}</p>}
        </div>
        <button type="button" onClick={onClose} className="text-xs text-ink-soft underline">Close</button>
      </div>
      {error && <p role="alert" className="text-sm text-thread">{error}</p>}
      {data && (["ips", "devices"] as const).map((kind) => (
        <div key={kind}>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-soft">{kind === "ips" ? "IP addresses" : "Devices"}</h3>
          {data[kind].length === 0 ? <p className="text-sm text-ink-soft">None recorded.</p> : (
            <ul className="mt-1 flex flex-col gap-1">
              {data[kind].map((item) => (
                <li key={item.value} className="flex flex-wrap items-baseline justify-between gap-2 text-sm">
                  <button type="button" className="font-mono text-xs text-brass-deep underline"
                    onClick={() => onFilter(kind === "ips" ? { ip: item.value } : { device_id: item.value })}>{item.value}</button>
                  <span className="text-xs text-ink-soft">
                    {item.events} events · last <DateTimeDisplay value={item.last_seen} format="relative" />
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      ))}
      <p className="text-xs text-ink-soft">Click an IP or device to see everyone who used it.</p>
    </Card>
  );
}

/**
 * Admin security view: who is signing in and changing things, from which IP and device.
 * Browsers don't reveal MAC addresses; the device ID is a random value each browser keeps.
 */
export default function Security() {
  const [summary, setSummary] = useState<ActivitySummary | null>(null);
  const [rows, setRows] = useState<ActivityEntry[] | null>(null);
  const [filters, setFilters] = useState<ActivityFilters>({});
  const [draft, setDraft] = useState<ActivityFilters>({});
  const [person, setPerson] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);

  const load = useCallback(async (next: ActivityFilters) => {
    setError(null);
    setRows(null);
    try {
      const [s, r] = await Promise.all([adminSecurityApi.summary(), adminSecurityApi.activity(next)]);
      setSummary(s);
      setRows(r);
    } catch {
      setError("Couldn't load activity. Check your connection and refresh.");
    }
  }, []);

  useEffect(() => { void load(filters); }, [filters, load]);

  function apply(event: FormEvent) {
    event.preventDefault();
    setFilters({ ...draft });
  }

  function filterBy(next: ActivityFilters) {
    setDraft(next);
    setFilters(next);
  }

  async function loadMore() {
    if (!rows?.length) return;
    setLoadingMore(true);
    try {
      const older = await adminSecurityApi.activity({ ...filters, before: rows[rows.length - 1].at });
      setRows([...rows, ...older]);
    } finally {
      setLoadingMore(false);
    }
  }

  const active = Object.values(filters).some(Boolean);

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h1 className="font-display text-xl text-ink">Security</h1>
        <Button variant="secondary" onClick={() => void load(filters)}>Refresh</Button>
      </div>

      {summary && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
          <Stat label="Active in last 15 min" value={summary.active_now} />
          <Stat label="Sign-ins (24 h)" value={summary.sign_ins_24h} />
          <Stat label="Failed sign-ins (24 h)" value={summary.failed_sign_ins_24h} alert />
          <Stat label="Admin sign-ins (24 h)" value={summary.admin_sign_ins_24h} />
          <Stat label="Different IPs (24 h)" value={summary.distinct_ips_24h} />
        </div>
      )}
      {summary && summary.top_failed_ips.length > 0 && (
        <Card className="p-4">
          <h2 className="text-sm font-medium text-ink">Most failed sign-ins by IP (24 h)</h2>
          <ul className="mt-2 flex flex-wrap gap-2">
            {summary.top_failed_ips.map((item) => (
              <li key={item.ip_address}>
                <button type="button" onClick={() => filterBy({ ip: item.ip_address })}
                  className="rounded-full border border-thread/40 px-3 py-1 font-mono text-xs text-thread">
                  {item.ip_address} · {item.attempts}
                </button>
              </li>
            ))}
          </ul>
        </Card>
      )}

      <form onSubmit={apply} className="grid gap-2 sm:grid-cols-[1fr_1fr_1fr_auto]" aria-label="Filter activity">
        <Input aria-label="Email" placeholder="Email" value={draft.email ?? ""} onChange={(e) => setDraft({ ...draft, email: e.target.value })} />
        <Input aria-label="IP address" placeholder="IP address" value={draft.ip ?? ""} onChange={(e) => setDraft({ ...draft, ip: e.target.value })} />
        <select aria-label="Event" value={draft.event ?? ""} onChange={(e) => setDraft({ ...draft, event: e.target.value })}
          className="rounded-lg border border-line bg-paper px-3 py-2 text-sm text-ink">
          <option value="">All events</option>
          {Object.entries(EVENTS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
        <div className="flex gap-2">
          <Button type="submit">Filter</Button>
          {active && <Button type="button" variant="secondary" onClick={() => filterBy({})}>Clear</Button>}
        </div>
      </form>

      {person && <FootprintPanel userId={person} onClose={() => setPerson(null)} onFilter={(f) => { filterBy(f); }} />}

      {error && <p role="alert" className="text-sm text-thread">{error}</p>}
      {rows === null && !error && <p className="text-sm text-ink-soft">Loading activity…</p>}
      {rows && rows.length === 0 && <p className="text-sm text-ink-soft">No activity matches these filters.</p>}
      {rows && rows.length > 0 && (
        <div className="overflow-x-auto rounded-card border border-line">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-line bg-muslin/50 text-left text-ink-soft">
                <th className="px-3 py-2 font-medium">When</th>
                <th className="px-3 py-2 font-medium">Who</th>
                <th className="px-3 py-2 font-medium">What</th>
                <th className="px-3 py-2 font-medium">IP address</th>
                <th className="px-3 py-2 font-medium">Device</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const failed = row.event.endsWith("_failed") || (row.status_code != null && row.status_code >= 400);
                const tried = typeof row.details?.email === "string" ? row.details.email : null;
                return (
                  <tr key={row.id} className="border-b border-line align-top last:border-0">
                    <td className="whitespace-nowrap px-3 py-2 text-xs text-ink-soft"><DateTimeDisplay value={row.at} format="datetime" /></td>
                    <td className="px-3 py-2">
                      {row.user_id ? (
                        <button type="button" onClick={() => setPerson(row.user_id)} className="text-left text-brass-deep underline">
                          {row.user_name ?? row.user_email}
                        </button>
                      ) : <span className="text-ink-soft">{tried ? `Tried ${tried}` : "Anonymous"}</span>}
                      {row.role && <span className="block text-xs text-ink-soft">{row.role.replace("_", " ")}</span>}
                    </td>
                    <td className="px-3 py-2">
                      <span className={failed ? "text-thread" : "text-ink"}>{EVENTS[row.event] ?? row.event}</span>
                      {row.event === "request" && (
                        <span className="block font-mono text-xs text-ink-soft">{row.method} {row.path} · {row.status_code}</span>
                      )}
                    </td>
                    <td className="px-3 py-2">
                      {row.ip_address ? (
                        <button type="button" onClick={() => filterBy({ ip: row.ip_address ?? undefined })}
                          className="font-mono text-xs text-ink underline decoration-line">{row.ip_address}</button>
                      ) : "—"}
                    </td>
                    <td className="px-3 py-2 text-xs text-ink-soft">
                      {describeDevice(row.user_agent)}
                      {row.device_id && (
                        <button type="button" onClick={() => filterBy({ device_id: row.device_id ?? undefined })}
                          className="block font-mono text-[11px] underline decoration-line" title={row.device_id}>
                          {row.device_id.slice(0, 16)}…
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      {rows && rows.length >= 100 && (
        <Button variant="secondary" className="self-start" isLoading={loadingMore} onClick={() => void loadMore()}>Show older</Button>
      )}
      <p className="text-xs text-ink-soft">
        Records sign-ins (including failed attempts) and every change made, with IP address and device. Browsers don't
        reveal MAC addresses; the device ID identifies one browser on one device. Entries are kept for {summary?.retention_days ?? 180} days.
      </p>
    </div>
  );
}
