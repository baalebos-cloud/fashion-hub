import { useAuth } from "@/hooks/use-auth";
import { ProfileHeader } from "@/components/profile/ProfileHeader";
import { ProfileForm } from "@/components/profile/ProfileForm";
import { RiderStatusCard } from "@/components/delivery/RiderStatusCard";
import { LoadingScreen } from "@/components/common/LoadingScreen";

export default function Profile() {
  const { user } = useAuth();

  if (!user) return <LoadingScreen />;

  return (
    <div className="flex max-w-lg flex-col gap-8">
      <ProfileHeader user={user} />
      <RiderStatusCard />
      <ProfileForm />
    </div>
  );
}
