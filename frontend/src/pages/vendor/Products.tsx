import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import { productsApi } from "@/api/products.api";
import { Table, type Column } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { formatCurrency } from "@/lib/formatters/currency";
import { vendorRoutes } from "@/config/routes.config";
import type { VendorProduct } from "@/types/product";

export default function Products() {
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [products, setProducts] = useState<VendorProduct[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let active = true; setIsLoading(true); setError(null);
    productsApi.mine(page).then((response) => { if (active) { setProducts(response.items); setTotalPages(response.total_pages); } }).catch((err) => { if (active) setError(getDisplayErrorMessage(err)); }).finally(() => { if (active) setIsLoading(false); });
    return () => { active = false; };
  }, [page]);

  const columns: Column<VendorProduct>[] = [
    { header: "Name", render: (p) => p.name },
    { header: "Price", render: (p) => formatCurrency(p.base_price, p.currency) },
    { header: "Status", render: (p) => (p.is_active ? "Active" : "Inactive") },
    { header: "", render: (p) => <Link to={vendorRoutes.editProduct(p.id)} className="text-brass-deep hover:underline">Edit</Link> },
  ];

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="font-display text-xl text-ink">Products</h1>
        <Link to={vendorRoutes.addProduct}><Button>Add product</Button></Link>
      </div>
      {error && <p role="alert">{error}</p>}
      {isLoading && <p role="status">Loading products…</p>}
      {!isLoading && products.length === 0 ? (
        <EmptyState title="No products yet" description="Add your first product to start selling." />
      ) : (
        <Table columns={columns} rows={products} />
      )}
      <div className="flex gap-4"><Button disabled={isLoading || page === 1} onClick={() => setPage((value) => value - 1)}>Previous</Button><span>Page {page}</span><Button disabled={isLoading || page >= totalPages} onClick={() => setPage((value) => value + 1)}>Next</Button></div>
    </div>
  );
}
