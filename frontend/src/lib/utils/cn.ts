import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** Standard Tailwind class-merging helper — combines conditional classes
 * (clsx) with conflict resolution (tailwind-merge), so e.g. a consumer
 * overriding `className="p-4"` on a Button correctly wins over the
 * component's own default padding instead of both classes fighting. */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
