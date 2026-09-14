import { ProfileHeader } from "@/components/profile/ProfileHeader";
import { ProfessionalPortfolio } from "./ProfessionalPortfolio";
import { ProfessionalServices } from "./ProfessionalServices";
import { ProfessionalReviews } from "./ProfessionalReviews";
import { ProfessionalLocation } from "./ProfessionalLocation";
import { Button } from "@/components/ui/button";
import type { Professional } from "@/types/professional";
import type { User } from "@/types/user";

export interface ProfessionalProfileProps {
  professional: Professional;
  user: User;
  onOrder?: () => void;
}

export function ProfessionalProfile({ professional, user, onOrder }: ProfessionalProfileProps) {
  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-8">
      <div className="flex items-start justify-between">
        <ProfileHeader user={user} isVerified={professional.is_verified} />
        {onOrder && (
          <Button onClick={onOrder} disabled={!professional.accepts_new_orders}>
            {professional.accepts_new_orders ? "Place an order" : "Not accepting orders"}
          </Button>
        )}
      </div>

      {professional.bio && <p className="text-sm text-ink-soft">{professional.bio}</p>}

      <ProfessionalServices professionalId={professional.id} />
      <ProfessionalPortfolio images={[]} />
      <ProfessionalLocation location={null} />
      <ProfessionalReviews professionalId={professional.id} averageRating={professional.average_rating} reviewCount={professional.review_count} />
    </div>
  );
}
