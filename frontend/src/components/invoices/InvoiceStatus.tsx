import { Badge } from "@/components/ui/badge";

export function InvoiceStatus({ status }: { status: string }) {
  const tone = status === "successful" ? "success" : status === "failed" ? "danger" : "neutral";
  return <Badge tone={tone}>{status}</Badge>;
}
