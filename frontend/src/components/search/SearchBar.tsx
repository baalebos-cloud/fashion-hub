import { useState } from "react";
import { useSearch } from "@/hooks/use-search";
import { SearchSuggestions } from "./SearchSuggestions";
import { Input } from "@/components/ui/input";

export function SearchBar({ detailsPathFor }: { detailsPathFor: (id: string) => string }) {
  const { results, search } = useSearch();
  const [value, setValue] = useState("");

  return (
    <div className="relative">
      <Input
        value={value}
        onChange={(e) => {
          setValue(e.target.value);
          search(e.target.value);
        }}
        placeholder="Search tailors, designers, styles…"
      />
      <SearchSuggestions results={results} detailsPathFor={detailsPathFor} />
    </div>
  );
}
