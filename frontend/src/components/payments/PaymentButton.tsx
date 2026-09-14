import { usePayment } from "@/hooks/use-payment";
import { Button } from "@/components/ui/button";

export function PaymentButton({ orderId, callbackUrl, disabled }: { orderId: string; callbackUrl: string; disabled?: boolean }) {
  const { payAndRedirect, isInitializing, error } = usePayment();

  return (
    <div>
      <Button onClick={() => payAndRedirect(orderId, callbackUrl)} isLoading={isInitializing} disabled={disabled} className="w-full">
        Pay now
      </Button>
      {error && <p className="mt-2 text-sm text-thread">{error}</p>}
    </div>
  );
}
