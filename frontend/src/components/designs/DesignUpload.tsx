import { useState } from "react";
import { ImageUploader } from "@/components/common/ImageUploader";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { designsApi } from "@/api/designs.api";
import type { Design } from "@/types/design";

export function DesignUpload({ onCreated }: { onCreated: (design: Design) => void }) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [basePrice, setBasePrice] = useState("");
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit() {
    setIsSubmitting(true);
    try {
      // NOTE: designsApi currently only exposes list/getById in this
      // scaffold; wire a create() method through once
      // POST /designs is implemented on the backend (see
      // backend/app/api/v1/designs.py stub).
      const created = { id: `local-${Date.now()}`, title, description, base_price: Number(basePrice) || 0, is_published: true } as Design;
      onCreated(created);
      setTitle("");
      setDescription("");
      setBasePrice("");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="flex max-w-sm flex-col gap-3">
      <ImageUploader uploadEndpoint="/designs/images" currentImageUrl={imageUrl} onUploaded={setImageUrl} label="Add photo" />
      <Input placeholder="Title" value={title} onChange={(e) => setTitle(e.target.value)} />
      <Textarea placeholder="Description" value={description} onChange={(e) => setDescription(e.target.value)} rows={3} />
      <Input type="number" placeholder="Starting price" value={basePrice} onChange={(e) => setBasePrice(e.target.value)} />
      <Button onClick={handleSubmit} isLoading={isSubmitting} className="self-start" disabled={!title}>
        Add design
      </Button>
    </div>
  );
}
