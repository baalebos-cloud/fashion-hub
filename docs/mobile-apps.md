# Tailora iPhone and Android apps

The apps are the same React website, packaged with [Capacitor](https://capacitorjs.com) (v8) and a few
native features. Everything lives in `frontend/`: `capacitor.config.ts`, `ios/` (Xcode project) and
`android/` (Android Studio project).

## What the apps add on top of the website

| Feature | Where |
|---|---|
| Stay signed in after the app is closed (iOS Keychain / Android Keystore, this device only) | `src/lib/native/session.ts` |
| `tailora://app/...` links open the right page | `src/lib/native/app-shell.ts`, `Info.plist`, `AndroidManifest.xml` |
| Android back button, status bar colours, launch screen | `src/lib/native/app-shell.ts`, `capacitor.config.ts` |
| Push notification registration (phones saved via `POST /api/v1/devices`; sending comes in phase 3) | `src/lib/native/push.ts`, `backend/app/api/v1/devices.py` |
| Microphone permission for in-app calls | `NSMicrophoneUsageDescription` (iOS), `RECORD_AUDIO` (Android) |

The website itself is unchanged: none of this runs outside the apps.

## Build

The apps load the bundled website from local files, so they need the full backend address:

```bash
cd frontend
VITE_API_BASE_URL=https://<backend>.up.railway.app/api/v1 npm run app:sync
npm run app:ios       # opens Xcode
npm run app:android   # opens Android Studio
```

`app:sync` refuses to build without an `https://…/api/v1` address. The backend already allows the
apps' origins (`MOBILE_APP_ORIGINS`: `capacitor://localhost`, `https://localhost`).

## One-time setup still needed

| For | What | Who |
|---|---|---|
| Android builds | Install Android Studio (includes the Android SDK) | Owner |
| Push on Android | Firebase project → add an Android app `ng.tailora.app` → put `google-services.json` in `frontend/android/app/` | Owner |
| Push on iPhone, TestFlight, App Store | Apple Developer Program; in Xcode set the Team, add the *Push Notifications* capability | Owner |
| Real app icon | Replace the placeholder (white serif "T" on indigo) in `ios/App/App/Assets.xcassets/AppIcon.appiconset` and `android/app/src/main/res/mipmap-*` | Owner / designer |

`appId` is `ng.tailora.app`. It can be changed until the first upload to the App Store or Google Play,
then it is permanent.

## Tested

- iPhone simulator (iOS, Xcode 27.2): the app builds, launches, shows the launch screen then the home
  page against a local backend, keeps pages clear of the status bar, opens `tailora://login` on the
  sign-in page, and reads the Keychain at start-up.
- Unit tests (`tests/components/NativeApp.test.tsx`): saving and restoring the sign-in, link handling,
  push registration and sign-out unregistering.
- Not yet tested: signing in inside the simulator end to end (the simulator automation could not type
  reliably), any Android build (Android Studio not installed), push delivery (needs Firebase / Apple).
