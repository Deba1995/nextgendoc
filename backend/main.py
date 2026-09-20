import json
import os
import re
import shutil
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .data_service import auto_match_headers, parse_spreadsheet
from .job_service import get_job, list_jobs, start_generation_job
from .pdf_service import generate_sample_preview, inspect_pdf, render_page_to_base64
from .sample_service import generate_sample_assets

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
TEMPLATES_DIR = UPLOAD_DIR / "templates"
DATA_DIR = UPLOAD_DIR / "data"
PROJECTS_DIR = BASE_DIR / "projects"
OUTPUT_DIR = BASE_DIR / "output"
FRONTEND_DIR = BASE_DIR / "frontend"
SAMPLE_DIR = BASE_DIR / "samples"

for d in [TEMPLATES_DIR, DATA_DIR, PROJECTS_DIR, OUTPUT_DIR, SAMPLE_DIR]:
    d.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="DocuNext - Offline Certificate Generator", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# In-memory store for uploaded sessions
SESSION_TEMPLATES: Dict[str, str] = {}
SESSION_DATA: Dict[str, Dict[str, Any]] = {}


class AutoMatchRequest(BaseModel):
    template_fields: List[str]
    spreadsheet_headers: List[str]


class PreviewRequest(BaseModel):
    template_id: str
    fields: List[Dict[str, Any]]
    row_data: Dict[str, str]
    page_num: Optional[int] = 0


class SaveProjectRequest(BaseModel):
    name: str
    project_data: Dict[str, Any]


class GenerateRequest(BaseModel):
    template_id: str
    data_id: str
    fields: List[Dict[str, Any]]
    filename_pattern: Optional[str] = "{Recipient Name}_{Course Title}.pdf"
    page_num: Optional[int] = 0
    row_start: Optional[int] = 0
    row_limit: Optional[int] = None


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "app": "DocuNext", "offline": True}


@app.post("/api/upload/template")
async def upload_template(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF templates are supported.")

    file_id = f"tpl_{uuid.uuid4().hex[:10]}"
    safe_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", file.filename)
    dest_path = TEMPLATES_DIR / f"{file_id}_{safe_name}"

    with open(dest_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        info = inspect_pdf(str(dest_path))
        preview_img = render_page_to_base64(str(dest_path), page_num=0)
    except Exception as e:
        if dest_path.exists():
            dest_path.unlink()
        raise HTTPException(status_code=400, detail=f"Failed to inspect PDF template: {str(e)}")

    SESSION_TEMPLATES[file_id] = str(dest_path)

    return {
        "template_id": file_id,
        "filename": file.filename,
        "page_count": info["page_count"],
        "width": info["width"],
        "height": info["height"],
        "has_acroform": info["has_acroform"],
        "acroform_fields": info["acroform_fields"],
        "preview_image": preview_img,
    }


@app.post("/api/upload/data")
async def upload_data(file: UploadFile = File(...)):
    ext = Path(file.filename).suffix.lower()
    if ext not in [".xlsx", ".xls", ".csv"]:
        raise HTTPException(status_code=400, detail="Only .xlsx or .csv files are supported.")

    data_id = f"dat_{uuid.uuid4().hex[:10]}"
    safe_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", file.filename)
    dest_path = DATA_DIR / f"{data_id}_{safe_name}"

    with open(dest_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        parsed = parse_spreadsheet(str(dest_path), max_preview_rows=10)
    except Exception as e:
        if dest_path.exists():
            dest_path.unlink()
        raise HTTPException(status_code=400, detail=f"Failed to parse spreadsheet: {str(e)}")

    SESSION_DATA[data_id] = parsed
    SESSION_DATA[data_id]["file_path"] = str(dest_path)

    return {
        "data_id": data_id,
        "filename": file.filename,
        "headers": parsed["headers"],
        "total_rows": parsed["total_rows"],
        "preview_rows": parsed["preview_rows"],
    }


@app.post("/api/automatch")
async def automatch(req: AutoMatchRequest):
    matches = auto_match_headers(req.template_fields, req.spreadsheet_headers)
    return {"matches": matches}


@app.post("/api/preview/sample")
async def preview_sample(req: PreviewRequest):
    template_path = SESSION_TEMPLATES.get(req.template_id)
    if not template_path or not Path(template_path).exists():
        raise HTTPException(status_code=404, detail="Template not found. Please upload again.")

    try:
        data_uri, warnings = generate_sample_preview(
            template_path=template_path,
            fields=req.fields,
            row_data=req.row_data,
            page_num=req.page_num or 0,
        )
        return {"preview_image": data_uri, "warnings": warnings}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preview generation failed: {str(e)}")


@app.post("/api/projects/save")
async def save_project(req: SaveProjectRequest):
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", req.name.strip())
    if not safe_name:
        safe_name = "certificate_project"
    project_file = PROJECTS_DIR / f"{safe_name}.json"

    with open(project_file, "w", encoding="utf-8") as f:
        json.dump(req.project_data, f, indent=2)

    return {"message": "Project saved successfully", "name": safe_name}


@app.get("/api/projects/list")
async def list_saved_projects():
    projects = []
    for f in PROJECTS_DIR.glob("*.json"):
        try:
            with open(f, "r", encoding="utf-8") as pf:
                data = json.load(pf)
            projects.append({
                "name": f.stem,
                "modified": f.stat().st_mtime,
                "fields_count": len(data.get("fields", [])),
                "filename_pattern": data.get("filename_pattern", ""),
            })
        except Exception:
            continue
    projects.sort(key=lambda x: x["modified"], reverse=True)
    return {"projects": projects}


@app.get("/api/projects/{name}")
async def load_project(name: str):
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", name)
    project_file = PROJECTS_DIR / f"{safe_name}.json"
    if not project_file.exists():
        raise HTTPException(status_code=404, detail="Project not found.")

    with open(project_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {"name": safe_name, "project_data": data}


@app.post("/api/generate")
async def generate_certificates(req: GenerateRequest):
    template_path = SESSION_TEMPLATES.get(req.template_id)
    if not template_path or not Path(template_path).exists():
        raise HTTPException(status_code=404, detail="Template not found. Please upload again.")

    data_info = SESSION_DATA.get(req.data_id)
    if not data_info:
        raise HTTPException(status_code=404, detail="Spreadsheet data not found. Please upload again.")

    all_rows = data_info.get("all_rows", [])
    if not all_rows:
        raise HTTPException(status_code=400, detail="Spreadsheet contains no data rows.")

    start = max(0, req.row_start or 0)
    if req.row_limit is not None and req.row_limit > 0:
        target_rows = all_rows[start : start + req.row_limit]
    else:
        target_rows = all_rows[start:]

    if not target_rows:
        raise HTTPException(status_code=400, detail="No spreadsheet rows selected for generation.")

    job_id = start_generation_job(
        template_path=template_path,
        fields=req.fields,
        rows=target_rows,
        filename_pattern=req.filename_pattern or "{Recipient Name}.pdf",
        output_base_dir=str(OUTPUT_DIR),
        page_num=req.page_num or 0,
    )

    return {"job_id": job_id, "status": "pending", "total_rows": len(target_rows)}


@app.get("/api/jobs/{job_id}/status")
async def job_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


@app.get("/api/jobs/{job_id}/files")
async def job_files(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return {"files": job.get("generated_files", []), "zip_available": bool(job.get("zip_path"))}


@app.get("/api/jobs/{job_id}/download/{filename}")
async def download_file(job_id: str, filename: str):
    safe_fn = Path(filename).name
    file_path = OUTPUT_DIR / job_id / safe_fn
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=safe_fn,
    )


@app.get("/api/jobs/{job_id}/download-zip")
async def download_zip(job_id: str):
    job = get_job(job_id)
    if not job or not job.get("zip_path"):
        raise HTTPException(status_code=404, detail="ZIP file not found.")
    zip_path = Path(job["zip_path"])
    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="ZIP file does not exist on disk.")
    return FileResponse(
        path=str(zip_path),
        media_type="application/zip",
        filename=f"certificates_{job_id}.zip",
    )


@app.post("/api/sample/load")
async def load_sample(sample_type: str = "flat", row_count: int = 10):
    """
    Generates and registers sample template & data for immediate testing.
    sample_type: 'flat' or 'acroform'
    row_count: number of rows (e.g. 10, 50, 100, 500, 1000)
    """
    assets = generate_sample_assets(SAMPLE_DIR, row_count=row_count)

    # 1. Register Template
    tpl_file = assets["flat_pdf"] if sample_type != "acroform" else assets["acro_pdf"]
    file_id = f"tpl_sample_{sample_type}"
    SESSION_TEMPLATES[file_id] = tpl_file

    info = inspect_pdf(tpl_file)
    preview_img = render_page_to_base64(tpl_file, page_num=0)

    # 2. Register Spreadsheet
    data_file = assets["excel"]
    data_id = f"dat_sample_{row_count}"
    parsed = parse_spreadsheet(data_file, max_preview_rows=10)
    SESSION_DATA[data_id] = parsed
    SESSION_DATA[data_id]["file_path"] = data_file

    return {
        "template": {
            "template_id": file_id,
            "filename": Path(tpl_file).name,
            "page_count": info["page_count"],
            "width": info["width"],
            "height": info["height"],
            "has_acroform": info["has_acroform"],
            "acroform_fields": info["acroform_fields"],
            "preview_image": preview_img,
        },
        "data": {
            "data_id": data_id,
            "filename": f"sample_data_{row_count}.xlsx",
            "headers": parsed["headers"],
            "total_rows": parsed["total_rows"],
            "preview_rows": parsed["preview_rows"],
        },
    }


# Mount frontend static files
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
