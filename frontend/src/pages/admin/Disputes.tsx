import { EmptyState } from "@/components/ui/empty-state";

/** No Dispute model exists yet in the backend scaffold (see
 * backend/docs/database.md's entity list) — orders/payments carry no
 * dispute status today. Add a Dispute table + admin endpoints before
 * wiring this page up for real. */
export default function Disputes() {
  return <EmptyState title="No open disputes" description="Order and payment disputes will appear here once reported." />;
}
