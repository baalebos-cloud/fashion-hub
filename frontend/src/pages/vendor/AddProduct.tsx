import { useState } from "react";
import { uploadFile } from "@/lib/storage/file-storage";
import { useNavigate } from "react-router-dom";
import { productsApi } from "@/api/products.api";
import { validateProduct } from "@/lib/validation/product";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { vendorRoutes } from "@/config/routes.config";

export default function AddProduct() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [stock, setStock] = useState(0);
  const [basePrice, setBasePrice] = useState("");
  const [images, setImages] = useState<string[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit() {
    const validationErrors = validateProduct({ name, basePrice: Number(basePrice) });
    if (images.length === 0) {
      setFormError("Upload at least one material photo.");
      return;
    }
    if (validationErrors.length > 0) {
      setErrors(Object.fromEntries(validationErrors.map((e) => [e.field, e.message])));
      return;
    }
    setErrors({});
    setFormError(null);
    setIsSubmitting(true);
    try {
      await productsApi.create({ name, description, base_price: Number(basePrice), initial_stock: stock, image_urls: images });
      navigate(vendorRoutes.products);
    } catch (err) {
      setFormError(getDisplayErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="flex max-w-sm flex-col gap-4">
      <h1 className="font-display text-xl text-ink">Add product</h1>
      <div>
        <label htmlFor="new-product-name">Product name</label>
        <Input id="new-product-name" placeholder="Product name" value={name} onChange={(e) => setName(e.target.value)} error={errors.name} />
        {errors.name && <p className="mt-1 text-xs text-thread">{errors.name}</p>}
      </div>
      <label htmlFor="new-product-description">Description</label>
      <Textarea id="new-product-description" placeholder="Description" value={description} onChange={(e) => setDescription(e.target.value)} rows={3} />
      <div className="flex flex-col gap-2">
        <label htmlFor="material-images">Material photos (1–5)</label>
        <input id="material-images" type="file" accept="image/jpeg,image/png,image/webp"
          multiple disabled={uploading || images.length >= 5}
          onChange={async (event) => {
            const chosen = Array.from(event.target.files ?? []).slice(0, 5 - images.length);
            setUploadError(null);
            setUploading(true);
            try {
              const urls: string[] = [];
              for (const file of chosen) {
                const result = await uploadFile("/media/upload?purpose=product", file);
                urls.push(result.url);
              }
              setImages(prev => [...prev, ...urls]);
            } catch (failure) {
              setUploadError(getDisplayErrorMessage(failure, "Unable to upload material image."));
            } finally {
              setUploading(false);
              event.target.value = "";
            }
          }} />
        {uploading && <p role="status">Uploading material photos…</p>}
        {uploadError && <p role="alert" className="text-thread">{uploadError}</p>}
        <div className="grid grid-cols-3 gap-2">
          {images.map((src, index) => (
            <div key={src} className="relative">
              <img src={src} alt={`Material photo ${index + 1}`} className="aspect-square w-full rounded object-cover" />
              <button type="button" aria-label={`Remove photo ${index + 1}`}
                className="absolute right-1 top-1 rounded bg-paper px-2 py-1"
                onClick={() => setImages(prev => prev.filter((_, i) => i !== index))}>×</button>
            </div>
          ))}
        </div>
      </div>
      <div>
        <label htmlFor="new-product-price">Price (NGN)</label>
        <Input id="new-product-price" type="number" min="0.01" step="0.01" placeholder="Price" value={basePrice} onChange={(e) => setBasePrice(e.target.value)} error={errors.basePrice} />
        {errors.basePrice && <p className="mt-1 text-xs text-thread">{errors.basePrice}</p>}
      </div>
      <label htmlFor="new-product-stock">Initial stock</label>
      <Input id="new-product-stock" type="number" min={0} max={1000000000} step={1} value={stock} onChange={(event) => setStock(Number(event.target.value))} />
      {formError && <p className="text-sm text-thread">{formError}</p>}
      <Button onClick={handleSubmit} isLoading={isSubmitting} disabled={uploading || images.length === 0 || !Number.isSafeInteger(stock) || stock < 0 || stock > 1000000000}>Add product</Button>
    </div>
  );
}
