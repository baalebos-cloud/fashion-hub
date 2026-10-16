import { Avatar } from "@/components/ui/avatar";
import { VerificationBadge } from "./VerificationBadge";
import { ROLE_LABELS } from "@/constants/roles";
import type { User } from "@/types/user";

export function ProfileHeader({ user, isVerified }: { user: User; isVerified?: boolean }) {
  return (
    <div className="flex items-center gap-4">
      <Avatar name={user.full_name} src={user.profile_photo_url} size="lg" />
      <div>
        <div className="flex items-center gap-2">
          <h1 className="font-display text-xl text-ink">{user.full_name}</h1>
          {isVerified && <VerificationBadge />}
        </div>
        <p className="text-sm text-ink-soft">{ROLE_LABELS[user.role]}</p>
      </div>
    </div>
  );
}
