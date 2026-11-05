import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { storefrontsApi, whatsappShareUrl } from "@/api/storefronts.api";
import { Avatar } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { VerificationBadge } from "@/components/profile/VerificationBadge";
import { authRoutes, customerRoutes, publicRoutes } from "@/config/routes.config";
import { useAuth } from "@/hooks/use-auth";
import type { Storefront as StorefrontData } from "@/types/storefront";

const KIND_LABEL = { tailor: "Tailor", designer: "Fashion designer", vendor: "Materials vendor" } as const;

function money(amount: number, currency: string) {
  try {
    return new Intl.NumberFormat("en-NG", { style: "currency", currency, maximumFractionDigits: 0 }).format(amount);
  } catch {
    return `${currency} ${amount.toLocaleString()}`;
  }
}

function Stars({ value }: { value: number }) {
  // Round down so the stars never overstate a rating (4.6 shows four; the number shows 4.6).
  const rounded = Math.max(0, Math.min(5, Math.floor(value)));
  return (
    <span aria-label={`${value.toFixed(1)} out of 5`} className="tracking-tight text-brass">
      {"★★★★★".slice(0, rounded)}
      <span className="text-line">{"★★★★★".slice(rounded)}</span>
    </span>
  );
}

export default function Storefront() {
  const { handle = "" } = useParams<{ handle: string }>();
  const navigate = useNavigate();
  const { isAuthenticated, user } = useAuth();
  const [shop, setShop] = useState<StorefrontData | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "missing">("loading");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    let active = true;
    setState("loading");
    storefrontsApi.getPublic(handle)
      .then((data) => { if (active) { setShop(data); setState("ready"); } })
      .catch(() => { if (active) setState("missing"); });
    return () => { active = false; };
  }, [handle]);

  useEffect(() => {
    if (shop) document.title = `${shop.display_name} · Tailora`;
  }, [shop]);

  if (state === "loading") {
    return (
      <div className="mx-auto max-w-5xl space-y-4 px-4 py-10" aria-busy="true">
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (state === "missing" || !shop) {
    return (
      <div className="mx-auto max-w-lg px-4 py-20 text-center">
        <h1 className="font-display text-2xl text-ink">This shop isn't available</h1>
        <p className="mt-2 text-sm text-ink-soft">
          The link may be mistyped, or the shop is still being verified by Tailora.
        </p>
        <div className="mt-6 flex justify-center gap-3">
          <Link to={publicRoutes.findTailor}><Button>Find a tailor</Button></Link>
          <Link to={publicRoutes.vendorMarketplace}><Button variant="secondary">Browse materials</Button></Link>
        </div>
      </div>
    );
  }

  const isProfessional = shop.kind !== "vendor";

  function startOrder() {
    if (!shop?.professional_id) return;
    const target = customerRoutes.createOrder(shop.professional_id);
    if (!isAuthenticated) navigate(authRoutes.login, { state: { from: { pathname: target } } });
    else navigate(target);
  }

  async function share() {
    if (!shop) return;
    const data = { title: shop.display_name, text: `Shop with ${shop.display_name} on Tailora`, url: shop.share_url };
    try {
      if (navigator.share) { await navigator.share(data); return; }
      await navigator.clipboard.writeText(shop.share_url);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch { /* Share sheet dismissed or clipboard blocked; nothing to do. */ }
  }

  const canOrder = isProfessional && shop.accepts_new_orders && (!isAuthenticated || user?.role === "customer");

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:py-12">
      <Card className="overflow-hidden p-0">
        <div className="h-24 bg-gradient-to-r from-ink via-ink/90 to-brass-deep sm:h-32" aria-hidden="true" />
        <div className="px-5 pb-6 sm:px-8">
          {/* Only the photo overlaps the banner; the name always sits on the light card for contrast. */}
          <Avatar name={shop.display_name} src={shop.profile_photo_url} size="lg"
            className="-mt-10 h-20 w-20 border-4 border-paper text-xl sm:-mt-12 sm:h-24 sm:w-24" />
          <div className="mt-3 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="font-display text-2xl text-ink sm:text-3xl">{shop.display_name}</h1>
              {shop.is_verified && <VerificationBadge />}
            </div>
            <p className="mt-1 text-sm text-ink-soft">
              {KIND_LABEL[shop.kind]}
              {shop.area && <> · {shop.area}</>}
              {shop.member_since && <> · On Tailora since {shop.member_since}</>}
            </p>
          </div>
          <div className="grid grid-cols-2 gap-2 sm:flex sm:shrink-0">
            {isProfessional && (
              <Button onClick={startOrder} disabled={!canOrder} className="col-span-2 sm:col-span-1">
                {shop.accepts_new_orders ? "Order from this shop" : "Not taking orders"}
              </Button>
            )}
            <Button variant="secondary" onClick={() => void share()}>{copied ? "Link copied" : "Share"}</Button>
            <a href={whatsappShareUrl(shop.display_name, shop.share_url)} target="_blank" rel="noopener noreferrer"
              className="inline-flex items-center justify-center rounded-lg border border-line px-4 py-2.5 text-sm font-medium text-ink transition-colors hover:border-brass">
              WhatsApp
            </a>
          </div>
          </div>
        </div>
        <dl className="grid grid-cols-3 border-t border-line text-center">
          <div className="p-4">
            <dt className="text-xs text-ink-soft">Rating</dt>
            <dd className="mt-1 text-sm text-ink"><Stars value={shop.average_rating} /> {shop.average_rating.toFixed(1)}</dd>
          </div>
          <div className="border-x border-line p-4">
            <dt className="text-xs text-ink-soft">Reviews</dt>
            <dd className="mt-1 text-sm font-medium text-ink">{shop.review_count}</dd>
          </div>
          <div className="p-4">
            <dt className="text-xs text-ink-soft">{isProfessional ? "Experience" : "Catalogue"}</dt>
            <dd className="mt-1 text-sm font-medium text-ink">
              {isProfessional
                ? (shop.years_experience ? `${shop.years_experience} yrs` : "New")
                : `${shop.products.length} items`}
            </dd>
          </div>
        </dl>
      </Card>

      {shop.bio && <p className="mt-6 max-w-3xl whitespace-pre-line text-sm leading-relaxed text-ink">{shop.bio}</p>}
      {isAuthenticated && user?.role !== "customer" && isProfessional && (
        <p className="mt-4 text-xs text-ink-soft">Sign in with a customer account to place an order.</p>
      )}

      {shop.designs.length > 0 && (
        <section className="mt-10" aria-labelledby="catalogue-heading">
          <h2 id="catalogue-heading" className="font-display text-lg text-ink">Catalogue</h2>
          <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {shop.designs.map((design) => (
              <Card key={design.id} className="flex flex-col gap-2">
                <h3 className="font-medium text-ink">{design.title}</h3>
                <p className="text-sm text-ink-soft">
                  From <span className="font-medium text-ink">{money(design.base_price, design.currency)}</span>
                  {design.estimated_turnaround_days ? ` · about ${design.estimated_turnaround_days} days` : ""}
                </p>
              </Card>
            ))}
          </div>
        </section>
      )}

      {shop.products.length > 0 && (
        <section className="mt-10" aria-labelledby="products-heading">
          <h2 id="products-heading" className="font-display text-lg text-ink">Materials</h2>
          <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
            {shop.products.map((product) => (
              <Link key={product.id} to={publicRoutes.productDetails(product.id)}>
                <Card className="h-full p-0 transition-colors hover:border-brass">
                  {product.image_url
                    ? <img src={product.image_url} alt={product.name} loading="lazy" className="aspect-square w-full rounded-t-card object-cover" />
                    : <div className="aspect-square w-full rounded-t-card bg-muslin" aria-hidden="true" />}
                  <div className="p-3">
                    <h3 className="line-clamp-1 text-sm font-medium text-ink">{product.name}</h3>
                    <p className="text-xs text-ink-soft">{money(product.base_price, product.currency)} / {product.unit_of_measure}</p>
                  </div>
                </Card>
              </Link>
            ))}
          </div>
        </section>
      )}

      {shop.portfolio.length > 0 && (
        <section className="mt-10" aria-labelledby="portfolio-heading">
          <h2 id="portfolio-heading" className="font-display text-lg text-ink">Past work</h2>
          <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {shop.portfolio.map((photo) => (
              <img key={photo.id} src={photo.image_url} alt={`Work by ${shop.display_name}`} loading="lazy"
                className="aspect-[4/5] w-full rounded-card object-cover" />
            ))}
          </div>
        </section>
      )}

      {shop.designs.length + shop.products.length + shop.portfolio.length === 0 && (
        <p className="mt-10 rounded-card border border-dashed border-line p-6 text-center text-sm text-ink-soft">
          This shop hasn't published its catalogue yet.
        </p>
      )}

      <section className="mt-10" aria-labelledby="reviews-heading">
        <h2 id="reviews-heading" className="font-display text-lg text-ink">Reviews</h2>
        {shop.reviews.length === 0
          ? <p className="mt-3 text-sm text-ink-soft">No reviews yet.</p>
          : (
            <ul className="mt-4 space-y-3">
              {shop.reviews.map((review) => (
                <li key={review.id}>
                  <Card className="p-4">
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-medium text-ink">{review.reviewer_first_name}</span>
                      {review.score !== null && <Stars value={review.score} />}
                    </div>
                    {review.comment && <p className="mt-2 text-sm text-ink-soft">{review.comment}</p>}
                  </Card>
                </li>
              ))}
            </ul>
          )}
      </section>
    </div>
  );
}
