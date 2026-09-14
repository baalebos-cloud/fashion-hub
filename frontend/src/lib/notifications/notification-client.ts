import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { AppNotification } from "@/types/notification";
import type { PaginatedResponse } from "@/types/api";

/** In-app notification fetch/mark-read — the actual dispatch (email/SMS/
 * push) is entirely backend-owned (backend/app/workers/*_tasks.py); the
 * frontend only ever reads the resulting in-app notification feed. */
export const notificationClient = {
  async list(unreadOnly = false): Promise<PaginatedResponse<AppNotification>> {
    const response = await apiClient.get<PaginatedResponse<AppNotification>>(endpoints.notifications.list, {
      params: { unread_only: unreadOnly },
    });
    return response.data;
  },

  async markRead(id: string): Promise<void> {
    await apiClient.post(endpoints.notifications.markRead(id));
  },
};
