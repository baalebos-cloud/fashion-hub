import { Modal } from "@/components/ui/modal";
import { PaymentSummary } from "./PaymentSummary";
import { PaymentButton } from "./PaymentButton";

export interface PaymentModalProps {
  isOpen: boolean;
  onClose: () => void;
  orderId: string;
  orderNumber: string;
  amount: number;
  currency: string;
  callbackUrl: string;
}

export function PaymentModal({ isOpen, onClose, orderId, orderNumber, amount, currency, callbackUrl }: PaymentModalProps) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Complete payment">
      <div className="flex flex-col gap-4">
        <PaymentSummary orderNumber={orderNumber} amount={amount} currency={currency} />
        <PaymentButton orderId={orderId} callbackUrl={callbackUrl} />
      </div>
    </Modal>
  );
}
