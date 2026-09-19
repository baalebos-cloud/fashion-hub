import { Table, type Column } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { DateTimeDisplay } from "@/components/common/DateTimeDisplay";
import { EmptyState } from "@/components/ui/empty-state";
import { formatCurrency } from "@/lib/formatters/currency";
import type { Referral, ReferralStatus } from "@/types/referral";

const STATUS_TONE: Record<ReferralStatus, "neutral" | "info" | "success"> = {
  pending: "neutral",
  qualified: "info",
  paid: "success",
};

const STATUS_LABEL: Record<ReferralStatus, string> = {
  pending: "Awaiting first order",
  qualified: "Commission earned",
  paid: "Paid out",
};

export function ReferralList({ referrals }: { referrals: Referral[] }) {
  if (referrals.length === 0) {
    return <EmptyState title="No referrals yet" description="Share your referral link to start earning commission." />;
  }

  const columns: Column<Referral>[] = [
    { header: "Status", render: (r) => <Badge tone={STATUS_TONE[r.status]}>{STATUS_LABEL[r.status]}</Badge> },
    {
      header: "Commission",
      render: (r) => (r.commission_amount != null ? formatCurrency(r.commission_amount, r.commission_currency ?? "NGN") : "—"),
    },
    {
      header: "Qualified",
      render: (r) => (r.qualified_at ? <DateTimeDisplay value={r.qualified_at} format="date" /> : "—"),
    },
  ];

  return <Table columns={columns} rows={referrals} />;
}
