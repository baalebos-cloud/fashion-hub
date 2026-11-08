import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { uploadFile } from "@/lib/storage/file-storage";
import { productsApi } from "@/api/products.api";
import { validateProduct } from "@/lib/validation/product";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { formatCurrency } from "@/lib/formatters/currency";
import { vendorRoutes } from "@/config/routes.config";

type Unit = "yard" | "meter" | "roll" | "piece";
const UNIT_LABEL: Record<Unit, string> = { yard: "yard", meter: "metre", roll: "roll", piece: "piece" };
const MAX_STOCK = 1000000000;

/** Add a product in three parts (details, price and stock, photos), with what's missing listed up top
 * and a preview of how tailors will see it. Same request as before. */
export default function AddProduct() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [stock, setStock] = useState(0);
  const [unit, setUnit] = useState<Unit>("yard");
  const [basePrice, setBasePrice] = useState("");
  const [images, setImages] = useState<string[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const stockValid = Number.isSafeInteger(stock) && stock >= 0 && stock <= MAX_STOCK;
  const missing = [
    !name.trim() && "add a product name",
    !(Number(basePrice) > 0) && "set a price",
    images.length === 0 && "add at least one photo",
    !stockValid && "enter a whole number for stock",
  ].filter(Boolean) as string[];

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
      await productsApi.create({ name, description, base_price: Number(basePrice), initial_stock: stock, image_urls: images, unit_of_measure: unit });
      navigate(vendorRoutes.products);
    } catch (err) {
      // The form keeps everything typed, so the vendor can retry.
      setFormError(getDisplayErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  }

  async function addPhotos(event: React.ChangeEvent<HTMLInputElement>) {
    const chosen = Array.from(event.target.files ?? []).slice(0, 5 - images.length);
    setUploadError(null);
    setUploading(true);
    try {
      const urls: string[] = [];
      for (const file of chosen) {
        const result = await uploadFile("/media/upload?purpose=product", file);
        urls.push(result.url);
      }
      setImages((prev) => [...prev, ...urls]);
    } catch (failure) {
      setUploadError(getDisplayErrorMessage(failure, "Unable to upload material image."));
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-5">
      <Link to={vendorRoutes.products} className="text-sm font-semibold text-indigo">‹ Products</Link>
      <h1 className="font-display text-3xl text-ink">Add a product</h1>

      {missing.length > 0 && (
        <p role="status" className="rounded-control bg-warning-wash px-4 py-3 text-sm text-warning">
          {missing.length === 1 ? "1 thing" : `${missing.length} things`} to do before you can list it: {missing.join(", ")}.
        </p>
      )}

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_300px]">
        <div className="flex flex-col gap-5">
          <section aria-label="Details" className="flex flex-col gap-4 rounded-card border border-line bg-surface p-5">
            <h2 className="font-semibold text-ink">Details</h2>
            <Field label="Product name" htmlFor="new-product-name" error={errors.name}
              help="What tailors search for: fabric, finish, colour. For example, French lace, royal blue.">
              <Input id="new-product-name" value={name} onChange={(e) => setName(e.target.value)} error={errors.name}
                aria-describedby="new-product-name-hint" />
            </Field>
            <Field label="Description" htmlFor="new-product-description" optional help="Weight, care, and how much a typical outfit needs.">
              <Textarea id="new-product-description" value={description} onChange={(e) => setDescription(e.target.value)} rows={3}
                aria-describedby="new-product-description-hint" />
            </Field>
          </section>

          <section aria-label="Price and stock" className="flex flex-col gap-4 rounded-card border border-line bg-surface p-5">
            <h2 className="font-semibold text-ink">Price and stock</h2>
            <div className="grid gap-4 sm:grid-cols-3">
              <Field label="Sold by" htmlFor="product-unit">
                <select id="product-unit" className="min-h-11 rounded-control border border-line-strong bg-surface px-3 text-ink focus:border-indigo focus:outline-none"
                  value={unit} onChange={(e) => setUnit(e.target.value as Unit)}>
                  <option value="yard">Yard</option><option value="meter">Metre</option>
                  <option value="roll">Roll</option><option value="piece">Piece</option>
                </select>
              </Field>
              <Field label={`Price per ${UNIT_LABEL[unit]} (₦)`} htmlFor="new-product-price" error={errors.basePrice}>
                <Input id="new-product-price" type="number" inputMode="decimal" min="0.01" step="0.01" value={basePrice}
                  onChange={(e) => setBasePrice(e.target.value)} error={errors.basePrice} aria-describedby="new-product-price-hint" />
              </Field>
              <Field label={`In stock (${UNIT_LABEL[unit]}s)`} htmlFor="new-product-stock" help="0 lists it as out of stock."
                error={stockValid ? undefined : "Enter a whole number, 0 or more."}>
                <Input id="new-product-stock" type="number" inputMode="numeric" min={0} max={MAX_STOCK} step={1} value={stock}
                  onChange={(event) => setStock(Number(event.target.value))} aria-describedby="new-product-stock-hint" />
              </Field>
            </div>
          </section>

          <section aria-label="Photos" className="flex flex-col gap-3 rounded-card border border-line bg-surface p-5">
            <h2 className="font-semibold text-ink">Photos</h2>
            <Field label="Material photos (1–5)" htmlFor="material-images"
              help="JPG, PNG or WebP. Daylight, fabric laid flat, plus one close-up.">
              <input id="material-images" type="file" accept="image/jpeg,image/png,image/webp" multiple
                aria-describedby="material-images-hint"
                className="text-sm text-ink file:mr-3 file:min-h-11 file:rounded-control file:border file:border-line-strong file:bg-surface file:px-4 file:font-semibold file:text-ink"
                disabled={uploading || images.length >= 5} onChange={(event) => { void addPhotos(event); }} />
            </Field>
            {uploading && <p role="status" className="text-sm text-ink-soft">Uploading material photos…</p>}
            {uploadError && <p role="alert" className="text-sm text-thread">{uploadError}</p>}
            {images.length > 0 && (
              <div className="grid grid-cols-3 gap-2 sm:grid-cols-5">
                {images.map((src, index) => (
                  <div key={src} className="relative">
                    <img src={src} alt={`Material photo ${index + 1}`} className="aspect-square w-full rounded-control object-cover" />
                    <button type="button" aria-label={`Remove photo ${index + 1}`}
                      className="absolute right-1 top-1 flex size-8 items-center justify-center rounded-full bg-surface text-ink shadow"
                      onClick={() => setImages((prev) => prev.filter((_, i) => i !== index))}>×</button>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>

        <aside aria-label="How tailors will see it" className="flex flex-col gap-3 self-start lg:sticky lg:top-6">
          <p className="text-[13px] font-semibold uppercase tracking-wide text-ink-soft">How tailors will see it</p>
          <div className="overflow-hidden rounded-card border border-line bg-surface">
            {images[0]
              ? <img src={images[0]} alt="" className="aspect-square w-full object-cover" />
              : <div className="flex aspect-square items-center justify-center bg-muslin text-sm text-ink-soft">No photo yet</div>}
            <div className="flex flex-col gap-1 p-3">
              <span className="font-semibold text-ink">{name.trim() || "Product name"}</span>
              <span className="font-mono text-sm text-ink">
                {Number(basePrice) > 0 ? formatCurrency(Number(basePrice), "NGN") : "₦ —"} / {UNIT_LABEL[unit]}
              </span>
              <span className="text-[13px] text-ink-soft">{stock > 0 ? "In stock" : "Out of stock"}</span>
            </div>
          </div>
          {formError && <p role="alert" className="text-sm text-thread">{formError}</p>}
          <Button size="lg" onClick={() => { void handleSubmit(); }} isLoading={isSubmitting}
            disabled={uploading || images.length === 0 || !stockValid}>Add product</Button>
          <p className="text-[13px] text-ink-soft">If saving fails, everything you typed stays here so you can try again.</p>
        </aside>
      </div>
    </div>
  );
}
