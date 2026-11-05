import { QueryClient } from "@tanstack/react-query";

/** Single app-wide cache, exported so account changes can wipe it (see account-isolation.ts). */
export const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 1000 * 60 * 5, retry: 1, refetchOnWindowFocus: false } },
});
