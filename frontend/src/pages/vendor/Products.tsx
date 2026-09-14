import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "@/hooks/use-auth";
import { productsApi } from "@/api/products.api";
import { Table, type Column } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { formatCurrency } from "@/lib/formatters/currency";
import { vendorRoutes } from "@/config/routes.config";
import type { VendorProduct } from "@/types/product";

export default function Products() {
  const { user } = useAuth();
  const [products, setProducts] = useState<VendorProduct[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!user) return;
    productsApi.list({ vendorId: user.id }).then((response) => setProducts(response.items)).finally(() => setIsLoading(false));
  }, [user]);

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
      {!isLoading && products.length === 0 ? (
        <EmptyState title="No products yet" description="Add your first product to start selling." />
      ) : (
        <Table columns={columns} rows={products} />
      )}
    </div>
  );
}
