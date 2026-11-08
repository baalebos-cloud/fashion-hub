"""Phones registered for push: own registrations only, a token follows the latest sign-in."""
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.rate_limit import limiter
from app.main import app
from app.models.device_token import DeviceToken

TOKEN = "fcm:APA91bH-test_token.0123456789"


@pytest.fixture()
def ctx(db, make_user):
    limiter.reset()
    a, b = make_user(), make_user(role="tailor")
    current = [a]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: current[0]
    with TestClient(app) as http:
        yield dict(http=http, db=db, a=a, b=b, current=current)
    app.dependency_overrides.clear()


def test_register_moves_to_the_latest_account_and_unregisters(ctx):
    http, db = ctx["http"], ctx["db"]
    assert http.post("/api/v1/devices", json={"platform": "android", "token": TOKEN}).status_code == 204
    assert http.post("/api/v1/devices", json={"platform": "android", "token": TOKEN}).status_code == 204  # repeat is fine
    assert db.query(DeviceToken).filter_by(token=TOKEN).one().user_id == ctx["a"].id
    ctx["current"][0] = ctx["b"]
    assert http.delete(f"/api/v1/devices/{TOKEN}").status_code == 204  # can't remove someone else's
    assert db.query(DeviceToken).filter_by(token=TOKEN).count() == 1
    http.post("/api/v1/devices", json={"platform": "android", "token": TOKEN})
    db.expire_all()
    assert db.query(DeviceToken).filter_by(token=TOKEN).one().user_id == ctx["b"].id
    assert http.delete(f"/api/v1/devices/{TOKEN}").status_code == 204
    assert db.query(DeviceToken).filter_by(token=TOKEN).count() == 0


@pytest.mark.parametrize("body", [{"platform": "web", "token": TOKEN}, {"platform": "ios", "token": "short"},
                                  {"platform": "ios", "token": "bad token with spaces!!"}, {"platform": "ios"}])
def test_rejects_bad_registrations(ctx, body):
    assert ctx["http"].post("/api/v1/devices", json=body).status_code == 422


@pytest.mark.parametrize("origin", ["capacitor://localhost", "https://localhost"])
def test_the_apps_may_call_the_api(ctx, origin):
    assert origin in settings.MOBILE_APP_ORIGINS
    res = ctx["http"].options("/api/v1/devices", headers={"Origin": origin, "Access-Control-Request-Method": "POST",
                                                          "Access-Control-Request-Headers": "authorization,content-type"})
    assert res.status_code == 200 and res.headers["access-control-allow-origin"] == origin
