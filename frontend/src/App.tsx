import { useEffect } from "react";
import { RouterProvider } from "react-router-dom";
import { router } from "@/router";
import { AIAssistant } from "@/components/ai/AIAssistant";
import { ErrorBoundary } from "@/components/common/ErrorBoundary";
import { useAuth } from "@/hooks/use-auth";
import { useAuthStore } from "@/store/auth.store";

/**
 * Application shell.
 *
 * The AI assistant is mounted once, here, alongside the router rather than
 * inside any single page — it must be available throughout the
 * application, not confined to one screen. It renders through a portal
 * (see AIAssistant.tsx), so its fixed position is unaffected by any
 * individual page's layout.
 */
export default function App() {
  const { isAuthenticated, user } = useAuth();
  const initialize = useAuthStore((s) => s.initialize);

  // Runs once: turns a persisted token (see lib/auth/token.ts) into a
  // hydrated user before AuthGuard decides whether to render protected
  // routes or redirect to /login.
  useEffect(() => {
    initialize();
  }, [initialize]);

  return (
    <ErrorBoundary>
      <RouterProvider router={router} />
      {isAuthenticated && <AIAssistant role={user?.role ?? "customer"} />}
    </ErrorBoundary>
  );
}
