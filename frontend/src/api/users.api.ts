import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { User } from "@/types/user";

export const usersApi = {
  async getCurrentUser(): Promise<User> {
    const response = await apiClient.get<User>(endpoints.users.me);
    return response.data;
  },

  async updateProfile(payload: Partial<Pick<User, "full_name" | "timezone">>): Promise<User> {
    const response = await apiClient.patch<User>(endpoints.users.me, payload);
    return response.data;
  },
};
