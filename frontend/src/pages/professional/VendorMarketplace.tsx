import { useEffect, useState } from "react";
import { productsApi } from "@/api/products.api";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import { Button } from "@/components/ui/button";
import { ProductGrid } from "@/components/marketplace/ProductGrid";
import { professionalRoutes } from "@/config/routes.config";
import type { VendorProduct } from "@/types/product";

export default function VendorMarketplace() {
  const [products, setProducts] = useState<VendorProduct[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setIsLoading(true); setError(null);
    productsApi.list({ page }).then((response) => { if (active) { setProducts(response.items); setTotalPages(response.total_pages); } })
      .catch((err) => { if (active) setError(getDisplayErrorMessage(err)); })
      .finally(() => { if (active) setIsLoading(false); });
    return () => { active = false; };
  }, [page]);

  return (
    <div className="flex flex-col gap-6">
      <h1 className="font-display text-xl text-ink">Vendor marketplace</h1>
      {error && <p role="alert">{error}</p>}
      <ProductGrid products={products} isLoading={isLoading} detailsPathFor={professionalRoutes.vendorProductDetails} />
      <div className="flex gap-4"><Button disabled={isLoading || page === 1} onClick={() => setPage((value) => value - 1)}>Previous</Button><span>Page {page}</span><Button disabled={isLoading || page >= totalPages} onClick={() => setPage((value) => value + 1)}>Next</Button></div>
    </div>
  );
}
