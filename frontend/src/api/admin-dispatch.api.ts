import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";

export interface AdminDispatchBoard {
  unassigned_count: number;
  active_count: number;
  available_verified_riders: number;
  open_issue_count: number;
  auto_offers_enabled: boolean;
  pending: Array<{ id: string; order_id: string; order_number: string | null; order_type: string | null;
    status: string; created_at: string;
    /** Auto-dispatch: rider currently holding the exclusive offer, if any. */
    offered_to?: string | null; offer_expires_at?: string | null; offer_attempt?: number | null }>;
  active: Array<{
    id: string;
    order_id: string;
    order_number: string | null;
    order_type: string | null;
    status: string;
    delivery_partner_id: string | null;
    rider_first_name: string | null;
    vehicle_type: string | null;
    open_issue_count: number;
    tracking?: { state: string; age_seconds: number | null } | null;
    created_at: string;
  }>;
}

export interface DispatchIssue {
  id: string;
  delivery_id: string;
  order_id: string;
  order_number: string;
  issue_type: string;
  description: string;
  status: "OPEN" | "INVESTIGATING";
  rider_first_name: string;
  delivery_status: string;
  has_photo: boolean;
  created_at: string;
}

export interface AvailableRider { id: string; first_name: string; vehicle_type: string | null; rating: number }

/** Admin-only dispatch control. Every mutation needs a reason and is audit-logged server-side. */
export interface DeliveryEvent {
  id: string;
  event_type: string;
  actor_role: string | null;
  details: Record<string, unknown>;
  created_at: string;
}

export const adminDispatchApi = {
  async events(deliveryId: string): Promise<DeliveryEvent[]> {
    return (await apiClient.get<DeliveryEvent[]>(`/admin/dispatch/deliveries/${deliveryId}/events`)).data;
  },
  async board(): Promise<AdminDispatchBoard> {
    return (await apiClient.get<AdminDispatchBoard>(endpoints.adminDispatch.board)).data;
  },
  async issues(): Promise<DispatchIssue[]> {
    return (await apiClient.get<DispatchIssue[]>("/admin/dispatch/issues")).data;
  },
  async riders(): Promise<AvailableRider[]> {
    return (await apiClient.get<AvailableRider[]>("/admin/dispatch/riders")).data;
  },
  async release(deliveryId: string, reason: string): Promise<void> {
    await apiClient.post(`/admin/dispatch/deliveries/${deliveryId}/release`, { reason });
  },
  async reassign(deliveryId: string, partnerId: string, reason: string): Promise<void> {
    await apiClient.post(`/admin/dispatch/deliveries/${deliveryId}/reassign`, { partner_id: partnerId, reason });
  },
  async cancelRequest(requestId: string, reason: string): Promise<void> {
    await apiClient.post(`/admin/dispatch/requests/${requestId}/cancel`, { reason });
  },
  async updateIssue(issueId: string, status: "INVESTIGATING" | "RESOLVED", note?: string): Promise<void> {
    await apiClient.patch(`/admin/dispatch/issues/${issueId}`, { status, note: note?.trim() || null });
  },
};
