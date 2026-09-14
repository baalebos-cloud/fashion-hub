import { useState } from "react";
import { searchApi } from "@/api/search.api";
import { debounce } from "@/lib/utils/debounce";
import type { Professional } from "@/types/professional";

/** Debounced professional search — the pattern used by SearchBar and
 * ProfessionalSearch. Other search domains (designs, products) follow the
 * same shape via searchApi.designs/vendorProducts. */
export function useSearch() {
  const [results, setResults] = useState<Professional[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  const search = debounce(async (query: string) => {
    if (!query.trim()) {
      setResults([]);
      return;
    }
    setIsSearching(true);
    try {
      setResults(await searchApi.professionals(query));
    } finally {
      setIsSearching(false);
    }
  }, 300);

  return { results, isSearching, search };
}
