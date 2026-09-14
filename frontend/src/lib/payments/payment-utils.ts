import type { PaymentStatus } from "@/types/payment";

/** Display-only helpers — never used to decide business logic (e.g.
 * whether to show a "Track order" button), which always keys off
 * order.status as returned by the backend after its own verification. */
export function paymentStatusLabel(status: PaymentStatus): string {
  const labels: Record<PaymentStatus, string> = {
    initialized: "Awaiting payment",
    pending: "Processing",
    successful: "Paid",
    failed: "Payment failed",
    reversed: "Refunded",
  };
  return labels[status];
}

export function isPaymentTerminal(status: PaymentStatus): boolean {
  return status === "successful" || status === "failed" || status === "reversed";
}
