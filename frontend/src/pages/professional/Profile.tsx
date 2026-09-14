import { useAuth } from "@/hooks/use-auth";
import { ProfileHeader } from "@/components/profile/ProfileHeader";
import { ProfilePhoto } from "@/components/profile/ProfilePhoto";
import { ProfileForm } from "@/components/profile/ProfileForm";
import { LoadingScreen } from "@/components/common/LoadingScreen";

export default function Profile() {
  const { user } = useAuth();
  if (!user) return <LoadingScreen />;

  return (
    <div className="flex max-w-lg flex-col gap-8">
      <ProfileHeader user={user} />
      <ProfilePhoto currentUrl={user.profile_photo_url} onUploaded={() => {}} />
      <ProfileForm />
    </div>
  );
}
