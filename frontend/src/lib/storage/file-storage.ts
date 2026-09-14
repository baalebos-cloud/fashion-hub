import { apiClient } from "@/lib/api/client";

/**
 * Uploads a file to the backend, which is the only party that ever talks
 * to the configured StorageProvider (local disk in dev, S3-compatible in
 * production — see backend/app/integrations/storage/). The frontend never
 * receives or uses storage credentials directly.
 */
export async function uploadFile(
  endpointPath: string,
  file: File,
  fieldName = "file"
): Promise<{ url: string }> {
  const formData = new FormData();
  formData.append(fieldName, file);

  const response = await apiClient.post<{ url: string }>(endpointPath, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}
