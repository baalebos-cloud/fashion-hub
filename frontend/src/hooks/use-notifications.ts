import { useEffect } from "react";
import { useNotificationStore } from "@/store/notification.store";

/** Avoid querying private notifications before authentication has completed. */
export function useNotifications(enabled = true) {
  const { items, unreadCount, isLoading, error, fetchAll, markRead } = useNotificationStore();

  useEffect(() => {
    if (enabled) void fetchAll();
  }, [enabled, fetchAll]);

  return { items, unreadCount, isLoading, error, markRead, refetch: fetchAll };
}
