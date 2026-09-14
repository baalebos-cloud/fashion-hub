import { useNotifications } from "@/hooks/use-notifications";
import { NotificationItem } from "@/components/notifications/NotificationItem";
import { EmptyState } from "@/components/ui/empty-state";

export default function Notifications() {
  const { items, markRead } = useNotifications();

  return (
    <div>
      <h1 className="mb-6 font-display text-xl text-ink">Notifications</h1>
      {items.length === 0 ? (
        <EmptyState title="You're all caught up" />
      ) : (
        <div className="divide-y divide-line rounded-card border border-line">
          {items.map((notification) => (
            <NotificationItem key={notification.id} notification={notification} onRead={() => markRead(notification.id)} />
          ))}
        </div>
      )}
    </div>
  );
}
