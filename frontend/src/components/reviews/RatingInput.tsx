import { useState } from "react";
import { cn } from "@/lib/utils/cn";

export function RatingInput({ value, onChange }: { value: number; onChange: (value: number) => void }) {
  const [hovered, setHovered] = useState<number | null>(null);
  const display = hovered ?? value;

  return (
    <div className="flex gap-1" role="radiogroup" aria-label="Rating">
      {[1, 2, 3, 4, 5].map((score) => (
        <button
          key={score}
          type="button"
          role="radio"
          aria-checked={value === score}
          aria-label={`${score} star${score > 1 ? "s" : ""}`}
          onMouseEnter={() => setHovered(score)}
          onMouseLeave={() => setHovered(null)}
          onClick={() => onChange(score)}
          className={cn("text-2xl leading-none transition-colors", score <= display ? "text-brass" : "text-line")}
        >
          ★
        </button>
      ))}
    </div>
  );
}
