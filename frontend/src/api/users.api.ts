import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { User } from "@/types/user";
import type { PaginatedResponse } from "@/types/api";

export const usersApi = {
  async getCurrentUser(): Promise<User> {
    const response = await apiClient.get<User>(endpoints.users.me);
    return response.data;
  },

  async updateProfile(payload: Partial<Pick<User, "full_name" | "timezone" | "profile_photo_url" | "whatsapp_number">>): Promise<User> {
    const response = await apiClient.patch<User>(endpoints.users.me, payload);
    return response.data;
  },

  async adminList(params: { role?: string; page?: number; pageSize?: number } = {}): Promise<PaginatedResponse<User & { is_active: boolean; created_at: string | null }>> {
    const response = await apiClient.get(endpoints.admin.users, {
      params: { role: params.role, page: params.page ?? 1, page_size: params.pageSize ?? 50 },
    });
    return response.data;
  },
};
