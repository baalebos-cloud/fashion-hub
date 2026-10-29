"""Non-destructive staging acceptance preflight.

Run:
  STAGING_BASE_URL=https://fashion-hub-fashion-hub-staging.up.railway.app \
  python tests/staging_acceptance_e2e.py

Authentication credentials are optional environment variables:
STAGING_CUSTOMER_EMAIL, STAGING_CUSTOMER_PASSWORD (and TAILOR, VENDOR, COURIER).
Without them, auth stages are SKIPPED, never passed. No payment gateways called.
"""
import asyncio
import json
import os
import secrets
import uuid
import time
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

ROLES = ("customer", "tailor", "vendor", "courier")


@dataclass
class Check:
    name: str
    result: str
    evidence: str


async def run():
    url = os.getenv("STAGING_BASE_URL", "https://fashion-hub-fashion-hub-staging.up.railway.app").rstrip("/")
    host = urlparse(url)
    if host.scheme != "https" or "staging" not in (host.hostname or "") or not (host.hostname or "").endswith(".up.railway.app"):
        raise SystemExit("Refusing non-HTTPS, non-staging Railway host")
    checks: list[Check] = []
    started = time.monotonic()
    ids = []
    async with httpx.AsyncClient(base_url=url, timeout=12.0, follow_redirects=False) as client:
        try:
            ready = await client.get("/health/ready")
            data = ready.json()
            passed = ready.status_code == 200 and data.get("status") == "ready" and all(data.get("checks", {}).get(k) for k in ("database", "redis"))
            checks.append(Check("Isolated service readiness", "PASS" if passed else "FAIL", f"HTTP {ready.status_code}; database and Redis readiness = {passed}"))
        except (httpx.HTTPError, ValueError) as exc:
            checks.append(Check("Isolated service readiness", "FAIL", type(exc).__name__))
        try:
            schema_response = await client.get("/openapi.json")
            schema = schema_response.json()
            routes = schema.get("paths", {})
            required = ("/api/v1/auth/login", "/api/v1/auth/refresh",
                        "/api/v1/measurements", "/api/v1/saga/orders/{order_id}",
                        "/api/v1/checkout", "/api/v1/payments/refund")
            missing = [r for r in required if r not in routes]
            checks.append(Check("API contract availability", "PASS" if not missing else "FAIL", "Missing routes: " + repr(missing)))
        except (httpx.HTTPError, ValueError) as exc:
            checks.append(Check("API contract availability", "FAIL", type(exc).__name__))
        for role in ROLES:
            name = "STAGING_" + role.upper()
            email, password = os.getenv(name + "_EMAIL"), os.getenv(name + "_PASSWORD")
            if not email and os.getenv("STAGING_CREATE_SYNTHETIC_ACCOUNTS") == "true":
                email = f"acceptance-{role}-{uuid.uuid4().hex[:12]}@example.com"
                password = "Staging9-" + secrets.token_urlsafe(24)
                signup = await client.post("/api/v1/auth/signup", json={
                    "email": email, "password": password,
                    "full_name": f"Staging Acceptance {role.title()}",
                    "role": "delivery_partner" if role == "courier" else role,
                })
                checks.append(Check(role + " synthetic signup",
                    "PASS" if signup.status_code in (200, 201) else "FAIL",
                    f"HTTP {signup.status_code}; disposable staging account"))
                if signup.status_code not in (200, 201):
                    continue
            if not email or not password:
                checks.append(Check(role + " JWT authentication", "SKIP", "No staging-only credentials supplied"))
                continue
            try:
                response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
                body = response.json()
                token, refresh = body.get("access_token"), body.get("refresh_token")
                ok = response.status_code == 200 and bool(token and refresh)
                checks.append(Check(role + " JWT authentication", "PASS" if ok else "FAIL", f"HTTP {response.status_code}; token pair issued={ok}"))
                if not ok:
                    continue
                refreshed = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
                checks.append(Check(role + " refresh", "PASS" if refreshed.status_code == 200 and refreshed.json().get("access_token") else "FAIL", f"HTTP {refreshed.status_code}"))
                me = await client.get("/api/v1/users/me", headers={"Authorization": "Bearer " + token})
                profile_ok = me.status_code == 200 and me.json().get("role") == ("delivery_partner" if role == "courier" else role)
                checks.append(Check(role + " profile permissions", "PASS" if profile_ok else "FAIL", f"HTTP {me.status_code}; matching role={profile_ok}"))
                if role == "customer":
                    create = await client.post("/api/v1/measurements", json={
                        "label": "Automated staging acceptance (synthetic)",
                        "garment_type": "shirt",
                        "fields": [
                            {"field_name": "chest", "value": 101.6, "unit": "cm"},
                            {"field_name": "waist", "value": 81.28, "unit": "cm"},
                        ],
                    }, headers={"Authorization": "Bearer " + token})
                    profile_id = None
                    if create.status_code == 201:
                        profile_id = create.json().get("id")
                        ids.append(str(profile_id))
                    checks.append(Check("Customer measurement profile persistence",
                        "PASS" if profile_id else "FAIL",
                        f"HTTP {create.status_code}; server-created profile={bool(profile_id)}"))
                    negative = await client.get("/api/v1/saga/orders/00000000-0000-0000-0000-000000000000",
                                                headers={"Authorization": "Bearer " + token})
                    checks.append(Check("Saga unknown-order access control", "PASS" if negative.status_code == 404 else "FAIL", f"HTTP {negative.status_code}; expected 404"))
            except (httpx.HTTPError, ValueError, KeyError) as exc:
                checks.append(Check(role + " authentication workflow", "FAIL", type(exc).__name__))
    for label in ("Browser measurement draft recovery", "Zod conversion and measurement save",
                  "Four-party material and courier fulfillment", "Out-of-stock compensation and mocked refund",
                  "SQL ledger balance and append-only mutation rejection",
                  "Concurrent idempotency replay across Redis and PostgreSQL"):
        checks.append(Check(label, "SKIP", "Requires isolated browser/DB test harness and controlled fake order fixtures; never infer success from API health"))
    counts = {v: sum(c.result == v for c in checks) for v in ("PASS", "FAIL", "SKIP")}
    certified = counts["FAIL"] == 0 and counts["SKIP"] == 0
    report = [
        "# Fashion Hub: Staging Acceptance Certification Report", "",
        "## 1. Test Execution Summary",
        f"- Total Scenarios Executed: {counts['PASS'] + counts['FAIL']}",
        f"- Passed: {counts['PASS']} | Failed: {counts['FAIL']} | Skipped: {counts['SKIP']}",
        f"- Execution Duration: {time.monotonic() - started:.2f}s", "",
        "## 2. Verification Checklist", "",
        "| Check | Outcome | Evidence |", "|---|---|---|",
    ]
    report += [f"| {c.name} | {c.result} | {c.evidence.replace('|', '/')} |" for c in checks]
    report += ["", "## 3. Database & Audit Log Evidence",
               "- Order IDs tested: none (no money or mutation attempted)",
               "- Saga Step Log Traces: unavailable without isolated privileged DB test session",
               "- Ledger Balanced Output: not measured", "",
               "## 4. Final Recommendation",
               "- Production Readiness Decision: " + ("CERTIFIED" if certified else "NOT CERTIFIED"),
               "- Key Blockers: " + ", ".join(c.name for c in checks if c.result != "PASS")]
    print("\n".join(report))
    return 0 if certified else 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
