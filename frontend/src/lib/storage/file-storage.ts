import { apiClient } from "@/lib/api/client";

/** Uses the established bearer-token and refresh interceptors. The browser
 * supplies the multipart boundary; never set Content-Type explicitly. */
export async function uploadFile(
  endpointPath: string,
  file: File,
  fieldName = "file",
): Promise<{ url: string; document_storage_key?: string; filename?: string; size_bytes?: number }> {
  const formData = new FormData();
  formData.append(fieldName, file);
  const response = await apiClient.post<{ url: string; filename?: string; size_bytes?: number }>(
    endpointPath, formData,
    { headers: { "Content-Type": undefined }, timeout: 120000 },
  );
  return response.data;
}

/** Unified media API. Private purposes return an opaque storage key. */
export function uploadMedia(file: File, category: "design" | "portfolio" | "product" | "kyc" | "kyb" | "delivery") {
  return uploadFile(`/media/upload?purpose=${category}`, file);
}
