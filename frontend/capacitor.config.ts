import type { CapacitorConfig } from "@capacitor/cli";

/**
 * Tailora's iPhone and Android apps: the same website build (dist/), packaged with native
 * features. Build with `npm run app:sync` (see docs/mobile-apps.md).
 * appId is permanent once the app is published to the App Store / Google Play.
 */
const config: CapacitorConfig = {
  appId: "ng.tailora.app",
  appName: "Tailora",
  webDir: "dist",
  server: {
    // Android serves the app from https://localhost (iOS uses capacitor://localhost).
    // Both are allowed by the backend's MOBILE_APP_ORIGINS.
    androidScheme: "https",
  },
  ios: {
    // Keep pages clear of the status bar / Dynamic Island and the home indicator.
    contentInset: "always",
    backgroundColor: "#F6F5F2", // shows behind the status bar: Tailora's paper colour
  },
  plugins: {
    SplashScreen: {
      launchAutoHide: false, // hidden by the app once it has drawn (lib/native/app-shell.ts)
      backgroundColor: "#F6F5F2",
      showSpinner: false,
    },
    PushNotifications: {
      presentationOptions: ["badge", "sound", "alert"],
    },
  },
};

export default config;
