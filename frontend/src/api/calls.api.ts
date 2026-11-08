import { apiClient } from "@/lib/api/client";
import type { AppCall, AppCallJoin, CallContact, CallParty, StartedCall } from "@/types/call";

/** Calls on an order. The API never returns anyone's phone number. */
export const callsApi = {
  async contacts(orderId: string): Promise<CallContact[]> {
    return (await apiClient.get<CallContact[]>(`/calls/orders/${orderId}/contacts`)).data;
  },
  async start(orderId: string, callee: CallParty): Promise<StartedCall> {
    return (await apiClient.post<StartedCall>("/calls", { order_id: orderId, callee })).data;
  },
  // ---- in-app calls ----
  async startApp(orderId: string, callee: CallParty): Promise<AppCallJoin> {
    return (await apiClient.post<AppCallJoin>("/calls/app", { order_id: orderId, callee })).data;
  },
  async incoming(): Promise<AppCall[]> {
    return (await apiClient.get<AppCall[]>("/calls/app/incoming")).data;
  },
  async status(callId: string): Promise<AppCall> {
    return (await apiClient.get<AppCall>(`/calls/app/${callId}`)).data;
  },
  async answer(callId: string): Promise<AppCallJoin> {
    return (await apiClient.post<AppCallJoin>(`/calls/app/${callId}/answer`)).data;
  },
  async decline(callId: string): Promise<AppCall> {
    return (await apiClient.post<AppCall>(`/calls/app/${callId}/decline`)).data;
  },
  async cancel(callId: string): Promise<AppCall> {
    return (await apiClient.post<AppCall>(`/calls/app/${callId}/cancel`)).data;
  },
  async end(callId: string): Promise<AppCall> {
    return (await apiClient.post<AppCall>(`/calls/app/${callId}/end`)).data;
  },
};
