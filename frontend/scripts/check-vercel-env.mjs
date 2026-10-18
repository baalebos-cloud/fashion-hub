// Vercel serves this SPA as static files; it has no same-origin API proxy.
// Keep local Vite/Nginx builds free to use their existing /api/v1 proxy.
import process from "node:process";

const value = process.env.VITE_API_BASE_URL;
let valid = false;
try {
  const url = new URL(value);
  valid = typeof value === "string" && value === value.trim()
    && url.protocol === "https:" && Boolean(url.hostname)
    && !url.username && !url.password && !url.search && !url.hash
    && url.pathname !== "/";
} catch {
  // Do not echo a malformed variable, which might contain credentials.
}

if (!valid) {
  process.stderr.write(
    "Vercel configuration error: set VITE_API_BASE_URL to the complete HTTPS "
    + "backend API URL, including the API prefix (for example "
    + "https://backend.example/api/v1), then rebuild. Bare hostnames and "
    + "relative paths send API requests to the static frontend. "
    + "NEXT_PUBLIC_API_URL is not used by this Vite application.\n",
  );
  process.exitCode = 1;
} else {
  process.stdout.write("Vercel backend API URL configuration is valid.\n");
}
