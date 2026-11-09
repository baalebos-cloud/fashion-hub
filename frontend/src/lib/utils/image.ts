/** Client-side image validation before upload (see lib/storage/file-storage.ts).
 * Mirrors backend/app/utils/file_upload.py's constraints so the person
 * gets instant feedback instead of waiting on a round trip to fail. */
import { isPhoto } from "@/lib/media/prepare-image";

/** Photos of any size or format (JPEG, PNG, WebP, iPhone HEIC) are accepted: they are resized and
 * turned into JPEG before upload. Only absurdly large files are refused up front. */
const MAX_SIZE_BYTES = 50 * 1024 * 1024;
export const PHOTO_ACCEPT = "image/*,.heic,.heif";

export function validateImageFile(file: File): string | null {
  if (!isPhoto(file)) {
    return "Please choose a photo (JPEG, PNG, WebP or iPhone HEIC).";
  }
  if (file.size > MAX_SIZE_BYTES) {
    return "This photo is too large. Choose one under 50 MB.";
  }
  return null;
}

export function readImageAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = () => reject(new Error("Failed to read image file."));
    reader.readAsDataURL(file);
  });
}
