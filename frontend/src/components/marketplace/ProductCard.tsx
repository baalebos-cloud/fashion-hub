import { Link } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { formatCurrency } from "@/lib/formatters/currency";
import type { VendorProduct } from "@/types/product";

export function ProductCard({ product, detailsPath }: { product: VendorProduct; detailsPath: string }) {
  return (
    <Link to={detailsPath}>
      <Card className="flex h-full flex-col gap-2 transition-colors hover:border-brass">
        <div className="aspect-square w-full overflow-hidden rounded-lg bg-muslin">
          {product.primary_image_url && (
            <img src={product.primary_image_url} alt={product.name} className="h-full w-full object-cover" />
          )}
        </div>
        <div className="font-medium text-ink">{product.name}</div>
        {product.vendor_verified === false && (
          <span className="self-start rounded-full bg-warning-wash px-2 py-0.5 text-[11px] font-medium text-warning">
            Vendor verification in progress
          </span>
        )}
        <div className="text-sm text-ink-soft">{formatCurrency(product.base_price, product.currency)}</div>
      </Card>
    </Link>
  );
}
