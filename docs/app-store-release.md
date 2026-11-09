# Releasing the Tailora apps (App Store and Google Play)

How to get the iPhone and Android apps from this repository into the stores. The build setup is in
[mobile-apps.md](mobile-apps.md); this page covers what the stores ask for. Uploading and submitting is
done by the owner from their own Apple and Google accounts.

## Already in the project

| Store requirement | Where |
|---|---|
| App ID / package name `ng.tailora.app` (permanent after the first upload) | `capacitor.config.ts`, `android/app/build.gradle` |
| One version for both apps, build number bumped per upload | `frontend/app-version.json`, `npm run app:version` |
| Permission texts: microphone (calls), camera (photos you choose to take), location while the app is open | `ios/App/App/Info.plist`, `android/app/src/main/AndroidManifest.xml` |
| Apple privacy manifest (no tracking; what's collected and why) | `ios/App/App/PrivacyInfo.xcprivacy` |
| Export compliance: only standard HTTPS, so no encryption paperwork | `ITSAppUsesNonExemptEncryption = false` in `Info.plist` |
| Sign-in never copied to cloud backups or a new phone | `android:allowBackup="false"`, `res/xml/data_extraction_rules.xml`; iOS Keychain is "this device only" |
| Android release signing from a private key file that is never committed | `android/keystore.properties` (git-ignored), `signingConfigs` in `build.gradle` |
| App icon 1024×1024 (iOS) and all Android sizes | `AppIcon.appiconset`, `res/mipmap-*` |
| Privacy policy and terms pages | `/privacy`, `/terms` on the website |

## Still to decide before the first submission

- **In-app account deletion.** Apple requires that anyone who can create an account in the app can
  also start deleting it in the app (App Review Guideline 5.1.1(v)); Google Play requires a deletion
  link too. Tailora can't do this yet; it needs a backend change, proposed separately.
- **Real app icon.** The current icon is a placeholder (white serif "T" on indigo).

## Each release

```bash
cd frontend
npm run app:version            # next build number, same version
npm run app:version -- 1.1.0   # or a new version number
VITE_API_BASE_URL=https://<backend>.up.railway.app/api/v1 npm run app:sync
```

Every upload to either store needs a higher build number than the last one, even when a review is
rejected.

**iPhone (Xcode, `npm run app:ios`):** pick *Any iOS Device*, then Product → Archive → Distribute App →
App Store Connect. The build shows up in TestFlight about 15 minutes later. Set the backend's
`APNS_USE_SANDBOX=false` for TestFlight and App Store builds.

**Android (Android Studio, `npm run app:android`):** Build → Generate Signed App Bundle (.aab), using
the upload key below, then upload the .aab to Google Play Console → Testing → Internal testing first.

## One-time setup (owner)

### Apple

1. Join the Apple Developer Program (organization account if Tailora is registered as a company).
2. In Xcode, select the *App* target → Signing & Capabilities → choose the Team. Add *Push
   Notifications* and *Time Sensitive Notifications*.
3. In App Store Connect, create the app with bundle ID `ng.tailora.app`.
4. Create an APNs key (.p8) for the backend's call alerts (see mobile-apps.md).

### Google

1. Create a Google Play developer account.
2. Create the upload key once, and keep the file and passwords safe (outside the repository):
   ```bash
   keytool -genkey -v -keystore ~/tailora-upload.jks -keyalg RSA -keysize 2048 -validity 10000 -alias upload
   ```
3. Create `frontend/android/keystore.properties` (git-ignored):
   ```properties
   storeFile=/Users/<you>/tailora-upload.jks
   storePassword=...
   keyAlias=upload
   keyPassword=...
   ```
4. In Play Console, turn on Play App Signing (Google keeps the final signing key, and the upload key
   can be replaced if lost).

## Store listing (draft)

- **Name:** Tailora
- **Subtitle (iOS, 30 characters max):** Tailors, designers & fabrics
- **Short description (Google Play, 80 characters max):** Order custom outfits from trusted tailors and
  designers, with tracked delivery.
- **Description:**

  > Tailora connects you with verified tailors, fashion designers and fabric vendors near you.
  >
  > • Find tailors and designers near you and see their work, prices and reviews.
  > • Save your measurements once and reuse them for every order.
  > • Order a custom outfit or shop ready-made pieces and fabrics.
  > • Pay securely, and follow your order from cutting to delivery.
  > • Message or call your tailor, vendor or rider in the app; your phone number stays private.
  > • Get notified when your order moves, and when someone calls.
  >
  > For tailors, designers and vendors: manage orders, measurements, stock and payouts in one place.

- **Category:** Shopping (secondary: Lifestyle)
- **Keywords (iOS, 100 characters max):** tailor,fashion,designer,custom,outfit,clothing,measurements,fabric,aso ebi,nigeria
- **Support URL:** the website's `/contact` page. **Privacy policy URL:** `/privacy`.
- **Age rating:** 4+ / Everyone (no mature content; people can message each other, so mention user
  messaging in the questionnaire).
- **Screenshots:** iPhone 6.9" (1320×2868) and 6.5" (1284×2778); Android phone (at least 2, 16:9 or
  9:16). Suggested screens: home, a tailor's profile, measurements, order tracking, an in-app call.

### Review notes (App Review / Play)

Give reviewers a demo customer account (created on the live site for review only, with no real
payment details) and say:

> Calls are voice over the internet between the people on one order; nothing is recorded. The
> microphone is used only during a call. Location is used only while the app is open.

## Privacy answers

Use the same answers for Apple's *App Privacy* and Google Play's *Data safety*. Nothing is used for
tracking or advertising, nothing is sold, and all data is sent over HTTPS.

| Data | Why | Linked to the person |
|---|---|---|
| Name, email, phone number | Account and sign-in, order contact | Yes |
| Delivery address | Delivery | Yes |
| Precise location (while the app is open) | Nearby tailors, delivery spot, rider progress during an active delivery | Yes |
| Photos (only ones the person adds) | Designs, products, delivery proof, profile photo, measurements | Yes |
| Messages, measurements, reviews (other user content) | Orders between customers and professionals | Yes |
| User ID, push notification token | Account and notifications | Yes |
| Purchase history | Orders, invoices and receipts | Yes |
| Identity details for professionals (NIN, ID documents) | Verifying tailors, designers, vendors and riders | Yes |

- Card details are entered with the payment provider, not stored by Tailora.
- Call audio is relayed live and not recorded or stored.
- Google Play: data can be deleted on request (in the app once account deletion ships, and through
  the contact page until then).
