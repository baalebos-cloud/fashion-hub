import { ProductCard } from "./ProductCard";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import type { VendorProduct } from "@/types/product";

export function ProductGrid({ products, isLoading, detailsPathFor }: { products: VendorProduct[]; isLoading?: boolean; detailsPathFor: (id: string) => string }) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-48" />
        ))}
      </div>
    );
  }

  if (products.length === 0) {
    return <EmptyState title="No products found" />;
  }

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
      {products.map((product) => (
        <ProductCard key={product.id} product={product} detailsPath={detailsPathFor(product.id)} />
      ))}
    </div>
  );
}
