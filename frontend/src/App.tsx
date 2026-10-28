import { useEffect, useState } from "react";
import { RouterProvider } from "react-router-dom";
import { router } from "@/router";
import { AIAssistant } from "@/components/ai/AIAssistant";
import { AIPublicTeaser } from "@/components/ai/AIPublicTeaser";
import { ErrorBoundary } from "@/components/common/ErrorBoundary";
import { ToastProvider } from "@/components/ui/toast";
import { useAuth } from "@/hooks/use-auth";
import { useAuthStore } from "@/store/auth.store";
import { authRoutes } from "@/config/routes.config";

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
      <ToastProvider>
        <RouterProvider router={router} />
        <GlobalAssistant />
      </ToastProvider>
    </ErrorBoundary>
  );
}
