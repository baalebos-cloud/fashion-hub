// Set the version shown in the App Store / Google Play and bump the build number.
//   npm run app:version            -> same version, next build number (for a new upload)
//   npm run app:version -- 1.1.0   -> new version, next build number
// Writes app-version.json (read by Android's build.gradle) and the iOS project settings.
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

export function nextVersion(current, requested) {
  if (requested !== undefined && !/^\d+\.\d+\.\d+$/.test(requested)) {
    throw new Error(`Version must look like 1.2.3, got "${requested}"`);
  }
  return { version: requested ?? current.version, build: Number(current.build) + 1 };
}

export function applyToIosProject(pbxproj, { version, build }) {
  return pbxproj
    .replace(/MARKETING_VERSION = [^;]+;/g, `MARKETING_VERSION = ${version};`)
    .replace(/CURRENT_PROJECT_VERSION = [^;]+;/g, `CURRENT_PROJECT_VERSION = ${build};`);
}

if (import.meta.url.startsWith("file:") && process.argv[1] === fileURLToPath(import.meta.url)) {
  const root = fileURLToPath(new URL("..", import.meta.url));
  const versionFile = `${root}app-version.json`;
  const iosProject = `${root}ios/App/App.xcodeproj/project.pbxproj`;
  const next = nextVersion(JSON.parse(readFileSync(versionFile, "utf8")), process.argv[2]);
  writeFileSync(versionFile, `${JSON.stringify(next, null, 2)}\n`);
  writeFileSync(iosProject, applyToIosProject(readFileSync(iosProject, "utf8"), next));
  console.log(`Tailora app version ${next.version} (build ${next.build}) for iPhone and Android.`);
}
