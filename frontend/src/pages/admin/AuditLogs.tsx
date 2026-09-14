import { useState } from "react";
import { Table, type Column } from "@/components/ui/table";
import { DateTimeDisplay } from "@/components/common/DateTimeDisplay";
import { EmptyState } from "@/components/ui/empty-state";

interface AuditLogRow {
  id: string;
  action: string;
  resource_type: string | null;
  created_at: string;
}

/** Read-only view of backend/app/models/audit_log.py rows. Requires a
 * `GET /admin/audit-logs` endpoint, which isn't wired up yet in
 * backend/app/api/v1/admin.py (currently a documented stub). */
export default function AuditLogs() {
  const [logs] = useState<AuditLogRow[]>([]);

  if (logs.length === 0) return <EmptyState title="No audit log entries to show" />;

  const columns: Column<AuditLogRow>[] = [
    { header: "Action", render: (log) => log.action },
    { header: "Resource", render: (log) => log.resource_type ?? "—" },
    { header: "When", render: (log) => <DateTimeDisplay value={log.created_at} format="datetime" /> },
  ];

  return (
    <div>
      <h1 className="mb-6 font-display text-xl text-ink">Audit logs</h1>
      <Table columns={columns} rows={logs} />
    </div>
  );
}
