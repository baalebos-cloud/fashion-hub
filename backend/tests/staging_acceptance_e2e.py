"""Safe, read-only staging acceptance preflight.

Runs separately from pytest suite and deliberately reports missing integrations
as NOT CERTIFIED. Never attempts a real gateway request or fabricates order IDs.
STAGING_BASE_URL must be a dedicated nonproduction endpoint.
"""
import json
import os
import time
from urllib.parse import urlparse
import httpx


REQUIRED_FLAGS = ("PAYMENTS_ENABLED", "REFUND_EXECUTION_ENABLED", "ENABLE_PRODUCTION_PAYMENTS")
CHECKS = {
    "authentication": "/api/v1/auth/login",
    "measurements": "/api/v1/measurements",
    "checkout": "/api/v1/checkout",
    "saga_audit": "/api/v1/saga/orders/{order_id}",
    "ai_extract": "/api/v1/ai/measurements/extract",
    "ai_spec": "/api/v1/ai/spec/estimate",
    "ai_advisor": "/api/v1/ai/advisor/stream",
}


def run():
    started = time.monotonic()
    base = os.environ.get("STAGING_BASE_URL", "").rstrip("/")
    parsed = urlparse(base)
    if parsed.scheme != "https" or not parsed.hostname or parsed.hostname in {"localhost", "127.0.0.1"}:
        raise SystemExit("STAGING_BASE_URL must be a dedicated HTTPS staging host")
    # Positive acknowledgement required; unset is never assumed safe.
    for name in REQUIRED_FLAGS:
        if os.environ.get(name, "").lower() != "false":
            raise SystemExit(f"Explicit {name}=false required for staging certification")
    report = {"environment": base, "checks": {}, "order_ids": [], "saga_traces": [],
              "ledger_variance": None, "production_readiness": "NOT CERTIFIED"}
    with httpx.Client(base_url=base, timeout=10, follow_redirects=False) as client:
        health = client.get("/health/ready")
        report["checks"]["readiness"] = health.status_code == 200
        spec_resp = client.get("/openapi.json")
        spec = spec_resp.json() if spec_resp.status_code == 200 else {}
        paths = spec.get("paths", {})
        for key, path in CHECKS.items():
            report["checks"][key] = path in paths
        # Route coverage cannot replace authenticated actor flows or DB evidence.
        for key in ("four_party_flow", "browser_recovery", "out_of_stock_compensation",
                    "append_only_ledger", "concurrent_idempotency", "postgis_coordinates"):
            report["checks"][key] = False
    report["duration_seconds"] = round(time.monotonic() - started, 3)
    print(json.dumps(report, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(run())
