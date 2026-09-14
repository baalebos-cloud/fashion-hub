import { useEffect } from "react";
import { useNotificationStore } from "@/store/notification.store";

export function useNotifications() {
  const { items, unreadCount, isLoading, fetchAll, markRead } = useNotificationStore();

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  return { items, unreadCount, isLoading, markRead, refetch: fetchAll };
}
