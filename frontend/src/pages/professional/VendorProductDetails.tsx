import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { productsApi } from "@/api/products.api";
import { useCart } from "@/hooks/use-cart";
import { useToast } from "@/components/ui/toast";
import { ProductDetails } from "@/components/marketplace/ProductDetails";
import { LoadingScreen } from "@/components/common/LoadingScreen";
import type { VendorProduct } from "@/types/product";

export default function VendorProductDetails() {
  const { productId } = useParams<{ productId: string }>();
  const { addItem } = useCart();
  const { showToast } = useToast();
  const [product, setProduct] = useState<VendorProduct | null>(null);

  useEffect(() => {
    if (productId) productsApi.getById(productId).then(setProduct);
  }, [productId]);

  if (!product) return <LoadingScreen label="Loading product…" />;

  return (
    <ProductDetails
      product={product}
      variants={[]}
      inventory={null}
      onAddToCart={async (variantId, quantity) => {
        await addItem(variantId, quantity);
        showToast("Added to cart.", "success");
      }}
    />
  );
}
