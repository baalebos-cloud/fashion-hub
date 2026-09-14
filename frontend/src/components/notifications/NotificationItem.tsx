import { cn } from "@/lib/utils/cn";
import { DateTimeDisplay } from "@/components/common/DateTimeDisplay";
import type { AppNotification } from "@/types/notification";

export function NotificationItem({ notification, onRead }: { notification: AppNotification; onRead: () => void }) {
  return (
    <button
      type="button"
      onClick={onRead}
      className={cn(
        "block w-full border-b border-line px-3.5 py-3 text-left last:border-0 hover:bg-muslin/60",
        !notification.is_read && "bg-muslin/30"
      )}
    >
      <div className="text-sm font-medium text-ink">{notification.title}</div>
      {notification.body && <div className="mt-0.5 text-xs text-ink-soft">{notification.body}</div>}
      <div className="mt-1 text-[11px] text-ink-soft/70">
        <DateTimeDisplay value={notification.created_at} format="relative" />
      </div>
    </button>
  );
}
