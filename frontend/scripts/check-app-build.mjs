// The phone apps run from local files, so the API address must be a full https:// URL
// (a relative /api/v1 only works on the website behind its proxy).
const url = process.env.VITE_API_BASE_URL ?? "";
if (!/^https:\/\/[^/]+\/.*api\/v1\/?$/.test(url)) {
  console.error(
    "Set VITE_API_BASE_URL to the live backend, e.g.\n" +
    "  VITE_API_BASE_URL=https://<backend>.up.railway.app/api/v1 npm run app:sync\n" +
    `Got: "${url || "(empty)"}"`);
  process.exit(1);
}
console.log(`Building the apps against ${url}`);
