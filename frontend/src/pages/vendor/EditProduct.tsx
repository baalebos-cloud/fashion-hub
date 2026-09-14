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
    if (productId) productsApi.getById(productId).then(setProduct);
  }, [productId]);

  if (!product) return <LoadingScreen label="Loading product…" />;

  async function handleSave() {
    if (!productId || !product) return;
    setIsSaving(true);
    setError(null);
    try {
      await productsApi.update(productId, { name: product.name, description: product.description ?? undefined, base_price: product.base_price });
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
      <Input value={product.name} onChange={(e) => setProduct({ ...product, name: e.target.value })} />
      <Textarea value={product.description ?? ""} onChange={(e) => setProduct({ ...product, description: e.target.value })} rows={3} />
      <Input type="number" value={product.base_price} onChange={(e) => setProduct({ ...product, base_price: Number(e.target.value) })} />
      {error && <p className="text-sm text-thread">{error}</p>}
      <Button onClick={handleSave} isLoading={isSaving}>Save changes</Button>
    </div>
  );
}
