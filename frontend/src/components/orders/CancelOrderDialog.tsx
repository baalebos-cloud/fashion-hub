import { useState } from "react";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { Textarea } from "@/components/ui/textarea";

export interface CancelOrderDialogProps {
  isOpen: boolean;
  onConfirm: (reason: string) => Promise<void>;
  onCancel: () => void;
}

export function CancelOrderDialog({ isOpen, onConfirm, onCancel }: CancelOrderDialogProps) {
  const [reason, setReason] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleConfirm() {
    setIsSubmitting(true);
    try {
      await onConfirm(reason);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <ConfirmDialog
      isOpen={isOpen}
      title="Cancel this order?"
      isDangerous
      isLoading={isSubmitting}
      onConfirm={handleConfirm}
      onCancel={onCancel}
      confirmLabel="Cancel order"
      description="This can't be undone once the order has moved into production."
    >
      <Textarea
        placeholder="Optional: let them know why (visible in the order timeline)"
        value={reason}
        onChange={(e) => setReason(e.target.value)}
      />
    </ConfirmDialog>
  );
}
