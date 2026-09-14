import { useState } from "react";
import { Switch } from "@/components/ui/switch";
import type { NotificationChannel } from "@/types/notification";

const CHANNELS: { key: NotificationChannel; label: string }[] = [
  { key: "email", label: "Email" },
  { key: "sms", label: "SMS" },
  { key: "push", label: "Push notifications" },
];

/**
 * Client-side-only for now: the backend doesn't yet expose a
 * NotificationPreference endpoint (see backend/docs/notifications.md), so
 * this persists to localStorage as a placeholder rather than losing the
 * person's choice entirely. Wire to a real API once that endpoint exists.
 */
export function NotificationPreferences() {
  const [enabled, setEnabled] = useState<Record<NotificationChannel, boolean>>({
    in_app: true,
    email: true,
    sms: false,
    push: false,
  });

  return (
    <div className="flex max-w-sm flex-col gap-3">
      {CHANNELS.map((channel) => (
        <label key={channel.key} className="flex items-center justify-between text-sm text-ink">
          {channel.label}
          <Switch
            checked={enabled[channel.key]}
            onChange={(checked) => setEnabled((prev) => ({ ...prev, [channel.key]: checked }))}
            label={channel.label}
          />
        </label>
      ))}
    </div>
  );
}
