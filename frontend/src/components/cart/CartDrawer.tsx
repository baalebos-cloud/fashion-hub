import { Drawer } from "@/components/ui/drawer";
import { CartList } from "./CartList";
import { CartSummary } from "./CartSummary";
import { Button } from "@/components/ui/button";
import { useCart } from "@/hooks/use-cart";
import { Link } from "react-router-dom";

export function CartDrawer({ isOpen, onClose, checkoutPath }: { isOpen: boolean; onClose: () => void; checkoutPath: string }) {
  const { summary } = useCart();
  const items = summary?.items ?? [];

  return (
    <Drawer isOpen={isOpen} onClose={onClose} title="Your cart">
      <div className="flex h-full flex-col gap-4">
        <div className="flex-1 overflow-y-auto">
          <CartList items={items} />
        </div>
        {items.length > 0 && (
          <>
            <CartSummary subtotal={summary?.subtotal ?? 0} />
            <Link to={checkoutPath} onClick={onClose}>
              <Button className="w-full">Checkout</Button>
            </Link>
          </>
        )}
      </div>
    </Drawer>
  );
}
