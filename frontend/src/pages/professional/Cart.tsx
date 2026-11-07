import { useCart } from "@/hooks/use-cart";
import { CartList } from "@/components/cart/CartList";
import { CartSummary } from "@/components/cart/CartSummary";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";
import { professionalRoutes } from "@/config/routes.config";
import { RelatedProducts } from "@/components/recommendations/RelatedProducts";
import { recommendationsApi } from "@/api/recommendations.api";

export default function Cart() {
  const { summary, isLoading, error } = useCart();
  const items = summary?.items ?? [];
  const productIds = [...new Set(items.map((item) => item.product_id).filter(Boolean))].sort();

  return (
    <div className="mx-auto flex max-w-lg flex-col gap-6">
      <h1 className="font-display text-xl text-ink">Your cart</h1>
      {error && <p role="alert">{error}</p>}
      {isLoading ? <p role="status">Loading cart…</p> : <CartList items={items} />}
      {items.length > 0 && (
        <>
          <CartSummary subtotal={summary?.subtotal ?? 0} />
          <Link to={professionalRoutes.checkout}><Button className="w-full">Checkout</Button></Link>
          <RelatedProducts title="Often bought together" loadKey={productIds.join(",")} source="bought_together"
            load={() => recommendationsApi.boughtTogether(productIds)} detailsPathFor={professionalRoutes.vendorProductDetails} />
        </>
      )}
    </div>
  );
}
