import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api/client";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import { PortfolioGrid } from "@/components/profile/PortfolioGrid";
import { ImageUploader } from "@/components/common/ImageUploader";
import type { PortfolioImage } from "@/components/profile/PortfolioGrid";

export default function Portfolio() {
  const [images, setImages] = useState<PortfolioImage[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    apiClient.get<PortfolioImage[]>("/professionals/me/portfolio")
      .then(({ data }) => setImages(data))
      .catch(err => setError(getDisplayErrorMessage(err, "Unable to load portfolio.")));
  }, []);

  async function addImage(url: string) {
    setSaving(true);
    setError(null);
    try {
      const { data } = await apiClient.post<PortfolioImage>("/professionals/me/portfolio", { image_url: url });
      setImages(previous => [data, ...previous]);
    } catch (err) {
      setError(getDisplayErrorMessage(err, "Photo uploaded, but could not be saved to your portfolio."));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="font-display text-xl text-ink">Portfolio</h1>
      <ImageUploader
        uploadEndpoint="/media/upload?purpose=portfolio"
        onUploaded={(url) => { void addImage(url); }}
        label="Add photo"
      />
      {saving && <p role="status">Saving photo to portfolio…</p>}
      {error && <p role="alert" className="text-sm text-thread">{error}</p>}
      <PortfolioGrid images={images} />
    </div>
  );
}
