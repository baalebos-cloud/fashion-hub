import { useEffect } from "react";
import { router } from "@/router";
import { useAuthStore } from "@/store/auth.store";
import { initNativeShell } from "@/lib/native/app-shell";
import { registerForPush } from "@/lib/native/push";
import { isNativeApp } from "@/lib/native/platform";

const navigate = (path: string) => { void router.navigate(path); };

/** Wires the phone-app features once; renders nothing, and does nothing on the website. */
export function NativeBridge() {
  const signedIn = useAuthStore((s) => s.isAuthenticated);
  useEffect(() => { void initNativeShell(navigate); }, []);
  useEffect(() => {
    if (signedIn && isNativeApp()) void registerForPush(navigate);
  }, [signedIn]);
  return null;
}
