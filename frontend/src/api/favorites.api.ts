import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";

export const favoritesApi = {
  /** Returns the new state: true if now favorited, false if removed. */
  async toggle(favoriteType: "professional" | "design" | "vendor_product", favoriteRefId: string): Promise<boolean> {
    const response = await apiClient.post<{ favorited: boolean }>(endpoints.favorites.toggle, {
      favorite_type: favoriteType,
      favorite_ref_id: favoriteRefId,
    });
    return response.data.favorited;
  },
};
