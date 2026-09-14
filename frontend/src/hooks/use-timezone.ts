import { useAuth } from "./use-auth";
import { appConfig } from "@/config/app.config";

/**
 * The single source of truth for "what timezone should we display
 * timestamps in," per the requirement that timestamp handling is global,
 * not decided ad-hoc by each component.
 *
 * Resolution order:
 *   1. The signed-in user's saved `timezone` (backend/app/models/user.py)
 *   2. The browser's detected timezone (appConfig.defaultTimezone)
 *   3. "UTC" as an absolute fallback
 *
 * Every component that renders a timestamp — DateTimeDisplay, and any
 * bespoke date rendering elsewhere — must go through this hook rather
 * than assuming a timezone, so a change to how the fallback is chosen
 * only has to happen in one place. The backend always stores and sends
 * UTC (see backend/docs/database.md); this hook is what turns that into
 * "3:45 PM" instead of a raw ISO string.
 */
export function useTimezone(): string {
  const { user } = useAuth();
  return user?.timezone || appConfig.defaultTimezone || "UTC";
}
