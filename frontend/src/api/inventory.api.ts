import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { Inventory } from "@/types/product";
export const inventoryApi = {
  async list(page = 1): Promise<Inventory[]> { return (await apiClient.get<Inventory[]>(endpoints.inventory.list, { params: { page } })).data; },
  /** Every stock row, page by page (100 per page, capped at 50 pages), so low-stock counts are complete. */
  async listAll(): Promise<Inventory[]> {
    const all: Inventory[] = [];
    for (let page = 1; page <= 50; page += 1) {
      const rows = (await apiClient.get<Inventory[]>(endpoints.inventory.list, { params: { page, page_size: 100 } })).data;
      all.push(...rows);
      if (rows.length < 100) break;
    }
    return all;
  },
  async restock(variantId: string, quantity: number, idempotencyKey: string): Promise<Inventory> {
    return (await apiClient.post<Inventory>(endpoints.inventory.restock(variantId), { quantity_to_add: quantity, idempotency_key: idempotencyKey })).data;
  },
};
