import { useEffect, useState } from "react";
import { useAuth } from "@/hooks/use-auth";
import { productsApi } from "@/api/products.api";
import { Table, type Column } from "@/components/ui/table";
import { InventoryBadge } from "@/components/marketplace/InventoryBadge";
import type { VendorProduct } from "@/types/product";

export default function Inventory() {
  const { user } = useAuth();
  const [products, setProducts] = useState<VendorProduct[]>([]);

  useEffect(() => {
    if (user) productsApi.list({ vendorId: user.id }).then((r) => setProducts(r.items));
  }, [user]);

  const columns: Column<VendorProduct>[] = [
    { header: "Product", render: (p) => p.name },
    { header: "Stock", render: () => <InventoryBadge quantityAvailable={0} /> },
  ];

  return (
    <div>
      <h1 className="mb-6 font-display text-xl text-ink">Inventory</h1>
      <Table columns={columns} rows={products} />
    </div>
  );
}
