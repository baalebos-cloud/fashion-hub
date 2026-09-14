import { useEffect, useState } from "react";
import { productsApi } from "@/api/products.api";
import { categoriesApi, type Category } from "@/api/categories.api";
import { ProductGrid } from "@/components/marketplace/ProductGrid";
import { VendorCategories } from "@/components/marketplace/VendorCategories";
import { professionalRoutes } from "@/config/routes.config";
import type { VendorProduct } from "@/types/product";

export default function VendorMarketplace() {
  const [products, setProducts] = useState<VendorProduct[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [selectedCategoryId, setSelectedCategoryId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    categoriesApi.list().then(setCategories);
  }, []);

  useEffect(() => {
    setIsLoading(true);
    productsApi
      .list({ categoryId: selectedCategoryId ?? undefined })
      .then((response) => setProducts(response.items))
      .finally(() => setIsLoading(false));
  }, [selectedCategoryId]);

  return (
    <div className="flex flex-col gap-6">
      <h1 className="font-display text-xl text-ink">Vendor marketplace</h1>
      <VendorCategories categories={categories} selectedId={selectedCategoryId} onSelect={setSelectedCategoryId} />
      <ProductGrid products={products} isLoading={isLoading} detailsPathFor={professionalRoutes.vendorProductDetails} />
    </div>
  );
}
