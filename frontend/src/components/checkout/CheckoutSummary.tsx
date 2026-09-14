import { CartSummary } from "@/components/cart/CartSummary";
import { useCart } from "@/hooks/use-cart";

export function CheckoutSummary({ deliveryFee }: { deliveryFee?: number }) {
  const { summary } = useCart();
  return <CartSummary subtotal={summary?.subtotal ?? 0} deliveryFee={deliveryFee} />;
}
