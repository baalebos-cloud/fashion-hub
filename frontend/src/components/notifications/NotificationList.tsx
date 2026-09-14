import { useNotifications } from "@/hooks/use-notifications";
import { NotificationItem } from "./NotificationItem";
import { EmptyState } from "@/components/ui/empty-state";

export function NotificationList() {
  const { items, markRead } = useNotifications();

  if (items.length === 0) {
    return (
      <div className="w-72 p-4">
        <EmptyState title="No notifications" description="You're all caught up." />
      </div>
    );
  }

  return (
    <div className="max-h-96 w-72 overflow-y-auto">
      {items.map((notification) => (
        <NotificationItem key={notification.id} notification={notification} onRead={() => markRead(notification.id)} />
      ))}
    </div>
  );
}
