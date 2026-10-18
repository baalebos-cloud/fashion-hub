# Railway database configuration

## Fix an empty-port startup failure

`ValueError: invalid literal for int() with base 10: ''` while SQLAlchemy
parses `DATABASE_URL` means the URI contains an empty port, such as
`HOST:/DATABASE`. This happens before a database connection is attempted.
Gunicorn retries cannot repair it, and no schema migration is needed to
resolve this parsing error.

1. In Railway, select the backend service and the correct environment, then
   open **Variables** and edit `DATABASE_URL`. Keep it server-side; never put
   a database credential in a frontend `VITE_*` variable.
2. Set the value using one of the provider options below. Do not share the
   actual URI, password, or a screenshot of the variable.
3. Apply the variable changes and deploy the backend again. If separate
   Celery worker and beat services use the same database, update their
   references and deployments as well.
4. Check the new deployment logs and health endpoints as described below.

### Railway-managed PostgreSQL

Use Railway's variable-reference picker to reference the database service's
`DATABASE_URL` in the backend service. For a database service named
`Postgres`, Railway expresses this as `${{Postgres.DATABASE_URL}}`; choose
the actual service name in your environment. Railway must resolve the
reference to a complete URI before starting the container. Do not paste an
unresolved reference into a local `.env` file.

The backend accepts `postgres://`, `postgresql://`, and
`postgresql+psycopg://`, selecting its installed psycopg driver automatically.
For a deployment running code from before this fix, use the explicit
`postgresql+psycopg://` scheme until the fix is merged and deployed.

### External PostgreSQL, including Supabase

Copy the **complete connection URI** from the database provider's connection
screen. Preserve its hostname, database, port, and query options, including
SSL settings. Choose the provider endpoint appropriate for a persistent
Python backend and reachable from Railway. A public TCP proxy or pooler can
use a different port from the database's internal endpoint; use the port
shown for that endpoint.

An illustrative URI, with placeholders only:

```text
postgresql+psycopg://USER:ENCODED_PASSWORD@HOST:5432/DATABASE?sslmode=require
```

Use a numeric port supplied by the provider. PostgreSQL also allows the
port to be omitted entirely, with no colon, to use its default. An empty
port (`HOST:/DATABASE`) is invalid. Do not guess a port or replace the
database destination to make validation pass.

If constructing a URI yourself, URL-encode the username and password once,
especially reserved characters such as `@`, `:`, `/`, `?`, `#`, and `%`.
Do not encode the whole URI or double-encode a provider-generated password.

## Verify the new deployment

After this fix is deployed, the following command inside the backend
container validates settings without printing the URI or connecting to the
database:

```sh
python -c 'from app.core.config import settings; print("Database URL configuration is valid.")'
```

This checks syntax and configuration only. A successful `/health/live`
response confirms the application has booted; `/health/ready` also checks
database and Redis connectivity. Use readiness to verify the configured
services are reachable. Authentication, DNS, TLS, PostGIS, or schema errors
after parsing require separate diagnosis; do not run migrations simply to
address the empty-port error.

The regression tests and CI containers use fake credentials and reserved
`.invalid` hosts for these startup checks. They do not change Railway
variables or access a deployed database. Correct the private Railway
variable and redeploy to resolve an existing malformed runtime value.
