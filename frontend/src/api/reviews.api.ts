import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { Review } from "@/types/review";

export const reviewsApi = {
  async mine(): Promise<Review[]> {
    const response = await apiClient.get<Review[]>("/reviews/mine");
    return response.data;
  },
  async listForProfessional(professionalId: string): Promise<Review[]> {
    const response = await apiClient.get<Review[]>(endpoints.reviews.forProfessional(professionalId));
    return response.data;
  },
};
