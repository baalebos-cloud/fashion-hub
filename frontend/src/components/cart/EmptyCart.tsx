import { Link } from "react-router-dom";
import { EmptyState } from "@/components/ui/empty-state";
import { Button } from "@/components/ui/button";

export function EmptyCart({ marketplacePath = "/app/professional/vendor-marketplace" }: { marketplacePath?: string }) {
  return (
    <EmptyState
      title="Your cart is empty"
      description="Browse fabrics, buttons, zippers, and more from verified vendors."
      action={
        <Link to={marketplacePath}>
          <Button variant="secondary">Browse the marketplace</Button>
        </Link>
      }
    />
  );
}
