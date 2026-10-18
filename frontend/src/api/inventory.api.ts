import { apiClient } from "@/lib/api/client";
import type { Inventory } from "@/types/product";
export const inventoryApi = {
  async list(page = 1): Promise<Inventory[]> { return (await apiClient.get<Inventory[]>("/vendor-inventory", { params: { page } })).data; },
  async restock(variantId: string, quantity: number): Promise<Inventory> {
    return (await apiClient.post<Inventory>(`/vendor-inventory/${variantId}/restock`, { quantity_to_add: quantity })).data;
  },
};
