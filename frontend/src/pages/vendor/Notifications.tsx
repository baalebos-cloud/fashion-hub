import { useNotifications } from "@/hooks/use-notifications";
import { NotificationItem } from "@/components/notifications/NotificationItem";
import { EmptyState } from "@/components/ui/empty-state";

export default function Notifications() {
  const { items, markRead } = useNotifications();
  if (items.length === 0) return <EmptyState title="You're all caught up" />;

  return (
    <div>
      <h1 className="mb-6 font-display text-xl text-ink">Notifications</h1>
      <div className="divide-y divide-line rounded-card border border-line">
        {items.map((n) => <NotificationItem key={n.id} notification={n} onRead={() => markRead(n.id)} />)}
      </div>
    </div>
  );
}
