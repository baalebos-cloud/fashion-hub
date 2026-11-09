import type { VendorProduct } from "@/types/product";

/** All the vendor's photos, first one first (older products only have the main one). */
export function productImages(product: Pick<VendorProduct, "image_urls" | "primary_image_url">): string[] {
  const all = product.image_urls?.length ? product.image_urls : product.primary_image_url ? [product.primary_image_url] : [];
  return Array.from(new Set(all));
}
