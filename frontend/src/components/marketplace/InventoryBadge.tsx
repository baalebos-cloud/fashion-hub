import { Badge } from "@/components/ui/badge";

export function InventoryBadge({ quantityAvailable }: { quantityAvailable: number }) {
  if (quantityAvailable <= 0) return <Badge tone="danger">Out of stock</Badge>;
  if (quantityAvailable <= 5) return <Badge tone="warning">Only {quantityAvailable} left</Badge>;
  return <Badge tone="success">In stock</Badge>;
}
