import { useAuth } from "@/hooks/use-auth";
import { ProfileHeader } from "@/components/profile/ProfileHeader";
import { ProfilePhoto } from "@/components/profile/ProfilePhoto";
import { useAuthStore } from "@/store/auth.store";
import { ProfileForm } from "@/components/profile/ProfileForm";
import { RiderStatusCard } from "@/components/delivery/RiderStatusCard";
import { LoadingScreen } from "@/components/common/LoadingScreen";

export default function Profile() {
  const { user } = useAuth();
  const refreshUser = useAuthStore((st) => st.refreshUser);

  if (!user) return <LoadingScreen />;

  return (
    <div className="flex max-w-lg flex-col gap-8">
      <ProfileHeader user={user} />
      <ProfilePhoto currentUrl={user.profile_photo_url} onUploaded={() => void refreshUser()} />
      <RiderStatusCard />
      <ProfileForm />
    </div>
  );
}
