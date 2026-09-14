import { useState } from "react";
import { Table, type Column } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { ROLE_LABELS } from "@/constants/roles";
import type { User } from "@/types/user";

/** Requires `GET /admin/users` (backend/app/api/v1/admin.py is currently
 * a documented stub — see backend/docs/api-reference.md). This page
 * renders the moment that endpoint exists; only the data-fetching effect
 * needs adding. */
export default function Users() {
  const [users] = useState<User[]>([]);

  if (users.length === 0) return <EmptyState title="No users to show" />;

  const columns: Column<User>[] = [
    { header: "Name", render: (u) => u.full_name },
    { header: "Email", render: (u) => u.email },
    { header: "Role", render: (u) => <Badge>{ROLE_LABELS[u.role]}</Badge> },
    { header: "Verified", render: (u) => (u.is_email_verified ? "Yes" : "No") },
  ];

  return (
    <div>
      <h1 className="mb-6 font-display text-xl text-ink">Users</h1>
      <Table columns={columns} rows={users} />
    </div>
  );
}
