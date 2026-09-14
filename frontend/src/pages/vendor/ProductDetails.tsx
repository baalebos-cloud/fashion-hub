import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { productsApi } from "@/api/products.api";
import { InventoryBadge } from "@/components/marketplace/InventoryBadge";
import { LoadingScreen } from "@/components/common/LoadingScreen";
import { formatCurrency } from "@/lib/formatters/currency";
import type { VendorProduct } from "@/types/product";

export default function ProductDetails() {
  const { productId } = useParams<{ productId: string }>();
  const [product, setProduct] = useState<VendorProduct | null>(null);

  useEffect(() => {
    if (productId) productsApi.getById(productId).then(setProduct);
  }, [productId]);

  if (!product) return <LoadingScreen label="Loading product…" />;

  return (
    <div className="max-w-md">
      <h1 className="font-display text-xl text-ink">{product.name}</h1>
      <p className="mt-1 text-sm text-ink-soft">{product.description}</p>
      <div className="mt-3 text-lg font-medium text-ink">{formatCurrency(product.base_price, product.currency)}</div>
      <div className="mt-2"><InventoryBadge quantityAvailable={0} /></div>
    </div>
  );
}
