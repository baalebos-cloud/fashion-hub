import { env } from "./environment";

/** Application-wide, non-secret constants. */
export const appConfig = {
  name: env.appName,
  defaultLocale: "en-US",
  defaultCurrency: "NGN",
  defaultTimezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
  supportEmail: "support@fashionhub.example",
  pagination: {
    defaultPageSize: 20,
    maxPageSize: 100,
  },
} as const;
