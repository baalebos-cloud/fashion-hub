"""First name, middle name and surname: sign-up, editing, and the rule for verified identities."""
import pytest
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.core.names import split_full_name
from app.core.rate_limit import limiter
from app.core.security import create_access_token
from app.main import app
from app.models.kyc_verification import KYCVerification
from app.models.user import User


@pytest.fixture()
def client(db, monkeypatch):
    def override_db():
        yield db
    app.dependency_overrides[get_db] = override_db
    limiter.reset()
    monkeypatch.setattr('app.workers.email_tasks.send_verification_email_task.delay', lambda **kwargs: None)
    try:
        with TestClient(app) as http:
            yield http
    finally:
        app.dependency_overrides.clear()
        limiter.reset()


def auth(user):
    return {"Authorization": "Bearer " + create_access_token(str(user.id), user.role)}


def patch_me(client, user, **body):
    return client.patch("/api/v1/users/me", json=body, headers=auth(user))


def test_split_full_name_for_older_accounts():
    assert split_full_name("Amaka Okafor") == ("Amaka", None, "Okafor")
    assert split_full_name("  Ifeoma   Chidinma  Nwosu ") == ("Ifeoma", "Chidinma", "Nwosu")
    assert split_full_name("Ade Bola Chi Okeke") == ("Ade", "Bola Chi", "Okeke")
    assert split_full_name("Madonna") == ("Madonna", None, None)
    assert split_full_name("") == (None, None, None)


def test_signup_with_three_parts(client, db):
    response = client.post("/api/v1/auth/signup", json={
        "email": "parts@example.com", "password": "Password123", "role": "tailor",
        "first_name": " Ifeoma ", "middle_name": "Chidinma", "last_name": "Nwosu"})
    assert response.status_code == 201, response.text
    body = response.json()
    assert (body["first_name"], body["middle_name"], body["last_name"]) == ("Ifeoma", "Chidinma", "Nwosu")
    assert body["full_name"] == "Ifeoma Chidinma Nwosu"


def test_signup_from_an_older_app_still_works_and_gets_parts(client, db):
    response = client.post("/api/v1/auth/signup", json={
        "email": "legacy@example.com", "password": "Password123", "role": "customer", "full_name": "Amaka  Okafor"})
    assert response.status_code == 201, response.text
    user = db.query(User).filter(User.email == "legacy@example.com").one()
    assert (user.first_name, user.middle_name, user.last_name, user.full_name) == ("Amaka", None, "Okafor", "Amaka Okafor")


@pytest.mark.parametrize("body", [
    {"first_name": "Amaka", "last_name": ""},
    {"first_name": "", "last_name": "Okafor"},
    {"first_name": "Am4ka", "last_name": "Okafor"},
    {"first_name": "Amaka", "last_name": "Okafor", "middle_name": "<script>"},
])
def test_signup_refuses_missing_or_odd_names(client, body):
    response = client.post("/api/v1/auth/signup", json={"email": "bad@example.com", "password": "Password123",
                                                        "role": "customer", **body})
    assert response.status_code in (400, 422), response.text


def test_anyone_can_correct_their_name(client, db, make_user):
    for role in ("customer", "tailor", "designer", "vendor", "delivery_partner"):
        user = make_user(role=role, full_name="Amaka Okafor")
        response = patch_me(client, user, first_name="Amaka", middle_name="Chiamaka", last_name="Okafor-Eze")
        assert response.status_code == 200, (role, response.text)
        assert response.json()["full_name"] == "Amaka Chiamaka Okafor-Eze"
        assert response.json()["middle_name"] == "Chiamaka"
        removed = patch_me(client, user, middle_name="")
        assert removed.json()["full_name"] == "Amaka Okafor-Eze" and removed.json()["middle_name"] is None


@pytest.mark.parametrize("first, middle, last", [
    ("Oluwaseun", "D'Angelo", "Adébáyọ̀ Jr."),
    ("राम", None, "शर्मा"),          # Devanagari vowel signs are marks outside U+0300–U+036F
    ("อนันต์", None, "สมบูรณ์"),     # Thai
    ("Zoë", "Mary-Kate", "O’Neil"),
])
def test_name_parts_accept_real_world_names(client, make_user, first, middle, last):
    user = make_user(full_name="Test User")
    response = patch_me(client, user, first_name=first, middle_name=middle or "", last_name=last)
    assert response.status_code == 200, response.text


@pytest.mark.parametrize("bad", ["-Amaka", "Amaka-", "Am4ka", "Amaka!", "Amaka  .  ", "'"])
def test_name_parts_refuse_symbols_and_stray_separators(client, make_user, bad):
    user = make_user(full_name="Test User")
    assert patch_me(client, user, first_name=bad, last_name="Okafor").status_code == 422


def test_overlong_parts_from_an_older_app_are_refused_not_cut(client, db, make_user):
    user = make_user(full_name="Amaka Okafor")
    long_word = "A" * 90
    response = patch_me(client, user, full_name=f"{long_word} Okafor")
    assert response.status_code == 422, response.text
    db.refresh(user)
    assert user.full_name == "Amaka Okafor"
    signup = client.post("/api/v1/auth/signup", json={"email": "long@example.com", "password": "Password123",
                                                     "role": "customer", "full_name": f"Okafor {long_word}"})
    assert signup.status_code == 422, signup.text


def test_older_app_can_still_send_full_name(client, db, make_user):
    user = make_user(full_name="Wrong Name")
    response = patch_me(client, user, full_name="Segun Ade Adewale")
    assert response.status_code == 200, response.text
    db.refresh(user)
    assert (user.first_name, user.middle_name, user.last_name) == ("Segun", "Ade", "Adewale")


def test_name_can_be_fixed_after_a_rejected_verification(client, db, make_user):
    user = make_user(role="tailor", full_name="Ifeoma Nwosu")
    db.add(KYCVerification(user_id=user.id, id_type="nin", status="rejected", nin_verified_full_name="NWOSU IFEOMA CHIDINMA",
                           rejection_reason="The name on your account doesn't match your NIN record."))
    db.commit()
    response = patch_me(client, user, first_name="Ify", last_name="Nwosu")
    assert response.status_code == 200, response.text  # free to change: it's checked again on resubmission


def test_verified_name_must_still_match_the_nin_record(client, db, make_user):
    user = make_user(role="tailor", full_name="Ifeoma Nwosu")
    db.add(KYCVerification(user_id=user.id, id_type="nin", status="verified", nin_verified_full_name="NWOSU IFEOMA CHIDINMA"))
    db.commit()
    ok = patch_me(client, user, first_name="Ifeoma", middle_name="Chidinma", last_name="Nwosu")
    assert ok.status_code == 200, ok.text
    refused = patch_me(client, user, first_name="Kemi", middle_name="", last_name="Adeyemi")
    assert refused.status_code == 422, refused.text
    assert "NIN record" in refused.text
    db.refresh(user)
    assert user.full_name == "Ifeoma Chidinma Nwosu"


def test_verified_by_staff_without_a_record_name_cannot_self_change(client, db, make_user):
    user = make_user(role="vendor", full_name="Adebayo Balogun")
    db.add(KYCVerification(user_id=user.id, id_type="nin", status="verified"))
    db.commit()
    assert patch_me(client, user, first_name="Someone", last_name="Else").status_code == 422
    # Saving the same name (e.g. other profile fields) is never blocked.
    assert patch_me(client, user, first_name="Adebayo", last_name="Balogun").status_code == 200
