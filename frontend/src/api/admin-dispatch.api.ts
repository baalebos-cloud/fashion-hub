import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";

export interface AdminDispatchBoard {
  unassigned_count: number;
  active_count: number;
  available_verified_riders: number;
  pending: Array<{ id: string; order_id: string; status: string; created_at: string }>;
  active: Array<{
    id: string;
    order_id: string;
    status: string;
    delivery_partner_id: string | null;
    vehicle_type: string | null;
    created_at: string;
  }>;
}

export const adminDispatchApi = {
  async board(): Promise<AdminDispatchBoard> {
    return (await apiClient.get<AdminDispatchBoard>(endpoints.adminDispatch.board)).data;
  },
};
