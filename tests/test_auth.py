import os
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from fastapi.testclient import TestClient
from backend.auth_service import (
    create_session_token,
    verify_session_token,
    is_auth_required,
    get_access_key,
)
from backend.main import app


def test_token_creation_and_verification():
    key = "super_secret_test_key_123"
    token = create_session_token(key, ttl_hours=2)
    assert verify_session_token(token, key) is True

    # Wrong key
    assert verify_session_token(token, "wrong_key") is False

    # Tampered signature
    parts = token.split(":")
    tampered = f"{parts[0]}:deadbeef"
    assert verify_session_token(tampered, key) is False

    # Expired token
    expired_token = create_session_token(key, ttl_hours=-1)
    assert verify_session_token(expired_token, key) is False

    # Empty / malformed
    assert verify_session_token("", key) is False
    assert verify_session_token("invalid_format", key) is False
    assert verify_session_token(None, key) is False


def test_auth_routes_open_mode(monkeypatch):
    monkeypatch.delenv("APP_ACCESS_KEY", raising=False)
    client = TestClient(app)

    res = client.get("/api/auth/status")
    assert res.status_code == 200
    assert res.json()["auth_required"] is False

    # In open mode, routes can be accessed without token
    res = client.get("/api/projects/list")
    assert res.status_code == 200


def test_auth_routes_protected_mode(monkeypatch):
    monkeypatch.setenv("APP_ACCESS_KEY", "mypassword999")
    client = TestClient(app)

    # Status check indicates auth required
    res = client.get("/api/auth/status")
    assert res.status_code == 200
    assert res.json()["auth_required"] is True

    # Protected route rejected without token
    res_unauth = client.get("/api/projects/list")
    assert res_unauth.status_code == 401

    # Invalid login attempt
    res_bad_login = client.post("/api/auth/login", json={"access_key": "wrong"})
    assert res_bad_login.status_code == 401
    assert res_bad_login.json()["success"] is False

    # Valid login attempt
    res_login = client.post("/api/auth/login", json={"access_key": "mypassword999"})
    assert res_login.status_code == 200
    data = res_login.json()
    assert data["success"] is True
    assert "token" in data
    token = data["token"]

    # Protected route with Bearer token
    res_auth = client.get(
        "/api/projects/list",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res_auth.status_code == 200

    # Protected route with ?token= query parameter (for direct downloads)
    res_query = client.get(f"/api/projects/list?token={token}")
    assert res_query.status_code == 200
