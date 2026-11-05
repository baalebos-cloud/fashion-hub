import { apiClient } from "@/lib/api/client";
import type { CallContact, CallParty, StartedCall } from "@/types/call";

/** Masked calls: the API never returns anyone's phone number. */
export const callsApi = {
  async contacts(orderId: string): Promise<CallContact[]> {
    return (await apiClient.get<CallContact[]>(`/calls/orders/${orderId}/contacts`)).data;
  },
  async start(orderId: string, callee: CallParty): Promise<StartedCall> {
    return (await apiClient.post<StartedCall>("/calls", { order_id: orderId, callee })).data;
  },
};
