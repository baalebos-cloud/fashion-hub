import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { productsApi } from "@/api/products.api";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { LoadingScreen } from "@/components/common/LoadingScreen";
import { vendorRoutes } from "@/config/routes.config";
import type { VendorProduct } from "@/types/product";

export default function EditProduct() {
  const { productId } = useParams<{ productId: string }>();
  const navigate = useNavigate();
  const [product, setProduct] = useState<VendorProduct | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (productId) productsApi.owned(productId).then(setProduct).catch((err) => setError(getDisplayErrorMessage(err)));
  }, [productId]);

  if (!product) return error ? <p role="alert">{error}</p> : <LoadingScreen label="Loading product…" />;

  async function handleSave() {
    if (!productId || !product) return;
    setIsSaving(true);
    setError(null);
    try {
      await productsApi.update(productId, { name: product.name, description: product.description ?? undefined, is_active: product.is_active });
      navigate(vendorRoutes.products);
    } catch (err) {
      setError(getDisplayErrorMessage(err));
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="flex max-w-sm flex-col gap-4">
      <h1 className="font-display text-xl text-ink">Edit product</h1>
      <label htmlFor="product-name">Product name</label>
      <Input id="product-name" value={product.name} onChange={(e) => setProduct({ ...product, name: e.target.value })} />
      <label htmlFor="product-description">Description</label>
      <Textarea id="product-description" value={product.description ?? ""} onChange={(e) => setProduct({ ...product, description: e.target.value })} rows={3} />
      <label><input type="checkbox" checked={product.is_active} onChange={(event) => setProduct({ ...product, is_active: event.target.checked })} /> Active listing</label>
      <p className="text-sm">Variant price: {product.base_price} {product.currency}. Price changes are not available in this form.</p>
      {error && <p className="text-sm text-thread">{error}</p>}
      <Button onClick={handleSave} isLoading={isSaving}>Save changes</Button>
    </div>
  );
}
