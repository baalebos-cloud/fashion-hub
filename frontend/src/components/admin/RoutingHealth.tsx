import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api/client";

interface Health { provider: string; configured: boolean; breaker_open: boolean; note?: string; last_latency_ms?: string; last_failure?: string }

/** One line on the dispatch page: where distances and ETAs come from right now. */
export function RoutingHealth() {
  const [health, setHealth] = useState<Health | null>(null);
  useEffect(() => { apiClient.get<Health>("/admin/routing/health").then((r) => setHealth(r.data)).catch(() => undefined); }, []);
  if (!health) return null;
  const name = health.provider === "google" ? "Google Routes" : health.provider === "osrm" ? "OSRM" : null;
  const text = !health.configured ? "Distances and ETAs are straight-line estimates (no routing provider set up)."
    : health.breaker_open ? `${name} is paused after errors${health.last_failure ? ` (${health.last_failure})` : ""}; showing estimates meanwhile.`
      : `Road routes from ${name}${health.last_latency_ms ? `, last answer in ${health.last_latency_ms} ms` : ""}.`;
  return <p className={`text-xs ${health.breaker_open ? "text-thread" : "text-ink-soft"}`} role="status">{text}</p>;
}
