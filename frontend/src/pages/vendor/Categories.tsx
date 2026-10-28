import { useEffect, useState } from "react";
import { categoriesApi, type Category } from "@/api/categories.api";
import { VendorCategories } from "@/components/marketplace/VendorCategories";

export default function Categories() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [error, setError] = useState(false);
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    let active = true;
    setError(false);
    categoriesApi.listVendor()
      .then((rows) => { if (active) setCategories(rows); })
      .catch(() => { if (active) setError(true); });
    return () => { active = false; };
  }, [retry]);

  return (
    <div>
      <h1 className="mb-6 font-display text-xl text-ink">Categories</h1>
      {error && <p role="alert" className="mb-4 text-sm text-thread">
        Could not load material categories.{" "}
        <button type="button" className="underline" onClick={() => setRetry((value) => value + 1)}>Retry</button>
      </p>}
      <VendorCategories categories={categories} selectedId={selectedId} onSelect={setSelectedId} />
    </div>
  );
}
