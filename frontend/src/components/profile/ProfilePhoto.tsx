import { useState } from "react";
import { apiClient } from "@/lib/api/client";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import { ImageUploader } from "@/components/common/ImageUploader";

export function ProfilePhoto({ currentUrl, onUploaded }: { currentUrl?: string | null; onUploaded: (url: string) => void }) {
  const [error, setError] = useState<string | null>(null);

  async function savePhoto(url: string) {
    setError(null);
    try {
      await apiClient.patch("/users/me", { profile_photo_url: url });
      onUploaded(url);
    } catch (failure) {
      setError(getDisplayErrorMessage(failure, "Photo uploaded, but could not be saved to your profile."));
    }
  }

  return (
    <div>
      <ImageUploader
        uploadEndpoint="/media/upload?purpose=avatar"
        currentImageUrl={currentUrl}
        onUploaded={(url) => { void savePhoto(url); }}
        label="Change photo"
      />
      {error && <p role="alert" className="text-sm text-thread">{error}</p>}
    </div>
  );
}
