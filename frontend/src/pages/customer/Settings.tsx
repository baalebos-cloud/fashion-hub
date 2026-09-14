import { NotificationPreferences } from "@/components/notifications/NotificationPreferences";
import { LogoutButton } from "@/components/auth/LogoutButton";

export default function Settings() {
  return (
    <div className="flex max-w-md flex-col gap-8">
      <h1 className="font-display text-xl text-ink">Settings</h1>
      <div>
        <h2 className="mb-3 text-sm font-medium text-ink-soft">Notifications</h2>
        <NotificationPreferences />
      </div>
      <LogoutButton className="self-start" />
    </div>
  );
}
