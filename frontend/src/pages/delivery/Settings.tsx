import { NotificationPreferences } from "@/components/notifications/NotificationPreferences";
import { LogoutButton } from "@/components/auth/LogoutButton";
import { DeleteAccount } from "@/components/account/DeleteAccount";

export default function Settings() {
  return (
    <div className="flex max-w-md flex-col gap-8">
      <h1 className="font-display text-xl text-ink">Settings</h1>
      <NotificationPreferences />
      <LogoutButton className="self-start" />
      <DeleteAccount />
    </div>
  );
}
