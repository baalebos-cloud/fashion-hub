import { SeamAssistantProvider, SeamAssistantWidget } from "./components/ai-assistant";
// import your router, e.g.:
// import { RouterProvider } from "react-router-dom";
// import { router } from "./router";

/**
 * Mount SeamAssistantProvider + SeamAssistantWidget ONCE, at the top of
 * the app shell — outside/around your router — so the assistant persists
 * across every route instead of living on one page. Every screen in the
 * app can still open it via useSeamAssistant()/<AskSeamLink> without
 * re-mounting anything.
 */
export default function App({ currentUser }) {
  return (
    <SeamAssistantProvider
      role={currentUser?.role ?? "customer"}
      userName={currentUser?.fullName}
      apiBaseUrl={import.meta.env.VITE_API_BASE_URL ?? "/api/v1"}
      getAuthToken={async () => localStorage.getItem("access_token")}
    >
      {/* <RouterProvider router={router} /> */}
      <div id="app-shell">{/* ...the rest of your application... */}</div>

      {/* Renders via a portal into document.body, so its fixed position
          is never affected by the app's own layout/overflow/z-index. */}
      <SeamAssistantWidget />
    </SeamAssistantProvider>
  );
}
