import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";

export type FavoriteType = "professional" | "design" | "vendor_product";

/** A saved item with what the Favorites page shows (backend/app/api/v1/favorites.py). */
export interface FavoriteItem {
  id: string;
  favorite_type: FavoriteType;
  favorite_ref_id: string;
  title: string | null;
  subtitle: string | null;
  image_url: string | null;
  price: number | null;
  currency: string | null;
  professional_id: string | null;
  /** False when the listing is no longer shown publicly. */
  available: boolean;
}

export const favoritesApi = {
  async list(): Promise<FavoriteItem[]> {
    return (await apiClient.get<FavoriteItem[]>(endpoints.favorites.toggle)).data;
  },
  /** Returns the new state: true if now favorited, false if removed. */
  async toggle(favoriteType: FavoriteType, favoriteRefId: string): Promise<boolean> {
    const response = await apiClient.post<{ favorited: boolean }>(endpoints.favorites.toggle, {
      favorite_type: favoriteType,
      favorite_ref_id: favoriteRefId,
    });
    return response.data.favorited;
  },
};
