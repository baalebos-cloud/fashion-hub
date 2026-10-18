import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { Inventory } from "@/types/product";
export const inventoryApi = {
  async list(page = 1): Promise<Inventory[]> { return (await apiClient.get<Inventory[]>(endpoints.inventory.list, { params: { page } })).data; },
  async restock(variantId: string, quantity: number, idempotencyKey: string): Promise<Inventory> {
    return (await apiClient.post<Inventory>(endpoints.inventory.restock(variantId), { quantity_to_add: quantity, idempotency_key: idempotencyKey })).data;
  },
};
