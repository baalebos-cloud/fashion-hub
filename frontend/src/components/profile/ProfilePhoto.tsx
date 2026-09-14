import { ImageUploader } from "@/components/common/ImageUploader";

export function ProfilePhoto({ currentUrl, onUploaded }: { currentUrl?: string | null; onUploaded: (url: string) => void }) {
  return (
    <ImageUploader
      uploadEndpoint="/users/me/photo"
      currentImageUrl={currentUrl}
      onUploaded={onUploaded}
      label="Change photo"
    />
  );
}
