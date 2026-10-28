import { create } from "zustand";
import { notificationsApi } from "@/api/notifications.api";
import type { AppNotification } from "@/types/notification";

interface NotificationState {
  items: AppNotification[];
  unreadCount: number;
  isLoading: boolean;
  error: string | null;
  fetchAll: () => Promise<void>;
  markRead: (id: string) => Promise<void>;
}

export const useNotificationStore = create<NotificationState>((set, get) => ({
  items: [],
  unreadCount: 0,
  isLoading: false,
  error: null,

  fetchAll: async () => {
    set({ isLoading: true, error: null });
    try {
      const { items } = await notificationsApi.list();
      set({ items, unreadCount: items.filter((n) => !n.is_read).length });
    } catch {
      // Background polling must never become an unhandled page-level rejection.
      // Keep last known notifications rather than inventing an empty inbox.
      set({ error: "Notifications are temporarily unavailable." });
    } finally {
      set({ isLoading: false });
    }
  },

  markRead: async (id) => {
    try {
      await notificationsApi.markRead(id);
    } catch {
      set({ error: "Could not mark the notification as read. Please retry." });
      return;
    }
    const items = get().items.map((n) => (n.id === id ? { ...n, is_read: true } : n));
    set({ items, unreadCount: items.filter((n) => !n.is_read).length, error: null });
  },
}));
