import { useCart } from "@/hooks/use-cart";
import { CartList } from "@/components/cart/CartList";
import { CartSummary } from "@/components/cart/CartSummary";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";
import { professionalRoutes } from "@/config/routes.config";

export default function Cart() {
  const { summary } = useCart();
  const items = summary?.items ?? [];

  return (
    <div className="mx-auto flex max-w-lg flex-col gap-6">
      <h1 className="font-display text-xl text-ink">Your cart</h1>
      <CartList items={items} />
      {items.length > 0 && (
        <>
          <CartSummary subtotal={summary?.subtotal ?? 0} />
          <Link to={professionalRoutes.checkout}><Button className="w-full">Checkout</Button></Link>
        </>
      )}
    </div>
  );
}
