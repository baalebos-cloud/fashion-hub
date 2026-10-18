import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { productsApi } from "@/api/products.api";
import { useCartStore } from "@/store/cart.store";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import { useToast } from "@/components/ui/toast";
import { ProductDetails } from "@/components/marketplace/ProductDetails";
import { LoadingScreen } from "@/components/common/LoadingScreen";
import type { VendorProduct } from "@/types/product";

export default function VendorProductDetails() {
  const { productId } = useParams<{ productId: string }>();
  const addItem = useCartStore((state) => state.addItem);
  const { showToast } = useToast();
  const [product, setProduct] = useState<VendorProduct | null>(null);

  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let active = true; setProduct(null); setError(null);
    if (productId) productsApi.getById(productId).then((value) => { if (active) setProduct(value); }).catch((err) => { if (active) setError(getDisplayErrorMessage(err)); });
    return () => { active = false; };
  }, [productId]);
  if (error) return <p role="alert">{error}</p>;

  if (!product) return <LoadingScreen label="Loading product…" />;

  return (
    <ProductDetails
      key={product.id}
      product={product}
      variants={product.variants ?? []}
      inventory={null}
      onAddToCart={async (variantId, quantity) => {
        await addItem(variantId, quantity);
        showToast("Added to cart.", "success");
      }}
    />
  );
}
