# Dependency security and credential rollout

## What this phase changes

The 18 October 2026 audit found nine frontend dependency findings (seven high,
two moderate). Patching within Tailwind 3 left seven findings because its braces
chain has no fixed compatible release. Tailwind 4.3.3 and its PostCSS adapter
remove that chain; tailwind-merge is upgraded for Tailwind 4. Existing Workroom
colors, fonts and card radius still come from `tailwind.config.js`. The legacy
`rounded` and small-shadow utilities retain their prior values. Browser checks
verify production CSS, mobile layout and visible keyboard focus.

The backend audit flagged python-jose/ecdsa, python-multipart, Starlette, pytest
and the unused WeasyPrint installation. This phase replaces python-jose with
PyJWT, updates FastAPI and multipart parsing, updates pytest/pytest-asyncio, and
removes the unused PDF engine. The application still returns invoice records;
PDF rendering remains unimplemented. The reviewed npm and Python graphs report
zero known vulnerabilities, with no advisory exclusions. Audits are a snapshot
of the advisory databases, so weekly checks continue after this PR.

## Credential compatibility

New and reset passwords use Argon2id (64 MiB memory, three iterations, four
lanes). Existing bcrypt and bcrypt_sha256 records remain readable through a
legacy verifier. A successful active-account login replaces the stored hash in
the same commit as its refresh session. Failed, inactive and malformed-hash
logins do not rewrite credentials. Passlib and its compatible bcrypt backend
remain solely for legacy verification and related compatibility tests; retire
those dependencies once legacy records have been upgraded. Size worker capacity
for the memory cost of concurrent authentication operations.

JWTs retain the existing standard signing format, subject, token type, expiry
and token ID. Keep the signing secret and configured algorithm unchanged during
rollout. Decode requires those issuer claims and verifies the configured
algorithm; a refresh token cannot authorize an access-token route. Extra claims
cannot replace server-owned identity, role, expiry or type.

No database migration or mass password reset is required. No project/live
database was accessed for this work. After deploying, exercise a development
account through signup, login, protected access and refresh. Old application
images do not understand Argon2id hashes: once hashes have been written, retain
the new verifier when rolling back, backport that verifier, or deploy a forward
fix. Do not overwrite password hashes to make an old image work.

## Install and maintain locks

Python's direct pins live in `backend/requirements.in`. The generated
`backend/requirements.txt` pins the complete graph with SHA-256 hashes for the
Python 3.12/Linux target used by CI and Docker. Development, tests and the image
install the same lock:

```sh
cd backend
python -m pip install --require-hashes -r requirements.txt
```

Regenerate with the reviewed pip-tools version. Use `--upgrade` when deliberately
refreshing transitive dependencies, and review that diff before publishing:

```sh
python -m pip install pip-tools==7.6.2
export CUSTOM_COMPILE_COMMAND='python -m piptools compile --generate-hashes --output-file=requirements.txt requirements.in'
pip-compile --generate-hashes --no-emit-index-url --no-emit-trusted-host --output-file=requirements.txt requirements.in
```

Frontend dependencies use `npm ci` and the committed `package-lock.json`. Run
`npm audit`, unit tests, lint, the production build and `npm run test:browser`
after changes. Browser checks need `npx playwright install --with-deps chromium`.
Tailwind 4 targets modern browsers (Safari 16.4+, Chrome 111+, Firefox 128+);
older browsers need a separate compatibility plan before being advertised as
supported.

Dependency-security CI verifies Python lock/source consistency and runs strict
pip-audit plus npm audit over runtime and development dependencies. It runs for
PRs, main pushes and weekly schedules. Dependabot proposes weekly npm, pip and
GitHub Actions updates; minor/patch changes are grouped, and merges remain with
the repository owner. CI never updates dependencies or commits candidate files.
Engineering CI verifies application imports, real PostgreSQL/PostGIS flows,
credential/token regressions, frontend tests/build, desktop/mobile browser
styles, and non-root Docker startup/liveness. Docker images are built locally in
the runner and are not published or deployed.

## Remaining scope

This change does not complete refresh-token rotation/reuse detection, one-use
password reset tokens, privileged MFA, refunds/payout delivery, inventory or
international shipping/tax. The image still includes the project's development
tooling in its shared Python lock; runtime/development image separation, OS
image scanning and SBOM publication remain follow-up work. See the
[architecture plan](architecture-review.md) and [checkout rollout](catalog-checkout.md).
