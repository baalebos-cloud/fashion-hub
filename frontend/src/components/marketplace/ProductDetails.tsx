import { useState } from "react";
import { ProductGallery } from "./ProductGallery";
import { ProductVariantSelector } from "./ProductVariantSelector";
import { ProductQuantitySelector } from "./ProductQuantitySelector";
import { InventoryBadge } from "./InventoryBadge";
import { Button } from "@/components/ui/button";
import { formatCurrency } from "@/lib/formatters/currency";
import type { VendorProduct, ProductVariant, Inventory } from "@/types/product";

export interface ProductDetailsProps {
  product: VendorProduct;
  variants: ProductVariant[];
  inventory: Inventory | null;
  onAddToCart: (variantId: string, quantity: number) => Promise<void>;
}

export function ProductDetails({ product, variants, inventory, onAddToCart }: ProductDetailsProps) {
  const [selectedVariantId, setSelectedVariantId] = useState<string | null>(variants[0]?.id ?? null);
  const [quantity, setQuantity] = useState(1);
  const [isAdding, setIsAdding] = useState(false);

  const available = inventory?.quantity_available ?? 0;

  async function handleAddToCart() {
    if (!selectedVariantId) return;
    setIsAdding(true);
    try {
      await onAddToCart(selectedVariantId, quantity);
    } finally {
      setIsAdding(false);
    }
  }

  return (
    <div className="grid gap-8 md:grid-cols-2">
      <ProductGallery images={product.primary_image_url ? [product.primary_image_url] : []} alt={product.name} />
      <div className="flex flex-col gap-4">
        <h1 className="font-display text-xl text-ink">{product.name}</h1>
        <div className="text-lg font-medium text-ink">{formatCurrency(product.base_price, product.currency)}</div>
        {product.description && <p className="text-sm text-ink-soft">{product.description}</p>}
        <InventoryBadge quantityAvailable={available} />
        <ProductVariantSelector variants={variants} selectedId={selectedVariantId} onSelect={setSelectedVariantId} />
        <ProductQuantitySelector quantity={quantity} max={Math.max(1, available)} onChange={setQuantity} />
        <Button onClick={handleAddToCart} isLoading={isAdding} disabled={available === 0} className="self-start">
          Add to cart
        </Button>
      </div>
    </div>
  );
}
