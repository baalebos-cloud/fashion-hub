import { useState } from "react";
import { useAuth } from "@/hooks/use-auth";
import { canMarkOrderReceived } from "@/lib/auth/permissions";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import type { Order } from "@/types/order";

export interface MarkReceivedButtonProps {
  order: Order;
  onConfirm: () => Promise<void>;
}

/**
 * Renders only for the customer who placed the order, and only once it's
 * `delivered` (see lib/auth/permissions.ts::canMarkOrderReceived). This is
 * a UX affordance, not the enforcement point — POST /orders/{id}/received
 * independently re-checks both the role and that the caller is this
 * specific order's buyer (see backend/docs/orders.md#mark-as-received-rule).
 * Hiding this button from a tailor doesn't grant them anything by being
 * shown it; it's simply never rendered for them.
 */
export function MarkReceivedButton({ order, onConfirm }: MarkReceivedButtonProps) {
  const { user } = useAuth();
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isConfirming, setIsConfirming] = useState(false);

  if (!canMarkOrderReceived(user, order)) return null;

  async function handleConfirm() {
    setIsConfirming(true);
    try {
      await onConfirm();
      setIsDialogOpen(false);
    } finally {
      setIsConfirming(false);
    }
  }

  return (
    <>
      <Button onClick={() => setIsDialogOpen(true)}>Mark as Received</Button>
      <ConfirmDialog
        isOpen={isDialogOpen}
        title="Mark this order as received?"
        description="Only do this once your order has actually arrived. You'll be able to leave a review right after."
        confirmLabel="Yes, I've received it"
        isLoading={isConfirming}
        onConfirm={handleConfirm}
        onCancel={() => setIsDialogOpen(false)}
      />
    </>
  );
}
