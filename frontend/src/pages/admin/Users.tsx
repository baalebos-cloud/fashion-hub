import { useEffect, useState } from "react";
import { Table, type Column } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import { ROLE_LABELS } from "@/constants/roles";
import { usersApi } from "@/api/users.api";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import type { User } from "@/types/user";

type AdminUser = User & { is_active: boolean; created_at: string | null };

const ROLE_FILTERS = [
  { label: "All", value: "" },
  { label: "Customers", value: "customer" },
  { label: "Tailors", value: "tailor" },
  { label: "Designers", value: "designer" },
  { label: "Vendors", value: "vendor" },
  { label: "Delivery", value: "delivery_partner" },
];

export default function Users() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [total, setTotal] = useState(0);
  const [role, setRole] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setIsLoading(true);
    setError(null);
    usersApi
      .adminList({ role: role || undefined })
      .then((res) => {
        if (!active) return;
        setUsers(res.items as AdminUser[]);
        setTotal(res.total);
      })
      .catch((err) => {
        if (active) setError(getDisplayErrorMessage(err, "Could not load users."));
      })
      .finally(() => { if (active) setIsLoading(false); });
    return () => { active = false; };
  }, [role]);

  const columns: Column<AdminUser>[] = [
    { header: "Name", render: (u) => u.full_name },
    { header: "Email", render: (u) => u.email },
    { header: "Role", render: (u) => <Badge>{ROLE_LABELS[u.role]}</Badge> },
    { header: "Email verified", render: (u) => u.is_email_verified ? "Yes" : "No" },
    { header: "Joined", render: (u) => u.created_at ? new Date(u.created_at).toLocaleDateString("en-NG") : "—" },
  ];

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-display text-xl text-ink">
          Registered users {!isLoading && <span className="ml-2 text-sm font-normal text-ink-soft">({total})</span>}
        </h1>
        <div className="flex flex-wrap gap-1.5">
          {ROLE_FILTERS.map((f) => (
            <button
              key={f.value}
              onClick={() => setRole(f.value)}
              className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${
                role === f.value
                  ? "border-ink bg-ink text-paper"
                  : "border-line text-ink-soft hover:border-ink hover:text-ink"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {isLoading && (
        <div className="flex justify-center py-16">
          <Spinner size="lg" />
        </div>
      )}
      {error && <p role="alert" className="text-sm text-thread">{error}</p>}
      {!isLoading && !error && users.length === 0 && (
        <p className="text-sm text-ink-soft">No users found{role ? ` with role "${role}"` : ""}.</p>
      )}
      {!isLoading && !error && users.length > 0 && (
        <Table columns={columns} rows={users} />
      )}
    </div>
  );
}
