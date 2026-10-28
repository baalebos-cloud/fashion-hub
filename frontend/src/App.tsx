import { useEffect, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "react-router-dom";
import { router } from "@/router";
import { AIAssistant } from "@/components/ai/AIAssistant";
import { AIPublicTeaser } from "@/components/ai/AIPublicTeaser";
import { ErrorBoundary } from "@/components/common/ErrorBoundary";
import { ToastProvider } from "@/components/ui/toast";
import { useAuth } from "@/hooks/use-auth";
import { useAuthStore } from "@/store/auth.store";
import { authRoutes } from "@/config/routes.config";

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 1000 * 60 * 5, retry: 1, refetchOnWindowFocus: false } },
});

const AUTH_PATHS: string[] = Object.values(authRoutes);

function GlobalAssistant() {
  const { isAuthenticated, isInitializing, user } = useAuth();
  const [pathname, setPathname] = useState(router.state.location.pathname);

  useEffect(() => router.subscribe((state) => setPathname(state.location.pathname)), []);

  if (isInitializing) return null;
  if (isAuthenticated) return <AIAssistant role={user?.role ?? "customer"} />;
  if (AUTH_PATHS.includes(pathname)) return null;
  return <AIPublicTeaser />;
}

export default function App() {
  const initialize = useAuthStore((s) => s.initialize);

  useEffect(() => {
    initialize();
  }, [initialize]);

  return (
    <ErrorBoundary>
      {/* All routed pages, dialogs and portal-mounted assistant share this provider. */}
      <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <RouterProvider router={router} />
        <GlobalAssistant />
      </ToastProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}
