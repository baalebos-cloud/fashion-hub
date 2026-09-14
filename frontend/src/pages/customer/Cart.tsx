import { EmptyState } from "@/components/ui/empty-state";

/** Customers don't purchase vendor materials (that's the professional's
 * cart flow — see pages/professional/Cart.tsx); this route is reserved
 * for a possible future "save designs to cart before ordering" flow. */
export default function Cart() {
  return <EmptyState title="Nothing here yet" description="Customers order directly from a professional's profile." />;
}
