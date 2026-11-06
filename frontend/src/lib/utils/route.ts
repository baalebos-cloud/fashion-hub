/** A road route from the routing provider, or the labelled straight-line estimate. */
export interface RouteSummary {
  distance_km: number | null;
  duration_minutes: number | null;
  source: string;
  verified: boolean;
  traffic_aware?: boolean;
  computed_at?: string | null;
  polyline?: string | null;
}

/** "14.2 km by road · about 33 min" for real routes; "≈ 12 km (estimate)" otherwise. */
export function describeRoute(route: RouteSummary | null | undefined, fallbackKm?: number | null): string | null {
  if (route && route.verified && route.distance_km != null) {
    const time = route.duration_minutes != null ? ` · about ${route.duration_minutes} min${route.traffic_aware ? " in current traffic" : ""}` : "";
    return `${route.distance_km.toFixed(1)} km by road${time}`;
  }
  const km = route?.distance_km ?? fallbackKm;
  return km != null ? `≈ ${km.toFixed(1)} km (estimate)` : null;
}
