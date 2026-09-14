import { useState } from "react";
import { useAuth } from "@/hooks/use-auth";
import { ProfileHeader } from "@/components/profile/ProfileHeader";
import { ProfileForm } from "@/components/profile/ProfileForm";
import { Switch } from "@/components/ui/switch";
import { LoadingScreen } from "@/components/common/LoadingScreen";

export default function Profile() {
  const { user } = useAuth();
  const [isAvailable, setIsAvailable] = useState(false);

  if (!user) return <LoadingScreen />;

  return (
    <div className="flex max-w-lg flex-col gap-8">
      <ProfileHeader user={user} />
      <label className="flex items-center justify-between text-sm text-ink">
        Available for deliveries
        <Switch checked={isAvailable} onChange={setIsAvailable} label="Available for deliveries" />
      </label>
      <ProfileForm />
    </div>
  );
}
