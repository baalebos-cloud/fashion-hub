import { apiClient } from "@/lib/api/client";
import type { JourneyMilestone } from "@/types/dispatch";

export interface CreatedShareLink { id: string; url: string; label: string | null; expires_at: string }
export interface ShareLinkSummary {
  id: string; label: string | null; created_at: string; expires_at: string;
  active: boolean; revoked: boolean; access_count: number; last_accessed_at: string | null;
}
/** What a recipient sees without an account: no address, phone, price, GPS or handover code. */
export interface PublicTracking {
  tracking_number: string;
  seller_name: string;
  kind: "garment" | "materials";
  status: string;
  delivery_status: string | null;
  dropoff_area: string | null;
  milestones: JourneyMilestone[];
  eta_minutes: number | null;
  eta_basis: string | null;
  rider: { first_name: string; vehicle_type: string | null; is_verified: boolean; rating: number } | null;
  link_expires_at: string;
}

export const trackingLinksApi = {
  async create(orderId: string, label?: string): Promise<CreatedShareLink> {
    return (await apiClient.post<CreatedShareLink>(`/orders/${orderId}/share-links`, { label: label?.trim() || null })).data;
  },
  async list(orderId: string): Promise<ShareLinkSummary[]> {
    return (await apiClient.get<ShareLinkSummary[]>(`/orders/${orderId}/share-links`)).data;
  },
  async revoke(orderId: string, linkId: string): Promise<void> {
    await apiClient.delete(`/orders/${orderId}/share-links/${linkId}`);
  },
  async publicView(token: string): Promise<PublicTracking> {
    return (await apiClient.get<PublicTracking>(`/public/track/${encodeURIComponent(token)}`)).data;
  },
};
