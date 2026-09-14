import { VerificationBadge } from "@/components/profile/VerificationBadge";
import { ProductGrid } from "./ProductGrid";
import type { Vendor } from "@/types/vendor";
import type { VendorProduct } from "@/types/product";

export function VendorProfile({ vendor, products, isLoading, productDetailsPathFor }: { vendor: Vendor; products: VendorProduct[]; isLoading?: boolean; productDetailsPathFor: (id: string) => string }) {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <div className="flex items-center gap-2">
          <h1 className="font-display text-xl text-ink">{vendor.business_name}</h1>
          {vendor.is_verified && <VerificationBadge />}
        </div>
        {vendor.business_description && <p className="mt-1 text-sm text-ink-soft">{vendor.business_description}</p>}
      </div>
      <ProductGrid products={products} isLoading={isLoading} detailsPathFor={productDetailsPathFor} />
    </div>
  );
}
