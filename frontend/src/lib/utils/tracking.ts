/** Words for how fresh a rider's location is. A "last seen" point is never presented as current. */
export function describeFreshness(state: string | null | undefined, ageSeconds?: number | null): { label: string; current: boolean } {
  const ago = ageSeconds == null ? "" : ageSeconds < 60 ? `${ageSeconds}s ago` : `${Math.round(ageSeconds / 60)} min ago`;
  switch (state) {
    case "live": return { label: `Live${ago ? ` · updated ${ago}` : ""}`, current: true };
    case "delayed": return { label: `Delayed · updated ${ago}`, current: true };
    case "last_known": return { label: `Last seen ${ago}. This isn't the rider's current position`, current: false };
    case "permission_denied": return { label: "The rider's location is switched off", current: false };
    case "not_sharing": return { label: "The rider isn't sharing their location", current: false };
    default: return { label: "Location unavailable right now", current: false };
  }
}
