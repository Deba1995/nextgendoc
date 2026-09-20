import os
import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.data_service import (
    auto_match_headers,
    build_filename,
    clean_cell_value,
    interpolate_text,
    parse_spreadsheet,
)
from backend.job_service import start_generation_job, get_job
from backend.pdf_service import (
    compute_auto_shrink_fontsize,
    generate_sample_preview,
    inspect_pdf,
    stamp_pdf,
)
from backend.sample_service import generate_sample_assets


def run_all_tests():
    print("=== Testing DocuNext Backend ===")

    test_dir = BASE_DIR / "test_scratch"
    test_dir.mkdir(parents=True, exist_ok=True)

    # 1. Generate Sample Assets
    print("1. Generating Sample Assets...")
    assets = generate_sample_assets(test_dir)
    assert Path(assets["flat_pdf"]).exists(), "Flat PDF template was not created."
    assert Path(assets["acro_pdf"]).exists(), "AcroForm PDF template was not created."
    assert Path(assets["excel"]).exists(), "Excel spreadsheet was not created."
    print("   [PASS] Sample assets created.")

    # 2. Test PDF Inspection
    print("2. Inspecting Flat PDF...")
    flat_info = inspect_pdf(assets["flat_pdf"])
    assert flat_info["page_count"] == 1
    assert flat_info["width"] == 792.0
    assert flat_info["height"] == 612.0
    assert not flat_info["has_acroform"]
    print(f"   [PASS] Flat PDF: {flat_info['width']}x{flat_info['height']} pts, AcroForm: {flat_info['has_acroform']}")

    print("3. Inspecting AcroForm PDF...")
    acro_info = inspect_pdf(assets["acro_pdf"])
    assert acro_info["has_acroform"]
    field_names = [f["name"] for f in acro_info["acroform_fields"]]
    print(f"   [PASS] AcroForm detected fields: {field_names}")
    assert "recipient_name" in field_names
    assert "course_title" in field_names

    # 4. Test Spreadsheet Parsing
    print("4. Parsing Excel Spreadsheet...")
    excel_info = parse_spreadsheet(assets["excel"])
    print(f"   [PASS] Headers: {excel_info['headers']}")
    print(f"   [PASS] Rows: {excel_info['total_rows']}")
    assert excel_info["total_rows"] == 10
    assert "Recipient Name" in excel_info["headers"]
    assert "Course Title" in excel_info["headers"]

    # 5. Test Auto Matching
    print("5. Testing Auto Matching...")
    matches = auto_match_headers(
        template_fields=["recipient_name", "course_title", "issue_date", "certificate_id"],
        spreadsheet_headers=excel_info["headers"],
    )
    for m in matches:
        print(f"   Match: {m['field_name']} -> {m['matched_header']} (score: {m['confidence']})")
        assert m["matched_header"] is not None

    # 6. Test Auto-Shrink Font Fitting
    print("6. Testing Auto-Shrink...")
    short_text = "Jane Doe"
    long_text = "Prof. Dr. Alexandrina Elizabeth Montgomery-Hetherington III, Esq."
    size_short = compute_auto_shrink_fontsize(short_text, "helv", target_width=300, target_height=50, desired_size=24)
    size_long = compute_auto_shrink_fontsize(long_text, "helv", target_width=300, target_height=50, desired_size=24)
    print(f"   [PASS] Font sizes: Short={size_short}pt, Long={size_long}pt")
    assert size_short == 24.0
    assert size_long < 24.0

    # 7. Test Text Stamping on Flat PDF
    print("7. Testing Stamping Flat PDF...")
    test_fields = [
        {
            "id": "f1",
            "binding": "{{Recipient Name}}",
            "x": 0.15,
            "y": 0.38,
            "width": 0.70,
            "height": 0.08,
            "is_normalized": True,
            "font_family": "serif",
            "font_size": 28,
            "auto_shrink": True,
            "bold": True,
            "italic": False,
            "color": "#1E3A8A",
            "align": "center",
        },
        {
            "id": "f2",
            "binding": "{{Course Title}}",
            "x": 0.20,
            "y": 0.58,
            "width": 0.60,
            "height": 0.06,
            "is_normalized": True,
            "font_family": "sans-serif",
            "font_size": 18,
            "auto_shrink": True,
            "bold": True,
            "italic": True,
            "color": "#111827",
            "align": "center",
        },
        {
            "id": "f3",
            "binding": "{{Completion Date}}",
            "x": 0.15,
            "y": 0.79,
            "width": 0.23,
            "height": 0.04,
            "is_normalized": True,
            "font_family": "sans-serif",
            "font_size": 12,
            "auto_shrink": False,
            "bold": False,
            "italic": False,
            "color": "#374151",
            "align": "center",
        },
    ]
    sample_row = excel_info["preview_rows"][0]
    out_pdf_path = test_dir / "test_output_cert.pdf"
    _, warnings = stamp_pdf(
        template_path=assets["flat_pdf"],
        fields=test_fields,
        row_data=sample_row,
        output_path=str(out_pdf_path),
    )
    assert out_pdf_path.exists()
    assert out_pdf_path.stat().st_size > 1000
    print(f"   [PASS] Stamped PDF saved to {out_pdf_path.name} ({out_pdf_path.stat().st_size} bytes)")

    # 8. Test Live Preview Generation (base64 image)
    print("8. Testing WYSIWYG Sample Preview Generation...")
    preview_data_uri, p_warnings = generate_sample_preview(
        template_path=assets["flat_pdf"],
        fields=test_fields,
        row_data=sample_row,
    )
    assert preview_data_uri.startswith("data:image/png;base64,")
    print(f"   [PASS] Preview generated successfully (URI length: {len(preview_data_uri)})")

    # 9. Test Filename Pattern Generation
    print("9. Testing Filename Pattern...")
    existing = set()
    fn1 = build_filename("{Recipient Name}_{Course Title}", sample_row, 0, existing)
    fn2 = build_filename("{Recipient Name}_{Course Title}", sample_row, 1, existing)
    print(f"   [PASS] Filename 1: {fn1}")
    print(f"   [PASS] Filename 2 (duplicate handling): {fn2}")
    assert fn1.endswith(".pdf")
    assert fn2.endswith(".pdf")
    assert fn1 != fn2

    # 10. Test Bulk Generation Job
    print("10. Testing Bulk Generation Job Worker...")
    job_id = start_generation_job(
        template_path=assets["flat_pdf"],
        fields=test_fields,
        rows=excel_info["preview_rows"][:5],
        filename_pattern="{Recipient Name}_{Certificate ID}.pdf",
        output_base_dir=str(test_dir / "output"),
    )
    import time
    for _ in range(30):
        job = get_job(job_id)
        if job["status"] in ["completed", "failed"]:
            break
        time.sleep(0.1)

    assert job["status"] == "completed"
    assert job["processed_rows"] == 5
    assert job["zip_path"] is not None
    assert Path(job["zip_path"]).exists()
    print(f"   [PASS] Job {job_id} completed: 5/5 rows processed, ZIP created at {Path(job['zip_path']).name}")

    print("\nALL BACKEND TESTS PASSED SUCCESSFULLY! [OK]")


if __name__ == "__main__":
    run_all_tests()
