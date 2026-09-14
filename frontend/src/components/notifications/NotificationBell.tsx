import { useState } from "react";
import { Dropdown } from "@/components/ui/dropdown";
import { NotificationList } from "./NotificationList";

export function NotificationBell({ unreadCount }: { unreadCount: number }) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <Dropdown
      trigger={
        <button
          type="button"
          aria-label={`Notifications${unreadCount > 0 ? ` (${unreadCount} unread)` : ""}`}
          onClick={() => setIsOpen((v) => !v)}
          className="relative flex h-10 w-10 items-center justify-center rounded-lg text-ink hover:bg-muslin"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path
              d="M18 8a6 6 0 10-12 0c0 7-3 9-3 9h18s-3-2-3-9"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <path d="M13.73 21a2 2 0 01-3.46 0" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
          {unreadCount > 0 && (
            <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-thread" aria-hidden="true" />
          )}
        </button>
      }
    >
      {isOpen && <NotificationList />}
    </Dropdown>
  );
}
