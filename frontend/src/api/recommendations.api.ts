import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";

export type RelatedReason = "bought_together" | "viewed_together" | "similar" | "same_vendor";

export type RelatedProduct = {
  product_id: string;
  name: string;
  vendor_name: string;
  primary_image_url: string | null;
  price_ngn: number;
  currency: string;
  unit_of_measure: string;
  reason: RelatedReason;
  /** true when learned from shoppers' behaviour; false for the category/shop fallback */
  learned: boolean;
};

export const recommendationsApi = {
  async similarProducts(productId: string, limit = 8): Promise<RelatedProduct[]> {
    const result = await apiClient.get<{ items: RelatedProduct[] }>(
      endpoints.recommendations.similarProducts(productId), { params: { limit } });
    return result.data.items;
  },
  async boughtTogether(productIds: string[], limit = 6): Promise<RelatedProduct[]> {
    const params = new URLSearchParams();
    productIds.forEach((id) => params.append("product_id", id));
    params.set("limit", String(limit));
    const result = await apiClient.get<{ items: RelatedProduct[] }>(endpoints.recommendations.boughtTogether, { params });
    return result.data.items;
  },
};
