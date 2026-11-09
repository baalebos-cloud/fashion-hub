import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import { productsApi } from "@/api/products.api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/error-state";
import { SkeletonRows } from "@/components/ui/skeleton";
import { formatCurrency } from "@/lib/formatters/currency";
import { vendorRoutes } from "@/config/routes.config";
import type { VendorProduct } from "@/types/product";

export default function Products() {
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [products, setProducts] = useState<VendorProduct[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true; setIsLoading(true); setError(null);
    productsApi.mine(page)
      .then((response) => { if (active) { setProducts(response.items); setTotalPages(response.total_pages); } })
      .catch((err) => { if (active) setError(getDisplayErrorMessage(err)); })
      .finally(() => { if (active) setIsLoading(false); });
    return () => { active = false; };
  }, [page, attempt]);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-display text-3xl text-ink">Products</h1>
        <Link to={vendorRoutes.addProduct}><Button>Add product</Button></Link>
      </div>

      {!isLoading && products.some((p) => p.vendor_verified === false) && (
        <p role="status" className="rounded-control bg-warning-wash px-3 py-2 text-sm text-warning">
          Your products are visible in the marketplace, marked "Vendor verification in progress". Tailors and customers
          can order them as soon as your identity and business checks are approved, under Verification.
        </p>
      )}
      {isLoading && <SkeletonRows rows={4} label="Loading products" onRetry={() => setAttempt((n) => n + 1)} />}
      {!isLoading && error && <ErrorState title="Couldn't load your products" description={error} onRetry={() => setAttempt((n) => n + 1)} />}

      {!isLoading && !error && products.length === 0 && (
        <div className="flex flex-col items-center gap-3 rounded-card border border-dashed border-line-strong bg-surface p-8 text-center">
          <p className="font-semibold text-ink">No products yet</p>
          <p className="max-w-sm text-sm text-ink-soft">Add your first fabric or trim. Tailors, designers and customers see it in the marketplace as soon as it's listed.</p>
          <Link to={vendorRoutes.addProduct}><Button>Add your first product</Button></Link>
        </div>
      )}

      {!isLoading && !error && products.length > 0 && (
        <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {products.map((p) => (
            <li key={p.id} className="flex gap-3 rounded-card border border-line bg-surface p-3">
              {p.primary_image_url
                ? <img src={p.primary_image_url} alt="" className="size-20 shrink-0 rounded-control object-cover" />
                : <div aria-hidden className="size-20 shrink-0 rounded-control bg-muslin" />}
              <div className="flex min-w-0 flex-1 flex-col gap-1">
                <span className="truncate font-semibold text-ink">{p.name}</span>
                <span className="font-mono text-sm text-ink">{formatCurrency(p.base_price, p.currency)}</span>
                {(p.image_urls?.length ?? 0) > 1 && <span className="text-xs text-ink-soft">{p.image_urls!.length} photos</span>}
                <div className="mt-auto flex items-center justify-between gap-2">
                  {p.is_active ? <Badge tone="success">Listed</Badge> : <Badge tone="neutral">Hidden</Badge>}
                  <Link to={vendorRoutes.editProduct(p.id)} className="text-sm font-semibold text-indigo">Edit</Link>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}

      {totalPages > 1 && (
        <nav aria-label="Product pages" className="flex items-center gap-4">
          <Button variant="secondary" disabled={isLoading || page === 1} onClick={() => setPage((value) => value - 1)}>Previous</Button>
          <span className="text-sm text-ink-soft">Page {page} of {totalPages}</span>
          <Button variant="secondary" disabled={isLoading || page >= totalPages} onClick={() => setPage((value) => value + 1)}>Next</Button>
        </nav>
      )}
    </div>
  );
}
