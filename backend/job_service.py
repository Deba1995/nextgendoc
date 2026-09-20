import concurrent.futures
import json
import logging
import threading
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

from .data_service import build_filename
from .pdf_service import stamp_pdf

logger = logging.getLogger(__name__)

# In-memory job store
JOBS: Dict[str, Dict[str, Any]] = {}
JOB_LOCK = threading.Lock()
THREAD_POOL = concurrent.futures.ThreadPoolExecutor(max_workers=4)


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    with JOB_LOCK:
        return JOBS.get(job_id)


def list_jobs() -> List[Dict[str, Any]]:
    with JOB_LOCK:
        return list(JOBS.values())


def start_generation_job(
    template_path: str,
    fields: List[Dict[str, Any]],
    rows: List[Dict[str, str]],
    filename_pattern: str,
    output_base_dir: str = "output",
    page_num: int = 0,
) -> str:
    """
    Spawns a background thread to generate PDFs for all rows.
    Returns:
        job_id (str)
    """
    job_id = str(uuid.uuid4())[:8]
    job_dir = Path(output_base_dir) / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    job_data = {
        "id": job_id,
        "status": "pending",
        "total_rows": len(rows),
        "processed_rows": 0,
        "percent": 0,
        "failed_rows": 0,
        "warnings": [],
        "error": None,
        "start_time": time.time(),
        "end_time": None,
        "output_dir": str(job_dir.resolve()),
        "zip_path": None,
        "generated_files": [],
    }

    with JOB_LOCK:
        JOBS[job_id] = job_data

    # Submit to thread pool
    THREAD_POOL.submit(
        _run_generation_worker,
        job_id,
        template_path,
        fields,
        rows,
        filename_pattern,
        job_dir,
        page_num,
    )

    return job_id


def _run_generation_worker(
    job_id: str,
    template_path: str,
    fields: List[Dict[str, Any]],
    rows: List[Dict[str, str]],
    filename_pattern: str,
    job_dir: Path,
    page_num: int,
):
    with JOB_LOCK:
        if job_id not in JOBS:
            return
        JOBS[job_id]["status"] = "running"

    existing_filenames = set()
    generated_files = []
    warnings_list = []
    failed_rows = 0

    try:
        for idx, row in enumerate(rows):
            filename = build_filename(filename_pattern, row, idx, existing_filenames)
            out_pdf_path = job_dir / filename

            try:
                _, row_warnings = stamp_pdf(
                    template_path=template_path,
                    fields=fields,
                    row_data=row,
                    output_path=str(out_pdf_path),
                    page_num=page_num,
                )
                for w in row_warnings:
                    if len(warnings_list) < 200:
                        warnings_list.append(f"Row {idx + 1} ({filename}): {w}")

                generated_files.append({
                    "filename": filename,
                    "row_index": idx + 1,
                    "size_bytes": out_pdf_path.stat().st_size if out_pdf_path.exists() else 0,
                })
            except Exception as e:
                failed_rows += 1
                if len(warnings_list) < 200:
                    warnings_list.append(f"Row {idx + 1} Failed: {str(e)}")
                logger.exception(f"Failed stamping row {idx + 1}")

            # Update progress
            with JOB_LOCK:
                if job_id in JOBS:
                    processed = idx + 1
                    JOBS[job_id]["processed_rows"] = processed
                    JOBS[job_id]["failed_rows"] = failed_rows
                    JOBS[job_id]["percent"] = int((processed / len(rows)) * 100)
                    JOBS[job_id]["warnings"] = warnings_list

        # Create ZIP archive
        zip_filename = f"certificates_{job_id}.zip"
        zip_path = job_dir / zip_filename
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for gf in generated_files:
                f_path = job_dir / gf["filename"]
                if f_path.exists():
                    zf.write(f_path, arcname=gf["filename"])

        with JOB_LOCK:
            if job_id in JOBS:
                JOBS[job_id]["status"] = "completed"
                JOBS[job_id]["percent"] = 100
                JOBS[job_id]["end_time"] = time.time()
                JOBS[job_id]["zip_path"] = str(zip_path.resolve())
                JOBS[job_id]["generated_files"] = generated_files

    except Exception as e:
        logger.exception(f"Job {job_id} encountered fatal error")
        with JOB_LOCK:
            if job_id in JOBS:
                JOBS[job_id]["status"] = "failed"
                JOBS[job_id]["error"] = str(e)
                JOBS[job_id]["end_time"] = time.time()
