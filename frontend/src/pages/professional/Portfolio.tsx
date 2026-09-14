import { useState } from "react";
import { PortfolioGrid } from "@/components/profile/PortfolioGrid";
import { ImageUploader } from "@/components/common/ImageUploader";
import type { PortfolioImage } from "@/components/profile/PortfolioGrid";

export default function Portfolio() {
  const [images, setImages] = useState<PortfolioImage[]>([]);

  return (
    <div className="flex flex-col gap-6">
      <h1 className="font-display text-xl text-ink">Portfolio</h1>
      <ImageUploader
        uploadEndpoint="/professionals/me/portfolio"
        onUploaded={(url) => setImages((prev) => [...prev, { id: `local-${Date.now()}`, image_url: url }])}
        label="Add photo"
      />
      <PortfolioGrid images={images} />
    </div>
  );
}
