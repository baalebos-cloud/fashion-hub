import { Link } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { VerificationBadge } from "@/components/profile/VerificationBadge";
import type { Vendor } from "@/types/vendor";

export function VendorCard({ vendor, detailsPath }: { vendor: Vendor; detailsPath: string }) {
  return (
    <Link to={detailsPath}>
      <Card className="transition-colors hover:border-brass">
        <div className="flex items-center gap-2">
          <div className="font-medium text-ink">{vendor.business_name}</div>
          {vendor.is_verified && <VerificationBadge />}
        </div>
        {vendor.business_description && <p className="mt-1 line-clamp-2 text-sm text-ink-soft">{vendor.business_description}</p>}
        <div className="mt-2 text-sm text-ink-soft">★ {vendor.average_rating.toFixed(1)}</div>
      </Card>
    </Link>
  );
}
