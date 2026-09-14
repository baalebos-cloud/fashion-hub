import { create } from "zustand";
import { notificationsApi } from "@/api/notifications.api";
import type { AppNotification } from "@/types/notification";

interface NotificationState {
  items: AppNotification[];
  unreadCount: number;
  isLoading: boolean;
  fetchAll: () => Promise<void>;
  markRead: (id: string) => Promise<void>;
}

export const useNotificationStore = create<NotificationState>((set, get) => ({
  items: [],
  unreadCount: 0,
  isLoading: false,

  fetchAll: async () => {
    set({ isLoading: true });
    try {
      const { items } = await notificationsApi.list();
      set({ items, unreadCount: items.filter((n) => !n.is_read).length });
    } finally {
      set({ isLoading: false });
    }
  },

  markRead: async (id) => {
    await notificationsApi.markRead(id);
    const items = get().items.map((n) => (n.id === id ? { ...n, is_read: true } : n));
    set({ items, unreadCount: items.filter((n) => !n.is_read).length });
  },
}));
