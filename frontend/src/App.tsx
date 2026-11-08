import { useEffect, useState } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "react-router-dom";
import { AppCalls } from "@/components/calls/AppCalls";
import { NativeBridge } from "@/components/native/NativeBridge";
import { router } from "@/router";
import { AIAssistant } from "@/components/ai/AIAssistant";
import { AIPublicTeaser } from "@/components/ai/AIPublicTeaser";
import { ErrorBoundary } from "@/components/common/ErrorBoundary";
import { ToastProvider } from "@/components/ui/toast";
import { useAuth } from "@/hooks/use-auth";
import { useAuthStore } from "@/store/auth.store";
import { authRoutes } from "@/config/routes.config";
import { queryClient } from "@/lib/query-client";
import "@/lib/auth/account-isolation";


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
        <AppCalls />
        <NativeBridge />
        <GlobalAssistant />
      </ToastProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}
