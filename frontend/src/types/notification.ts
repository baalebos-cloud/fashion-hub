export type NotificationChannel = "in_app" | "email" | "sms" | "push";

export interface AppNotification {
  id: string;
  channel: NotificationChannel;
  event_type: string;
  title: string;
  body?: string | null;
  is_read: boolean;
  created_at: string;
}
