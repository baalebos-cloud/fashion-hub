import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { CartSummary } from "@/types/cart";

export const cartApi = {
  async getSummary(): Promise<CartSummary> {
    const response = await apiClient.get<CartSummary>(endpoints.cart.summary);
    return response.data;
  },

  async addItem(productVariantId: string, quantity: number): Promise<CartSummary> {
    const response = await apiClient.post<CartSummary>(endpoints.cart.items, {
      product_variant_id: productVariantId,
      quantity,
    });
    return response.data;
  },

  async updateItem(cartItemId: string, quantity: number): Promise<CartSummary> {
    const response = await apiClient.patch<CartSummary>(endpoints.cart.item(cartItemId), { quantity });
    return response.data;
  },

  async removeItem(cartItemId: string): Promise<void> {
    await apiClient.delete(endpoints.cart.item(cartItemId));
  },
};
