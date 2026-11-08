import { useEffect } from "react";
import { useAuthStore } from "@/store/auth.store";
import { useCallStore } from "@/store/call.store";
import { CallCenter } from "./CallCenter";

/**
 * Calls live above the pages, so moving around Tailora never drops a call.
 * Signed-in order parties only (admins never take part in order calls); when the session
 * ends for any reason, any call is hung up and the microphone released.
 */
export function AppCalls() {
  const user = useAuthStore((s) => s.user);
  const signedIn = useAuthStore((s) => s.isAuthenticated) && user != null;
  const enabled = signedIn && user?.role !== "admin";
  useEffect(() => {
    if (!enabled) void useCallStore.getState().reset();
  }, [enabled]);
  useEffect(() => () => { void useCallStore.getState().reset(); }, []);
  if (!enabled) return null;
  return <CallCenter />;
}
