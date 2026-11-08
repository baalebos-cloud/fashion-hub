import { Link } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import type { Professional } from "@/types/professional";

/** Shows only what the API returns. Three separate trust signals: on Tailora (always),
 * verified (identity/business checked) and taking new orders. */
export function ProfessionalCard({ professional, detailsPath }: { professional: Professional; detailsPath: string }) {
  const name = professional.business_name ?? "Unnamed studio";
  const reviews = professional.review_count;
  return (
    <Link to={detailsPath} className="block h-full rounded-card focus-visible:outline-2">
      <Card className="flex h-full flex-col gap-3 transition-colors hover:border-indigo">
        <div className="flex items-start gap-3">
          <Avatar name={name} src={professional.shop_photo_url} size="lg" />
          <div className="flex min-w-0 flex-col gap-1">
            <span className="truncate font-semibold text-ink">{name}</span>
            <span className="text-[13px] text-ink-soft">
              <span className="capitalize">{professional.professional_type}</span>
              {professional.years_experience ? ` · ${professional.years_experience} years' experience` : ""}
            </span>
            <div className="flex flex-wrap gap-1.5">
              {professional.is_verified
                ? <Badge tone="success">✓ Verified</Badge>
                : <Badge tone="neutral">Verification pending</Badge>}
              {professional.accepts_new_orders
                ? <Badge tone="info">Taking orders</Badge>
                : <Badge tone="warning">Not taking orders</Badge>}
            </div>
          </div>
        </div>
        {professional.bio && <p className="line-clamp-2 text-sm text-ink-soft">{professional.bio}</p>}
        <p className="mt-auto text-[13px]">
          {reviews > 0
            ? <><span className="font-semibold text-brass-deep">★ {professional.average_rating.toFixed(1)}</span> <span className="text-ink-soft">{reviews} review{reviews === 1 ? "" : "s"}</span></>
            : <span className="text-ink-soft">No reviews yet</span>}
        </p>
      </Card>
    </Link>
  );
}
