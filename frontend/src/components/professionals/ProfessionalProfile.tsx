import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api/client";
import type { PortfolioImage } from "@/components/profile/PortfolioGrid";
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
  const [portfolio, setPortfolio] = useState<PortfolioImage[]>([]);
  const [portfolioLoading, setPortfolioLoading] = useState(true);
  const [portfolioError, setPortfolioError] = useState(false);

  useEffect(() => {
    let active = true;
    setPortfolioLoading(true);
    setPortfolioError(false);
    apiClient.get<PortfolioImage[]>(`/professionals/${professional.id}/portfolio`)
      .then(({ data }) => { if (active) setPortfolio(data); })
      .catch(() => { if (active) setPortfolioError(true); })
      .finally(() => { if (active) setPortfolioLoading(false); });
    return () => { active = false; };
  }, [professional.id]);

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

      {!professional.is_verified && <p className="rounded-lg border border-line bg-muslin/40 px-4 py-3 text-sm text-ink-soft">Verification pending. This professional has registered but has not completed business verification.</p>}
      <ProfessionalServices professionalId={professional.id} />
      {portfolioLoading ? <p role="status">Loading portfolio…</p>
        : portfolioError ? <p role="alert">Portfolio could not be loaded.</p>
        : <ProfessionalPortfolio images={portfolio} />}
      <ProfessionalLocation location={null} />
      <ProfessionalReviews professionalId={professional.id} averageRating={professional.average_rating} reviewCount={professional.review_count} />
    </div>
  );
}
