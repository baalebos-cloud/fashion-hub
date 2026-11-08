import { useEffect, useState } from "react";
import { Link, useParams, useNavigate } from "react-router-dom";
import { productsApi } from "@/api/products.api";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Switch } from "@/components/ui/switch";
import { ErrorState } from "@/components/ui/error-state";
import { LoadingScreen } from "@/components/common/LoadingScreen";
import { formatCurrency } from "@/lib/formatters/currency";
import { vendorRoutes } from "@/config/routes.config";
import type { VendorProduct } from "@/types/product";

export default function EditProduct() {
  const { productId } = useParams<{ productId: string }>();
  const navigate = useNavigate();
  const [product, setProduct] = useState<VendorProduct | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true; setProduct(null); setError(null);
    if (productId) productsApi.owned(productId).then((value) => { if (active) setProduct(value); }).catch((err) => { if (active) setError(getDisplayErrorMessage(err)); });
    return () => { active = false; };
  }, [productId]);

  if (!product) return error ? <ErrorState title="Couldn't load this product" description={error} /> : <LoadingScreen label="Loading product…" />;

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
    <div className="mx-auto flex w-full max-w-xl flex-col gap-5">
      <Link to={vendorRoutes.products} className="text-sm font-semibold text-indigo">‹ Products</Link>
      <h1 className="font-display text-3xl text-ink">Edit product</h1>
      <section className="flex flex-col gap-4 rounded-card border border-line bg-surface p-5">
        <Field label="Product name" htmlFor="product-name">
          <Input id="product-name" value={product.name} onChange={(e) => setProduct({ ...product, name: e.target.value })} />
        </Field>
        <Field label="Description" htmlFor="product-description" optional>
          <Textarea id="product-description" value={product.description ?? ""} onChange={(e) => setProduct({ ...product, description: e.target.value })} rows={3} />
        </Field>
        <div className="flex items-start justify-between gap-4 rounded-control border border-line p-3">
          <span className="flex flex-col">
            <span className="text-sm font-semibold text-ink">Listed</span>
            <span className="text-[13px] text-ink-soft">Hidden products can't be ordered, but their order history is kept.</span>
          </span>
          <Switch checked={product.is_active} onChange={(checked) => setProduct({ ...product, is_active: checked })} label="Listed" />
        </div>
        <p className="text-sm text-ink-soft">
          Price <span className="font-mono text-ink">{formatCurrency(product.base_price, product.currency)}</span>. Changing the price isn't available in this form yet.
          Change stock on the Inventory page.
        </p>
      </section>
      {error && <p role="alert" className="text-sm text-thread">{error}</p>}
      <Button className="self-start" onClick={() => { void handleSave(); }} isLoading={isSaving}>Save changes</Button>
    </div>
  );
}
