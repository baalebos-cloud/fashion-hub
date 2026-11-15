import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import { productsApi } from "@/api/products.api";
import { ProductDetails as ProductDetailsComponent } from "@/components/marketplace/ProductDetails";
import { LoadingScreen } from "@/components/common/LoadingScreen";
import { authRoutes } from "@/config/routes.config";
import { useNavigate } from "react-router-dom";
import type { VendorProduct } from "@/types/product";
import { trackView, viewSource } from "@/lib/tracking/interactions";
import { RelatedProducts } from "@/components/recommendations/RelatedProducts";
import { recommendationsApi } from "@/api/recommendations.api";
import { publicRoutes } from "@/config/routes.config";
import { useAuthStore } from "@/store/auth.store";
import { useCartStore } from "@/store/cart.store";
import { useToast } from "@/components/ui/toast";
import { materialRoutesFor } from "@/lib/routes/material-routes";

export default function ProductDetails() {
  const { productId } = useParams<{ productId: string }>();
  const [search] = useSearchParams();
  const from = search.get("from");
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const addItem = useCartStore((state) => state.addItem);
  const { showToast } = useToast();
  const buyerRoutes = materialRoutesFor(user?.role);
  const [product, setProduct] = useState<VendorProduct | null>(null);

  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let active = true; setProduct(null); setError(null);
    if (productId) productsApi.getById(productId).then((value) => { if (active) setProduct(value); }).catch((err) => { if (active) setError(getDisplayErrorMessage(err)); });
    return () => { active = false; };
  }, [productId]);
  // Only `product` should re-record a view; `from` is read once with it.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { if (product) trackView("product", product.id, viewSource(from, "product_page")); }, [product]);
  if (error) return <p role="alert">{error}</p>;

  if (!product) return <LoadingScreen label="Loading product…" />;

  return (
    <div className="mx-auto max-w-4xl px-4 py-10">
      <ProductDetailsComponent
        key={product.id}
        product={product}
        variants={product.variants ?? []}
        inventory={null}
        onAddToCart={async (variantId, quantity) => {
          if (!user) {
            // Sign in first, then come straight back to this product in the buyer's own app area.
            navigate(authRoutes.login, { state: { from: { pathname: `/app/materials/products/${product.id}` } } });
            return;
          }
          if (!buyerRoutes) throw new Error("Materials are bought by customers, tailors and designers. Sign in with one of those accounts to order.");
          await addItem(variantId, quantity);
          showToast("Added to cart.", "success");
          navigate(buyerRoutes.cart);
        }}
      />
      <div className="mt-10">
        <RelatedProducts title="You might also like" loadKey={product.id} source="similar_items"
          load={() => recommendationsApi.similarProducts(product.id)} detailsPathFor={publicRoutes.productDetails} />
      </div>
    </div>
  );
}
