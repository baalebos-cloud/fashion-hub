import { useState } from "react";
import { Table, type Column } from "@/components/ui/table";
import { EmptyState } from "@/components/ui/empty-state";
import type { User } from "@/types/user";

/** Requires `GET /admin/users?role=customer`. See Users.tsx. */
export default function Customers() {
  const [customers] = useState<User[]>([]);
  if (customers.length === 0) return <EmptyState title="No customers to show" />;

  const columns: Column<User>[] = [
    { header: "Name", render: (u) => u.full_name },
    { header: "Email", render: (u) => u.email },
  ];

  return (
    <div>
      <h1 className="mb-6 font-display text-xl text-ink">Customers</h1>
      <Table columns={columns} rows={customers} />
    </div>
  );
}
