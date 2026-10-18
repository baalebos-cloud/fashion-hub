# Vercel frontend and Railway backend

## Configure the API address

This frontend uses Vite. Its API setting is **`VITE_API_BASE_URL`**, not
`NEXT_PUBLIC_API_URL`. The value is public and embedded in the JavaScript
bundle at build time; changing a variable requires a new frontend build.

1. In the Vercel project, set **Root Directory** to `frontend`.
2. In **Settings → Environment Variables**, add or update
   `VITE_API_BASE_URL` for Production. Set Preview separately to an appropriate
   test backend; do not point previews at production data by default.
3. Use the complete HTTPS backend API URL, including the backend's API
   prefix (`/api/v1` by default). For the reported Railway deployment:

   ```text
   https://fashion-hub-production-2661.up.railway.app/api/v1
   ```

4. Deploy the frontend again. The repository's Vercel build command validates
   this variable before building; clear any dashboard Build Command override
   that would bypass `vercel.json`.

A value such as `fashion-hub-production-2661.up.railway.app` is a relative
path. The browser requests
`https://fashion-hub-tawny.vercel.app/fashion-hub-production-2661.up.railway.app/auth/signup`
instead of reaching Railway. Vercel's static SPA fallback cannot handle that
signup POST and returns 405. The local `/api/v1` default also requires a
reverse proxy; Vite's development proxy does not run on Vercel.

Do not put database URLs, payment secret keys, or admin passwords in
`VITE_*` variables. They are included in browser code.

## Allow the frontend origin on Railway

In the Railway backend service, `CORS_ALLOWED_ORIGINS` must include the
exact public frontend origin. For the reported frontend:

```text
CORS_ALLOWED_ORIGINS=["https://fashion-hub-tawny.vercel.app"]
```

Preserve any other required trusted origins. An origin contains the scheme
and hostname, plus a port when applicable, with no path or trailing slash.
Apply the backend variable changes and redeploy. Allow intended preview
origins explicitly when testing a preview; do not use `*` with credentials.

## Verify signup routing

1. Open `https://fashion-hub-production-2661.up.railway.app/health/live` to
   check that the backend has booted. `/health/ready` also checks database
   and Redis connectivity.
2. In the browser's Network panel, a vendor signup should send **POST** to
   `https://fashion-hub-production-2661.up.railway.app/api/v1/auth/signup`,
   with `role: "vendor"`. A successful request returns 201.
3. A cross-origin JSON request first sends OPTIONS. If the browser blocks
   the preflight, check the exact CORS origin on Railway. Avoid sharing
   request bodies, Authorization headers, or tokens when diagnosing this.

The API uses one public signup route for all supported public roles. Admin
accounts are deliberately excluded. Do not change signup to GET to address
a 405; correct the destination URL.

## Create the first admin

Use the Railway backend container, with its configured database and existing
schema. From an authenticated, linked Railway CLI on your machine:

```sh
railway ssh --service YOUR_BACKEND_SERVICE_NAME
```

Inside the container, run from `/app`, replacing the example values privately:

```sh
python scripts/create_admin.py --email admin@example.com --password 'YOUR_STRONG_PASSWORD' --full-name 'Platform Admin'
```

The script hashes the password, creates an active, email-verified admin, and
refuses to create another when an admin already exists. Use the normal login
page with that email and password. If an admin already exists, use the normal
password-reset flow instead of creating another through public signup.

The URL validator and regression tests do not change Vercel/Railway variables
or create accounts in a deployed database. Apply the private configuration
changes and rebuild the affected deployments to fix an existing deployment.
