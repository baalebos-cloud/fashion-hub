import type { User } from "@/types/user";

export interface NameParts {
  first: string;
  middle: string;
  last: string;
}

/** The person's name in three parts. Older accounts only have full_name: first word, last word,
 * and anything between as the middle name (the server does the same, see backend/app/core/names.py). */
export function nameParts(user: Pick<User, "full_name" | "first_name" | "middle_name" | "last_name"> | null | undefined): NameParts {
  if (!user) return { first: "", middle: "", last: "" };
  if (user.first_name || user.last_name) {
    return { first: user.first_name ?? "", middle: user.middle_name ?? "", last: user.last_name ?? "" };
  }
  const words = (user.full_name ?? "").split(/\s+/).filter(Boolean);
  if (words.length < 2) return { first: words[0] ?? "", middle: "", last: "" };
  return { first: words[0], middle: words.slice(1, -1).join(" "), last: words[words.length - 1] };
}

export function composeName(parts: NameParts): string {
  return [parts.first, parts.middle, parts.last].map((p) => p.trim().replace(/\s+/g, " ")).filter(Boolean).join(" ");
}

// Letters in any alphabet (with accents and tone marks), joined by spaces, hyphens, apostrophes or full stops.
const NAME_PART = /^[\p{L}\p{M}]+(?:[ .'’-]+[\p{L}\p{M}]+)*\.?$/u;

export type NameErrors = Partial<Record<keyof NameParts, string>>;

export function validateNameParts(parts: NameParts): NameErrors {
  const errors: NameErrors = {};
  const check = (key: keyof NameParts, label: string, required: boolean) => {
    const value = parts[key].trim().replace(/\s+/g, " ");
    if (!value) {
      if (required) errors[key] = `Enter your ${label}.`;
      return;
    }
    if (value.length > 80) errors[key] = `Your ${label} is too long.`;
    else if (!NAME_PART.test(value)) errors[key] = `Use letters only (spaces, hyphens and apostrophes are fine).`;
  };
  check("first", "first name", true);
  check("middle", "middle name", false);
  check("last", "surname", true);
  return errors;
}
