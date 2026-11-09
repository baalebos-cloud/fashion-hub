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
| Push notification registration (phones saved via `POST /api/v1/devices`) | `src/lib/native/push.ts`, `backend/app/api/v1/devices.py` |
| Incoming-call alerts that ring when the app is closed, replaced by "Missed call" if unanswered | `backend/app/services/call_push.py`, `backend/app/integrations/notifications/mobile_push.py`, `src/lib/native/push.ts` |
| Permission texts: microphone for calls, camera for photos you take, location while the app is open | `Info.plist` (iOS), `AndroidManifest.xml` (Android) |
| Store readiness: version numbers, privacy manifest, release signing, listing and privacy answers | [app-store-release.md](app-store-release.md) |
| Security (OWASP MASVS): what is protected on the phone, and decisions left to the owner | [mobile-security.md](mobile-security.md) |
| Paying: Paystack opens in the phone's browser and returns to the app through `/payment/app-return` | `src/lib/payments/return-url.ts`, [payments-go-live.md](payments-go-live.md) |

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

## Incoming-call alerts

When a call starts, the backend sends the person being called an urgent alert, *"Ada is calling —
Tailora call about order TL-… Tap to answer."*, to every phone they're signed in on:

- **Android** (Firebase): the *Incoming calls* channel, maximum importance, with Tailora's ringtone
  (`android/app/src/main/res/raw/ringtone.wav`) and vibration.
- **iPhone** (Apple, sent directly): a time-sensitive alert with the default sound, so it can break
  through Focus once the *Time Sensitive Notifications* capability is turned on in Xcode.

Tapping the alert opens Tailora on the incoming-call screen (answering needs one more tap there, which
also lets the phone grant the microphone). If the call is cancelled or nobody answers within 45 s, the
alert is replaced with *"Missed call from Ada"*. Alerts are sent after the API has replied, so a slow
push service never delays a call. Dead phone tokens are removed automatically.

The full phone-style call screen (CallKit on iPhone, full-screen calls on Android) is a possible later
step; it needs the call audio rebuilt natively.

Backend settings (all off until set): `APNS_KEY_ID`, `APNS_TEAM_ID`, `APNS_PRIVATE_KEY`,
`APNS_BUNDLE_ID`, `APNS_USE_SANDBOX` (true only for builds run from Xcode; **false for TestFlight and App Store** builds, which use Apple's production service), `FCM_PROJECT_ID`,
`FCM_SERVICE_ACCOUNT_JSON`. See `backend/.env.example`.

## One-time setup still needed

| For | What | Who |
|---|---|---|
| Android builds | Install Android Studio (includes the Android SDK) | Owner |
| Push on Android | Firebase project → add an Android app `ng.tailora.app` → put `google-services.json` in `frontend/android/app/` | Owner |
| Push on iPhone, TestFlight, App Store | Apple Developer Program; in Xcode set the Team, add the *Push Notifications* and *Time Sensitive Notifications* capabilities; create an APNs key (.p8) for the backend | Owner |
| Call alerts on Android | In Firebase, create a service account key for the backend (`FCM_SERVICE_ACCOUNT_JSON`) | Owner |
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
  Call alerts are tested against Apple's and Firebase's documented request formats with the network
  stubbed; real delivery needs the keys above and real phones.
