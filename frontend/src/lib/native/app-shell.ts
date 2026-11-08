/**
 * Phone-app behaviour that a website doesn't need: status bar colours, hiding the launch
 * screen, the Android back button, and opening tailora:// links (and push taps) on the
 * right page. Does nothing on the website.
 */
import { isNativeApp, nativePlatform } from "./platform";

type Navigate = (path: string) => void;

/** Only paths inside the app (e.g. "/app/customer/orders/123") are followed. */
export function internalPath(url: string): string | null {
  try {
    const parsed = new URL(url);
    // tailora://app/customer/orders/1 -> host "app" + path; https://<site>/app/... -> path
    const path = parsed.protocol === "tailora:" ? `/${parsed.host}${parsed.pathname}` : parsed.pathname;
    const full = `${path}${parsed.search}`.replace(/\/{2,}/g, "/");
    return full.startsWith("/") && !full.startsWith("//") ? full : null;
  } catch {
    return url.startsWith("/") && !url.startsWith("//") ? url : null;
  }
}

export async function initNativeShell(navigate: Navigate): Promise<void> {
  if (!isNativeApp()) return;
  const [{ App }, { SplashScreen }, { StatusBar, Style }] = await Promise.all([
    import("@capacitor/app"), import("@capacitor/splash-screen"), import("@capacitor/status-bar"),
  ]);
  try {
    await StatusBar.setStyle({ style: Style.Light });
    if (nativePlatform() === "android") await StatusBar.setBackgroundColor({ color: "#F6F5F2" });
  } catch {
    // Status bar styling is cosmetic.
  }
  await App.addListener("backButton", ({ canGoBack }) => {
    if (canGoBack) window.history.back();
    else void App.minimizeApp();
  });
  await App.addListener("appUrlOpen", ({ url }) => {
    const path = internalPath(url);
    if (path) navigate(path);
  });
  await SplashScreen.hide();
}
