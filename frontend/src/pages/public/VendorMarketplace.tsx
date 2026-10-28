import { useEffect, useState } from "react";
import { productsApi } from "@/api/products.api";
import { categoriesApi, type Category } from "@/api/categories.api";
import { ProductGrid } from "@/components/marketplace/ProductGrid";
import { VendorCategories } from "@/components/marketplace/VendorCategories";
import type { VendorProduct } from "@/types/product";

export default function VendorMarketplace() {
  const [products, setProducts] = useState<VendorProduct[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [selectedCategoryId, setSelectedCategoryId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [productsError, setProductsError] = useState(false);
  const [categoriesError, setCategoriesError] = useState(false);
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    let active = true;
    setCategoriesError(false);
    categoriesApi.listVendor()
      .then((result) => { if (active) setCategories(result); })
      .catch(() => { if (active) setCategoriesError(true); });
    return () => { active = false; };
  }, [retry]);

  useEffect(() => {
    let active = true;
    setProductsError(false);
    setIsLoading(true);
    productsApi.list({ categoryId: selectedCategoryId ?? undefined })
      .then((response) => { if (active) setProducts(response.items); })
      .catch(() => { if (active) setProductsError(true); })
      .finally(() => { if (active) setIsLoading(false); });
    return () => { active = false; };
  }, [selectedCategoryId, retry]);

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <h1 className="mb-6 font-display text-2xl text-ink">Vendor marketplace</h1>
      <div className="mb-6">
        <VendorCategories categories={categories} selectedId={selectedCategoryId} onSelect={setSelectedCategoryId} />
      </div>
      {(productsError || categoriesError) && (
        <div role="alert" className="mb-5 flex flex-wrap items-center gap-3 text-sm text-thread">
          <span>Some marketplace information couldn't be loaded. Please try again.</span>
          <button type="button" onClick={() => setRetry((value) => value + 1)}
            className="rounded-lg border border-line px-3 py-1.5 text-ink hover:bg-muslin">
            Retry
          </button>
        </div>
      )}
      {!productsError && (
        <ProductGrid products={products} isLoading={isLoading} detailsPathFor={(id) => "/products/" + id} />
      )}
    </div>
  );
}
