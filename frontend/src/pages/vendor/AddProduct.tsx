import { useState } from "react";
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
  const [basePrice, setBasePrice] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit() {
    const validationErrors = validateProduct({ name, basePrice: Number(basePrice) });
    if (validationErrors.length > 0) {
      setErrors(Object.fromEntries(validationErrors.map((e) => [e.field, e.message])));
      return;
    }
    setErrors({});
    setFormError(null);
    setIsSubmitting(true);
    try {
      await productsApi.create({ name, description, base_price: Number(basePrice) });
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
        <Input placeholder="Product name" value={name} onChange={(e) => setName(e.target.value)} error={errors.name} />
        {errors.name && <p className="mt-1 text-xs text-thread">{errors.name}</p>}
      </div>
      <Textarea placeholder="Description" value={description} onChange={(e) => setDescription(e.target.value)} rows={3} />
      <div>
        <Input type="number" placeholder="Price" value={basePrice} onChange={(e) => setBasePrice(e.target.value)} error={errors.basePrice} />
        {errors.basePrice && <p className="mt-1 text-xs text-thread">{errors.basePrice}</p>}
      </div>
      {formError && <p className="text-sm text-thread">{formError}</p>}
      <Button onClick={handleSubmit} isLoading={isSubmitting}>Add product</Button>
    </div>
  );
}
