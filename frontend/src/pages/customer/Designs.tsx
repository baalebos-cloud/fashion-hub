import { useState } from "react";
import { useAuth } from "@/hooks/use-auth";
import { EmptyState } from "@/components/ui/empty-state";

/** Customer-side "designs" is the set of designs they've favorited while
 * browsing professionals (see components/designs/DesignCard, used with an
 * onSelect handler that calls api/favorites.api.ts::toggle on a
 * professional's profile page). Listing favorited designs here requires a
 * `GET /favorites?type=design` endpoint, which doesn't exist yet in the
 * backend scaffold (only POST /favorites to toggle) — wire this up once
 * that lands. */
export default function Designs() {
  const { user } = useAuth();
  const [hasFavorites] = useState(false);

  if (!user) return null;

  if (!hasFavorites) {
    return <EmptyState title="No saved designs yet" description="Favorite a design on a professional's profile to see it here." />;
  }

  return null;
}
