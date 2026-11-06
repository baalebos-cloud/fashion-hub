export interface PlannedStop {
  key: string;
  kind: "pickup" | "dropoff";
  eta_minutes: number;
  load_after: number;
  order_number: string | null;
  delivery_id: string | null;
}

export interface PlannedRoute {
  id: string;
  stops: PlannedStop[];
  total_minutes: number | null;
  baseline_minutes: number | null;
  minutes_saved: number | null;
  solver: string | null;
  estimated: boolean;
  planned_at: string | null;
}

export function routeSummary(route: PlannedRoute): string {
  const total = route.total_minutes != null ? `About ${route.total_minutes} min in total` : "Route planned";
  const saved = route.minutes_saved && route.minutes_saved > 0 ? `, ${route.minutes_saved} min less than one order at a time` : "";
  return `${total}${saved}.${route.estimated ? " Times are estimates (no live road data)." : ""}`;
}

