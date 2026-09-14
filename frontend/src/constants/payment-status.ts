import type { PaymentStatus } from "@/types/payment";

export const PAYMENT_STATUS_LABELS: Record<PaymentStatus, string> = {
  initialized: "Awaiting Payment",
  pending: "Processing",
  successful: "Paid",
  failed: "Failed",
  reversed: "Refunded",
};
