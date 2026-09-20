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


def test_email_csv_and_persistence(tmp_path):
    from backend.email_service import generate_email_csv_report, load_persisted_email_report, _save_report

    mock_job = {
        "id": "job123",
        "status": "completed",
        "total": 2,
        "processed": 2,
        "succeeded": 1,
        "failed": 1,
        "logs": [
            {"index": 0, "recipient": "Alice", "target_email": "alice@example.com", "status": "sent", "timestamp": "12:00:00"},
            {"index": 1, "recipient": "Bob", "target_email": "bob@example.com", "status": "failed", "timestamp": "12:00:05", "error": "550 Invalid User"},
        ]
    }
    csv_str = generate_email_csv_report(mock_job["logs"])
    assert "Row Number,Recipient Name,Target Email" in csv_str
    assert "Alice,alice@example.com,SENT" in csv_str
    assert "Bob,bob@example.com,FAILED" in csv_str

    report_path = tmp_path / "email_report.json"
    _save_report(mock_job, report_path)
    loaded = load_persisted_email_report(report_path)
    assert loaded is not None
    assert loaded["id"] == "job123"
    assert loaded["succeeded"] == 1
    assert len(loaded["logs"]) == 2


def test_email_selective_index_and_retry_logs():
    from backend.email_service import _update_or_append_log

    logs = [
        {"index": 0, "recipient": "Alice", "target_email": "alice@example.com", "status": "sent"},
        {"index": 1, "recipient": "Bob", "target_email": "bob@example.com", "status": "failed", "error": "Timeout"},
    ]

    # Retry Bob (index 1) with successful outcome
    _update_or_append_log(logs, {
        "index": 1,
        "recipient": "Bob",
        "target_email": "bob@example.com",
        "status": "sent",
        "error": None
    })

    # Should update in place without increasing length or duplicating
    assert len(logs) == 2
    assert logs[1]["status"] == "sent"
    assert logs[1]["error"] is None

    # Appending a new index (index 2)
    _update_or_append_log(logs, {
        "index": 2,
        "recipient": "Charlie",
        "target_email": "charlie@example.com",
        "status": "sent"
    })
    assert len(logs) == 3
    assert logs[2]["recipient"] == "Charlie"

