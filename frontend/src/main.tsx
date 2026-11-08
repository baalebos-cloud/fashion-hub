import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";
import { restoreNativeSession } from "@/lib/native/session";

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Root element (#root) not found in index.html.");
}

// In the phone apps, bring back the saved sign-in before the first render (no-op on the website).
void restoreNativeSession().finally(() => {
  createRoot(rootElement).render(
    <StrictMode>
      <App />
    </StrictMode>
  );
});
