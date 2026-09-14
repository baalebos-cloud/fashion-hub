import { EmptyState } from "@/components/ui/empty-state";

/** Requires GET /favorites (list) on the backend, which isn't in the
 * current scaffold (only POST /favorites to toggle) — see
 * backend/app/api/v1/favorites.py. Wire this page up once that lands. */
export default function Favorites() {
  return <EmptyState title="No favorites yet" description="Save professionals you like to find them again quickly." />;
}
