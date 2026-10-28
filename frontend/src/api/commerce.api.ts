import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";

export type CatalogRecommendation = {
  product_id: string;
  title: string;
  price_ngn: string;
  category: string;
  available_units: number;
};

export type CatalogRecommendationResponse = {
  currency: "NGN";
  items: CatalogRecommendation[];
  catalog_sample_limit: number;
  note: string;
};

export const commerceApi = {
  async recommendations(budgetNgn: number): Promise<CatalogRecommendationResponse> {
    const result = await apiClient.get<CatalogRecommendationResponse>(
      endpoints.commerce.recommendations, {
        params: { budget_ngn: budgetNgn, limit: 5 },
      },
    );
    return result.data;
  },
};
