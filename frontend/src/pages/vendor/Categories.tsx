import { useEffect, useState } from "react";
import { categoriesApi, type Category } from "@/api/categories.api";
import { VendorCategories } from "@/components/marketplace/VendorCategories";

export default function Categories() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    categoriesApi.list().then(setCategories);
  }, []);

  return (
    <div>
      <h1 className="mb-6 font-display text-xl text-ink">Categories</h1>
      <VendorCategories categories={categories} selectedId={selectedId} onSelect={setSelectedId} />
    </div>
  );
}
