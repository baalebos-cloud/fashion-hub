import { useEffect, useState } from "react";
import { Table, type Column } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import { usersApi } from "@/api/users.api";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import type { User } from "@/types/user";

type AdminUser = User & { is_active: boolean; created_at: string | null };

const ROLE_FILTERS = [
  { label: "All professionals", value: "" },
  { label: "Tailors", value: "tailor" },
  { label: "Designers", value: "designer" },
];

export default function Professionals() {
  const [professionals, setProfessionals] = useState<AdminUser[]>([]);
  const [total, setTotal] = useState(0);
  const [role, setRole] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setIsLoading(true);
    setError(null);
    // When no specific role is selected, fetch tailors and designers separately and merge
    const fetches = role
      ? [usersApi.adminList({ role })]
      : [usersApi.adminList({ role: "tailor" }), usersApi.adminList({ role: "designer" })];

    Promise.all(fetches)
      .then((results) => {
        if (!active) return;
        const items = results.flatMap((r) => r.items) as AdminUser[];
        items.sort((a, b) => (b.created_at ?? "").localeCompare(a.created_at ?? ""));
        setProfessionals(items);
        setTotal(results.reduce((sum, r) => sum + r.total, 0));
      })
      .catch((err) => { if (active) setError(getDisplayErrorMessage(err, "Could not load professionals.")); })
      .finally(() => { if (active) setIsLoading(false); });
    return () => { active = false; };
  }, [role]);

  const columns: Column<AdminUser>[] = [
    { header: "Name", render: (u) => u.full_name },
    { header: "Email", render: (u) => u.email },
    { header: "Type", render: (u) => <Badge>{u.role}</Badge> },
    { header: "Email verified", render: (u) => u.is_email_verified ? "Yes" : "No" },
    { header: "Joined", render: (u) => u.created_at ? new Date(u.created_at).toLocaleDateString("en-NG") : "—" },
  ];

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <h1 className="font-display text-xl text-ink">Professionals</h1>
          {!isLoading && <span className="text-sm text-ink-soft">({total})</span>}
        </div>
        <div className="flex gap-1.5">
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
      {isLoading && <div className="flex justify-center py-16"><Spinner size="lg" /></div>}
      {error && <p role="alert" className="text-sm text-thread">{error}</p>}
      {!isLoading && !error && professionals.length === 0 && (
        <p className="text-sm text-ink-soft">No professionals registered yet.</p>
      )}
      {!isLoading && !error && professionals.length > 0 && (
        <Table columns={columns} rows={professionals} />
      )}
    </div>
  );
}
