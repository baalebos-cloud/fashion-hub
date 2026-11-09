# Phone app security (OWASP MASVS / MASTG)

How the Tailora iPhone and Android apps measure up against the
[OWASP Mobile Application Security Verification Standard](https://mas.owasp.org/MASVS/), using the tests in
the [Mobile Application Security Testing Guide](https://mas.owasp.org/MASTG/0x06b-iOS-Security-Testing/).
The apps are the website packaged with Capacitor, so most security lives in the backend (every request is
checked there); this page covers what the phone itself must protect.

## In place

| Area | Control | Where |
|---|---|---|
| STORAGE | Sign-in tokens in the iOS Keychain / Android Keystore, this device only, never synced to iCloud | `src/lib/native/session.ts` |
| STORAGE | No app data in cloud backups or device transfers (Android); Keychain items are device-only (iOS) | `res/xml/data_extraction_rules.xml`, `allowBackup="false"` |
| STORAGE | The app-switcher / recent-apps picture is covered, so a NIN, address, order or chat isn't kept in it | `SceneDelegate.swift` (iOS), `MainActivity.java` (Android) |
| STORAGE | NIN field: no keyboard learning, autocorrect or autofill suggestions | `KYCForm.tsx` |
| STORAGE | Measurement drafts and cached data cleared on sign-out; sign-out also removes the stored tokens and push registration | `lib/auth/account-isolation.ts`, `store/auth.store.ts` |
| STORAGE | No tokens, NINs or personal data in logs (app or backend) | backend loggers; no `console.log` in the app |
| CRYPTO | No keys or secrets in the app; payments, identity and push keys stay on the backend | `.env` on Railway only |
| AUTH | Sessions are short-lived access tokens with refresh rotation; admins need a fresh authenticator code for sensitive decisions | backend `auth_service`, `admin_auth_service` |
| NETWORK | HTTPS only. iOS App Transport Security is on with no exceptions; Android blocks cleartext and, in release builds, trusts only the phone's built-in certificates | `Info.plist` (no ATS exceptions), `res/xml/network_security_config.xml` |
| PLATFORM | `tailora://` links only open pages inside the app; they never run actions or load outside pages | `lib/native/app-shell.ts` (`internalPath`) |
| PLATFORM | Outside links (Paystack, maps) open in the phone's browser, not inside the app's WebView | Capacitor default navigation |
| PLATFORM | Permissions asked only when used, with plain explanations (microphone, camera, location); no tracking | `Info.plist`, `AndroidManifest.xml`, `PrivacyInfo.xcprivacy` |
| CODE | Dependencies audited on every pull request (npm audit, pip-audit); iOS 15+ and Android 7+ (API 24) minimum | CI `Dependency security` |
| RESILIENCE | WebView remote debugging is only on in debug builds (Capacitor's default); release builds can't be inspected | `capacitor.config.ts` defaults |

## Decisions for the owner

These are stronger protections that cost something. None is required for a marketplace of this kind;
each is worth doing before handling more sensitive data or if abuse appears.

| Option | What it protects against | Cost / risk |
|---|---|---|
| **Certificate pinning** (MASVS-NETWORK-2) | Interception even with a trusted-but-wrong certificate | The app stops working if Railway changes its certificate chain unless pins are updated in an app release; needs a backup pin and a plan |
| **Biometric app lock** (MASVS-AUTH-2) | Someone using an unlocked phone to open Tailora | Extra step for users; needs a setting and a fallback |
| **Block screenshots entirely** | Screenshots of sensitive screens | Users can't screenshot orders or receipts to share them |
| **Jailbreak / root detection** (MASVS-RESILIENCE-1) | Running on a tampered phone | Easy to bypass; can lock out legitimate users; low value for this app |
| **Android code shrinking/obfuscation (R8)** (MASVS-RESILIENCE-3) | Reverse engineering the Android wrapper | The app logic is web code anyway; needs testing in Android Studio before release |

## How to test

- iOS: run from Xcode, open a page with personal details, swipe up to the app switcher: the Tailora cover
  shows instead of the page.
- Android: same with the recent-apps button.
- Network: with a proxy (e.g. mitmproxy) and its certificate installed as a user certificate, a release
  Android build refuses the connection; a debug build allows it for testing.
- Keychain: after signing out, the tokens are gone from the Keychain (the app asks to sign in after a
  restart).
