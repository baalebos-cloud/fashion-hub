import { Link } from "react-router-dom";
import type { Professional } from "@/types/professional";

export function SearchSuggestions({ results, detailsPathFor }: { results: Professional[]; detailsPathFor: (id: string) => string }) {
  if (results.length === 0) return null;

  return (
    <div className="absolute z-40 mt-1 w-full rounded-lg border border-line bg-paper shadow-lg">
      {results.slice(0, 6).map((result) => (
        <Link key={result.id} to={detailsPathFor(result.id)} className="block px-3 py-2 text-sm hover:bg-muslin">
          {result.business_name ?? "Unnamed studio"}
        </Link>
      ))}
    </div>
  );
}
