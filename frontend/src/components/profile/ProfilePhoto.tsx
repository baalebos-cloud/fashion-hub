import { apiClient } from "@/lib/api/client";
import { ImageUploader } from "@/components/common/ImageUploader";

export function ProfilePhoto({ currentUrl, onUploaded }: { currentUrl?: string | null; onUploaded: (url: string) => void }) {
  return (
    <ImageUploader
      uploadEndpoint="/media/upload?purpose=avatar"
      currentImageUrl={currentUrl}
      onUploaded={(url) => { void apiClient.patch("/users/me", { profile_photo_url: url }).then(() => onUploaded(url)); }}
      label="Change photo"
    />
  );
}
