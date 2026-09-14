import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { Order } from "@/types/order";

/**
 * Returns one Order per vendor represented in the cart (see
 * backend/docs/checkout.md) — the frontend then initializes a single
 * combined payment across all of them via payments.api.ts.
 */
export const checkoutApi = {
  async submit(cartId: string, deliveryAddressId: string): Promise<Order[]> {
    const response = await apiClient.post<Order[]>(endpoints.checkout.submit, {
      cart_id: cartId,
      delivery_address_id: deliveryAddressId,
    });
    return response.data;
  },
};
