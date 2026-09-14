import { Badge } from "@/components/ui/badge";

export function DeliveryStatus({ status }: { status: string }) {
  return <Badge tone="info">{status.replace(/_/g, " ")}</Badge>;
}
