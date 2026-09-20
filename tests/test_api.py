import sys
import time
from pathlib import Path

# Add project root to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from fastapi.testclient import TestClient
from backend.main import app


def test_full_api_flow():
    print("=== Testing DocuNext Full API Integration ===")
    client = TestClient(app)

    # 1. Health check
    print("1. Health check...")
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["offline"] is True
    print("   [PASS] Health check OK")

    # 2. Frontend static route
    print("2. Frontend static serving...")
    res = client.get("/")
    assert res.status_code == 200
    assert "DocuNext" in res.text
    assert "stepper-nav" in res.text
    print("   [PASS] Frontend served index.html")

    # 3. Load sample demo assets
    print("3. Loading Demo Sample Assets...")
    res = client.post("/api/sample/load?sample_type=flat")
    assert res.status_code == 200
    data = res.json()
    tpl_id = data["template"]["template_id"]
    data_id = data["data"]["data_id"]
    headers = data["data"]["headers"]
    preview_rows = data["data"]["preview_rows"]
    assert len(headers) >= 4
    assert len(preview_rows) == 10
    print(f"   [PASS] Template ID: {tpl_id}, Data ID: {data_id}, Rows: {len(preview_rows)}")

    # 4. Preview sample stamping
    print("4. Testing Live Preview Endpoint...")
    sample_fields = [
        {
            "id": "f_test1",
            "name": "Recipient Name",
            "binding": "{{Recipient Name}}",
            "x": 0.15,
            "y": 0.38,
            "width": 0.70,
            "height": 0.08,
            "font_family": "serif",
            "font_size": 26,
            "auto_shrink": True,
            "bold": True,
            "color": "#1E3A8A",
            "align": "center",
        }
    ]
    res = client.post(
        "/api/preview/sample",
        json={
            "template_id": tpl_id,
            "fields": sample_fields,
            "row_data": preview_rows[0],
            "page_num": 0,
        },
    )
    assert res.status_code == 200
    p_data = res.json()
    assert p_data["preview_image"].startswith("data:image/png;base64,")
    print("   [PASS] Live preview image rendered successfully")

    # 5. Project Save & Load
    print("5. Testing Project Save & Load...")
    save_res = client.post(
        "/api/projects/save",
        json={
            "name": "integration_test_project",
            "project_data": {
                "version": "1.0",
                "filename_pattern": "{Recipient Name}_{Certificate ID}.pdf",
                "fields": sample_fields,
            },
        },
    )
    assert save_res.status_code == 200
    list_res = client.get("/api/projects/list")
    assert list_res.status_code == 200
    projects = [p["name"] for p in list_res.json()["projects"]]
    assert "integration_test_project" in projects

    load_res = client.get("/api/projects/integration_test_project")
    assert load_res.status_code == 200
    assert len(load_res.json()["project_data"]["fields"]) == 1
    print("   [PASS] Project saved, listed, and loaded successfully")

    # 6. Bulk Generation Job
    print("6. Testing Bulk Generation Trigger...")
    gen_res = client.post(
        "/api/generate",
        json={
            "template_id": tpl_id,
            "data_id": data_id,
            "fields": sample_fields,
            "filename_pattern": "{Recipient Name}_{Certificate ID}.pdf",
            "page_num": 0,
        },
    )
    assert gen_res.status_code == 200
    job_id = gen_res.json()["job_id"]
    print(f"   [PASS] Job started with ID: {job_id}")

    # Poll status until completed
    print("7. Polling Job Progress...")
    for _ in range(40):
        status_res = client.get(f"/api/jobs/{job_id}/status")
        assert status_res.status_code == 200
        st = status_res.json()
        if st["status"] in ["completed", "failed"]:
            break
        time.sleep(0.1)

    assert st["status"] == "completed"
    assert st["processed_rows"] == 10
    assert st["percent"] == 100
    print(f"   [PASS] Job status: {st['status']} ({st['processed_rows']}/{st['total_rows']} rows)")

    # 8. Verify ZIP download
    print("8. Testing ZIP Download...")
    zip_res = client.get(f"/api/jobs/{job_id}/download-zip")
    assert zip_res.status_code == 200
    assert zip_res.headers["content-type"] == "application/zip"
    assert len(zip_res.content) > 1000
    print(f"   [PASS] ZIP downloaded: {len(zip_res.content)} bytes")

    # 9. Verify Individual file download
    print("9. Testing Individual File Download...")
    files_res = client.get(f"/api/jobs/{job_id}/files")
    assert files_res.status_code == 200
    files = files_res.json()["files"]
    assert len(files) == 10
    first_file = files[0]["filename"]
    pdf_res = client.get(f"/api/jobs/{job_id}/download/{first_file}")
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert len(pdf_res.content) > 1000
    print(f"   [PASS] Individual file '{first_file}' verified ({len(pdf_res.content)} bytes)")

    print("\nALL API INTEGRATION TESTS PASSED! [OK]")


if __name__ == "__main__":
    test_full_api_flow()
