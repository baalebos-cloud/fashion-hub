import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { Order } from "@/types/order";

export interface MaterialCheckout {
  cart_id: string;
  cart_revision: number;
  vendor_id: string;
  delivery_address_id: string;
  idempotency_key: string;
}

/** One order/payment per vendor. Keep the same payload and key on retry. */
export const checkoutApi = {
  async submit(payload: MaterialCheckout): Promise<Order> {
    return (await apiClient.post<Order>(endpoints.checkout.submit, payload)).data;
  },
};
