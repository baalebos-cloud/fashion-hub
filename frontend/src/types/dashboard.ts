/** Loosely-typed summary card data — shape varies per role, so callers
 * narrow via the `kind` discriminant rather than one rigid interface. */
export interface DashboardSummaryCard {
  kind: string;
  label: string;
  value: string | number;
  trend?: { direction: "up" | "down" | "flat"; label: string };
}
