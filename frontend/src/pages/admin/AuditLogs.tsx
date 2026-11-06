import { useEffect, useState } from "react";
import { Table, type Column } from "@/components/ui/table";
import { DateTimeDisplay } from "@/components/common/DateTimeDisplay";
import { EmptyState } from "@/components/ui/empty-state";
import { adminSecurityApi, type AuditEntry } from "@/api/admin-security.api";

/** Admin and system actions: approvals, rejections, dispatch changes. Newest first. */
export default function AuditLogs() {
  const [logs, setLogs] = useState<AuditEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    adminSecurityApi.auditLogs().then(setLogs).catch(() => setError("Couldn't load the audit log."));
  }, []);

  if (error) return <p role="alert" className="text-sm text-thread">{error}</p>;
  if (logs === null) return <p className="text-sm text-ink-soft">Loading…</p>;
  if (logs.length === 0) return <EmptyState title="No audit log entries to show" />;

  const columns: Column<AuditEntry>[] = [
    { header: "Action", render: (log) => log.action.replace(".", " · ") },
    { header: "Resource", render: (log) => log.resource_type ?? "—" },
    { header: "By", render: (log) => log.actor_email ?? "System" },
    { header: "IP address", render: (log) => <span className="font-mono text-xs">{log.ip_address ?? "—"}</span> },
    { header: "When", render: (log) => <DateTimeDisplay value={log.created_at} format="datetime" /> },
  ];

  return (
    <div>
      <h1 className="mb-6 font-display text-xl text-ink">Audit logs</h1>
      <Table columns={columns} rows={logs} />
    </div>
  );
}
