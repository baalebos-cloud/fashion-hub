import { useState } from "react";
import { ImageUploader } from "@/components/common/ImageUploader";
import { MeasurementFieldSelector } from "./MeasurementFieldSelector";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { designsApi } from "@/api/designs.api";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import type { Design } from "@/types/design";

export function DesignUpload({ onCreated }: { onCreated: (design: Design) => void }) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [basePrice, setBasePrice] = useState("");
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [requiredFields, setRequiredFields] = useState<string[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    setIsSubmitting(true);
    setError(null);
    try {
      const created = await designsApi.create({
        title,
        description: description || undefined,
        base_price: Number(basePrice) || 0,
        required_measurement_fields: requiredFields.length > 0 ? requiredFields : undefined,
      });
      onCreated(created);
      setTitle("");
      setDescription("");
      setBasePrice("");
      setRequiredFields([]);
    } catch (err) {
      setError(getDisplayErrorMessage(err, "Couldn't add this design."));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="flex max-w-sm flex-col gap-4">
      <ImageUploader uploadEndpoint="/designs/images" currentImageUrl={imageUrl} onUploaded={setImageUrl} label="Add photo" />
      <Input placeholder="Title" value={title} onChange={(e) => setTitle(e.target.value)} />
      <Textarea placeholder="Description" value={description} onChange={(e) => setDescription(e.target.value)} rows={3} />
      <Input type="number" placeholder="Starting price" value={basePrice} onChange={(e) => setBasePrice(e.target.value)} />
      <MeasurementFieldSelector selected={requiredFields} onChange={setRequiredFields} />
      {error && <p className="text-sm text-thread">{error}</p>}
      <Button onClick={handleSubmit} isLoading={isSubmitting} className="self-start" disabled={!title}>
        Add design
      </Button>
    </div>
  );
}
