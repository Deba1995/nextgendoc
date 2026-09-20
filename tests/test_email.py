import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from fastapi.testclient import TestClient
from backend.main import app
from backend.email_service import interpolate_template



def test_email_interpolation():
    row = {
        "Recipient Name": "Ada Lovelace",
        "Course Title": "Software Architecture",
        "Certificate ID": "CERT-2026-001"
    }
    subj = interpolate_template("Hello {{Recipient Name}} - {{Course Title}}", row)
    assert subj == "Hello Ada Lovelace - Software Architecture"


def test_smtp_auth_failure():
    client = TestClient(app)
    res = client.post("/api/email/test-connection", json={
        "host": "smtp.gmail.com",
        "port": 587,
        "use_tls": True,
        "use_ssl": False,
        "username": "invalid_user@gmail.com",
        "password": "wrong_password"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is False
    assert "Authentication failed" in data["message"] or "Connection error" in data["message"]


def test_email_api_routes():
    client = TestClient(app)
    # Test status of non-existent job
    res = client.get("/api/email/status/non_existent_id")
    assert res.status_code == 404

    # Test cancel non-existent job
    res_cancel = client.post("/api/email/cancel/non_existent_id")
    assert res_cancel.status_code == 200
    assert res_cancel.json()["cancelled"] is False
