import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { favoritesApi, type FavoriteItem } from "@/api/favorites.api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Avatar } from "@/components/ui/avatar";
import { EmptyState } from "@/components/ui/empty-state";
import { customerRoutes } from "@/config/routes.config";
import { formatCurrency } from "@/lib/formatters/currency";
import { getDisplayErrorMessage } from "@/lib/utils/errors";

const KIND: Record<FavoriteItem["favorite_type"], string> = { professional: "Tailor or designer", design: "Design", vendor_product: "Fabric" };

function linkFor(item: FavoriteItem): string | null {
  if (!item.available) return null;
  if (item.favorite_type === "vendor_product") return customerRoutes.materialDetails(item.favorite_ref_id);
  return item.professional_id ? customerRoutes.professionalDetails(item.professional_id) : null;
}

/** Tailors, designs and fabrics the customer saved. */
export default function Favorites() {
  const [items, setItems] = useState<FavoriteItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [removing, setRemoving] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    favoritesApi.list()
      .then((rows) => { if (active) setItems(rows); })
      .catch((err) => { if (active) setError(getDisplayErrorMessage(err, "Couldn't load your favorites.")); });
    return () => { active = false; };
  }, []);

  async function remove(item: FavoriteItem) {
    setRemoving(item.id);
    try {
      await favoritesApi.toggle(item.favorite_type, item.favorite_ref_id);
      setItems((rows) => (rows ?? []).filter((r) => r.id !== item.id));
    } catch (err) {
      setError(getDisplayErrorMessage(err, "Couldn't remove it. Try again."));
    } finally {
      setRemoving(null);
    }
  }

  if (error && !items) return <p role="alert" className="text-thread">{error}</p>;
  if (!items) return <p role="status">Loading your favorites…</p>;
  if (items.length === 0) {
    return <EmptyState title="No favorites yet" description="Tap the heart on a tailor, design or fabric to find it again quickly." />;
  }

  return (
    <div className="flex flex-col gap-4">
      <h1 className="font-display text-xl text-ink">Favorites</h1>
      {error && <p role="alert" className="text-sm text-thread">{error}</p>}
      <div className="grid gap-3 sm:grid-cols-2">
        {items.map((item) => {
          const to = linkFor(item);
          const body = (
            <div className="flex items-center gap-3">
              <Avatar name={item.title ?? "?"} src={item.image_url} size="lg" />
              <div className="flex min-w-0 flex-col">
                <span className="text-xs text-ink-soft">{KIND[item.favorite_type]}</span>
                <span className="truncate font-semibold text-ink">{item.title ?? "No longer listed"}</span>
                {item.subtitle && <span className="truncate text-sm text-ink-soft">{item.subtitle}</span>}
                {item.price != null && <span className="text-sm text-ink">{formatCurrency(item.price, item.currency ?? "NGN")}</span>}
                {!item.available && <span className="text-xs text-thread">Not available right now</span>}
              </div>
            </div>
          );
          return (
            <Card key={item.id} className="flex items-center justify-between gap-3">
              {to ? <Link to={to} className="min-w-0 flex-1">{body}</Link> : <div className="min-w-0 flex-1 opacity-70">{body}</div>}
              <Button variant="ghost" size="sm" isLoading={removing === item.id} onClick={() => void remove(item)}
                aria-label={`Remove ${item.title ?? "this item"} from favorites`}>Remove</Button>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
