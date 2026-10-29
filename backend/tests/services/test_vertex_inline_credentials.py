"""Tests for Railway inline Vertex service account configuration (no network)."""
import json
import sys
from types import ModuleType, SimpleNamespace

import pytest
from app.services import vertex_service


class FakeCredentials:
    seen = None

    @classmethod
    def from_service_account_info(cls, info, scopes):
        cls.seen = info
        return object()


def _setup(monkeypatch, raw):
    fake_sa = ModuleType("google.oauth2.service_account")
    fake_sa.Credentials = FakeCredentials
    fake_oauth = ModuleType("google.oauth2")
    fake_oauth.service_account = fake_sa
    monkeypatch.setitem(sys.modules, "google.oauth2", fake_oauth)
    monkeypatch.setitem(sys.modules, "google.oauth2.service_account", fake_sa)
    import google
    monkeypatch.setattr(google, "oauth2", fake_oauth, raising=False)
    fake_genai = ModuleType("google.genai")
    seen = {}
    def client(**kwargs):
        seen.update(kwargs)
        return object()
    fake_genai.Client = client
    monkeypatch.setattr(google, "genai", fake_genai, raising=False)
    monkeypatch.setattr(vertex_service.settings, "VERTEX_AI_ENABLED", True)
    monkeypatch.setattr(vertex_service.settings, "GCP_PROJECT_ID", "test-project")
    monkeypatch.setattr(vertex_service.settings, "GCP_REGION", "us-central1")
    monkeypatch.setattr(vertex_service.settings, "GCP_SERVICE_ACCOUNT_JSON", raw)
    return seen


def test_inline_json_initializes_client(monkeypatch):
    info = {"type": "service_account", "client_email": "test@example.iam.gserviceaccount.com",
            "project_id": "test-project", "private_key": "fake"}
    seen = _setup(monkeypatch, json.dumps(info))
    assert vertex_service.VertexAIService()._client() is not None
    assert seen["project"] == "test-project"
    assert seen["credentials"] is not None


def test_malformed_json_fails_cleanly(monkeypatch, caplog):
    _setup(monkeypatch, "{not json")
    with pytest.raises(vertex_service.VertexUnavailable):
        vertex_service.VertexAIService()._client()
    assert "seam_vertex_setup_failed" in caplog.text
    assert "{not json" not in caplog.text


def test_escaped_pem_line_endings_normalized(monkeypatch):
    info = {"type": "service_account", "client_email": "test@example.iam.gserviceaccount.com",
            "project_id": "test-project", "private_key": "line1\\nline2"}
    _setup(monkeypatch, json.dumps(info))
    vertex_service.VertexAIService()._client()
    assert FakeCredentials.seen["private_key"] == "line1\nline2"
