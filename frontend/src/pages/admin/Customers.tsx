import { useEffect, useState } from "react";
import { Table, type Column } from "@/components/ui/table";
import { Spinner } from "@/components/ui/spinner";
import { usersApi } from "@/api/users.api";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import type { User } from "@/types/user";

type AdminUser = User & { is_active: boolean; created_at: string | null };

export default function Customers() {
  const [customers, setCustomers] = useState<AdminUser[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setIsLoading(true);
    usersApi
      .adminList({ role: "customer" })
      .then((res) => {
        setCustomers(res.items as AdminUser[]);
        setTotal(res.total);
      })
      .catch((err) => setError(getDisplayErrorMessage(err, "Could not load customers.")))
      .finally(() => setIsLoading(false));
  }, []);

  const columns: Column<AdminUser>[] = [
    { header: "Name", render: (u) => u.full_name },
    { header: "Email", render: (u) => u.email },
    { header: "Email verified", render: (u) => u.is_email_verified ? "Yes" : "No" },
    { header: "Joined", render: (u) => u.created_at ? new Date(u.created_at).toLocaleDateString("en-NG") : "—" },
  ];

  return (
    <div>
      <div className="mb-6 flex items-center gap-3">
        <h1 className="font-display text-xl text-ink">Customers</h1>
        {!isLoading && <span className="text-sm text-ink-soft">({total})</span>}
      </div>
      {isLoading && <div className="flex justify-center py-16"><Spinner size="lg" /></div>}
      {error && <p role="alert" className="text-sm text-thread">{error}</p>}
      {!isLoading && !error && customers.length === 0 && (
        <p className="text-sm text-ink-soft">No customers registered yet.</p>
      )}
      {!isLoading && !error && customers.length > 0 && (
        <Table columns={columns} rows={customers} />
      )}
    </div>
  );
}
