import { Link } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Avatar } from "@/components/ui/avatar";
import { VerificationBadge } from "@/components/profile/VerificationBadge";
import type { Professional } from "@/types/professional";

export function ProfessionalCard({ professional, detailsPath }: { professional: Professional; detailsPath: string }) {
  return (
    <Link to={detailsPath}>
      <Card className="flex h-full flex-col gap-3 transition-colors hover:border-brass">
        <div className="flex items-center gap-3">
          <Avatar name={professional.business_name ?? "Professional"} src={professional.shop_photo_url} />
          <div className="min-w-0">
            <div className="flex items-center gap-1.5">
              <div className="truncate font-medium text-ink">{professional.business_name ?? "Unnamed studio"}</div>
              {professional.is_verified && <VerificationBadge />}
            </div>
            <div className="text-xs text-ink-soft capitalize">{professional.professional_type}</div>
          </div>
        </div>
        {professional.bio && <p className="line-clamp-2 text-sm text-ink-soft">{professional.bio}</p>}
        <div className="mt-auto flex items-center justify-between text-sm">
          <span className="text-ink-soft">★ {professional.average_rating.toFixed(1)} ({professional.review_count})</span>
          {!professional.accepts_new_orders && <span className="text-xs text-thread">Not accepting orders</span>}
        </div>
      </Card>
    </Link>
  );
}
