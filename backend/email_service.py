import email
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
from pathlib import Path
import re
import smtplib
import ssl
import threading
import time
from typing import Any, Dict, List, Optional
import uuid

logger = logging.getLogger("docunext.email")

# In-memory store for active and completed email jobs
EMAIL_JOBS: Dict[str, Dict[str, Any]] = {}


def verify_smtp_connection(
    host: str,
    port: int,
    use_tls: bool,
    use_ssl: bool,
    username: str,
    password: str,
    timeout: int = 12,
) -> Dict[str, Any]:
    """
    Attempts to connect and authenticate with the specified SMTP server.
    Returns a dict with success boolean and detailed diagnostic message.
    """
    try:
        if use_ssl:
            context = ssl.create_default_context()
            server = smtplib.SMTP_SSL(host, port, context=context, timeout=timeout)
        else:
            server = smtplib.SMTP(host, port, timeout=timeout)
            server.ehlo()
            if use_tls:
                context = ssl.create_default_context()
                server.starttls(context=context)
                server.ehlo()

        if username and password:
            server.login(username, password)

        server.quit()
        return {"success": True, "message": f"Successfully connected and authenticated to {host}:{port}!"}
    except smtplib.SMTPAuthenticationError:
        return {
            "success": False,
            "message": "Authentication failed. If using Gmail, make sure to generate and use a 16-character Google App Password (not your regular account password).",
            "error_code": "AUTH_FAILED",
        }
    except Exception as e:
        return {"success": False, "message": f"Connection error: {str(e)}", "error_code": "CONNECTION_FAILED"}


def interpolate_template(template_str: str, row_data: Dict[str, Any]) -> str:
    """
    Replaces {{Column Name}} placeholders in subject or body with row values.
    """
    if not template_str:
        return ""

    def replacer(match: re.Match) -> str:
        var_name = match.group(1).strip()
        for k, v in row_data.items():
            if k.strip().lower() == var_name.lower():
                return str(v) if v is not None else ""
        return match.group(0)

    return re.sub(r"\{\{([^}]+)\}\}", replacer, template_str)


def send_single_email(
    server: smtplib.SMTP,
    sender_email: str,
    sender_name: str,
    recipient_email: str,
    subject: str,
    body_text: str,
    attachment_path: Optional[str] = None,
    is_html: bool = False,
) -> None:
    """
    Sends one MIME email with optional PDF attachment over an active SMTP connection.
    """
    msg = MIMEMultipart("mixed")
    if sender_name:
        msg["From"] = f"{sender_name} <{sender_email}>"
    else:
        msg["From"] = sender_email
    msg["To"] = recipient_email
    msg["Subject"] = subject

    body_subtype = "html" if is_html or "<html" in body_text.lower() or "<p>" in body_text.lower() else "plain"
    msg.attach(MIMEText(body_text, body_subtype, "utf-8"))

    if attachment_path and Path(attachment_path).exists():
        p = Path(attachment_path)
        with open(p, "rb") as f:
            part = MIMEApplication(f.read(), Name=p.name)
        part["Content-Disposition"] = f'attachment; filename="{p.name}"'
        msg.attach(part)

    server.send_message(msg)


def run_email_batch_worker(
    job_id: str,
    smtp_config: Dict[str, Any],
    email_column: str,
    subject_template: str,
    body_template: str,
    rows: List[Dict[str, Any]],
    generated_files: List[Dict[str, Any]],
    test_mode: bool = False,
    test_email: str = "",
    delay_seconds: float = 1.2,
) -> None:
    """
    Background worker thread to dispatch bulk emails with throttling and Test Mode support.
    """
    job = EMAIL_JOBS[job_id]
    job["status"] = "running"
    job["start_time"] = time.time()

    host = smtp_config.get("host", "").strip()
    port = int(smtp_config.get("port", 587))
    use_tls = smtp_config.get("use_tls", True)
    use_ssl = smtp_config.get("use_ssl", False)
    username = smtp_config.get("username", "").strip()
    password = smtp_config.get("password", "").strip()
    sender_email = smtp_config.get("sender_email", username).strip()
    sender_name = smtp_config.get("sender_name", "DocuNext").strip()

    file_map = {}
    for i, f in enumerate(generated_files):
        p = f.get("path")
        file_map[i] = p
        if "row_index" in f and isinstance(f["row_index"], int):
            file_map[f["row_index"] - 1] = p

    server = None
    try:
        if use_ssl:
            context = ssl.create_default_context()
            server = smtplib.SMTP_SSL(host, port, context=context, timeout=20)
        else:
            server = smtplib.SMTP(host, port, timeout=20)
            server.ehlo()
            if use_tls:
                context = ssl.create_default_context()
                server.starttls(context=context)
                server.ehlo()

        if username and password:
            server.login(username, password)

        for idx, row in enumerate(rows):
            if job.get("cancelled", False):
                job["status"] = "cancelled"
                break

            actual_recipient = str(row.get(email_column, "")).strip()

            if test_mode:
                target_email = test_email.strip()
                subject_prefix = f"[TEST MODE - For: {actual_recipient or 'Row ' + str(idx + 1)}] "
            else:
                target_email = actual_recipient
                subject_prefix = ""

            if not target_email or "@" not in target_email:
                job["processed"] += 1
                job["failed"] += 1
                job["logs"].append({
                    "index": idx,
                    "recipient": actual_recipient or f"Row {idx + 1}",
                    "target_email": target_email or "(empty)",
                    "status": "skipped",
                    "error": "Missing or invalid email address",
                    "timestamp": time.strftime("%H:%M:%S"),
                })
                continue

            resolved_subject = subject_prefix + interpolate_template(subject_template, row)
            resolved_body = interpolate_template(body_template, row)
            attachment_file = file_map.get(idx)

            try:
                send_single_email(
                    server=server,
                    sender_email=sender_email,
                    sender_name=sender_name,
                    recipient_email=target_email,
                    subject=resolved_subject,
                    body_text=resolved_body,
                    attachment_path=attachment_file,
                )
                job["processed"] += 1
                job["succeeded"] += 1
                job["logs"].append({
                    "index": idx,
                    "recipient": actual_recipient or f"Row {idx + 1}",
                    "target_email": target_email,
                    "status": "sent",
                    "error": None,
                    "timestamp": time.strftime("%H:%M:%S"),
                })
            except Exception as send_err:
                logger.error(f"Failed to send email to {target_email}: {send_err}")
                job["processed"] += 1
                job["failed"] += 1
                job["logs"].append({
                    "index": idx,
                    "recipient": actual_recipient or f"Row {idx + 1}",
                    "target_email": target_email,
                    "status": "failed",
                    "error": str(send_err),
                    "timestamp": time.strftime("%H:%M:%S"),
                })

            if delay_seconds > 0 and idx < len(rows) - 1:
                time.sleep(delay_seconds)

        if job["status"] != "cancelled":
            job["status"] = "completed"

    except Exception as conn_err:
        logger.error(f"SMTP Batch failed: {conn_err}")
        job["status"] = "failed"
        job["error"] = str(conn_err)
    finally:
        if server:
            try:
                server.quit()
            except Exception:
                pass
        job["end_time"] = time.time()


def start_email_job(
    smtp_config: Dict[str, Any],
    email_column: str,
    subject_template: str,
    body_template: str,
    rows: List[Dict[str, Any]],
    generated_files: List[Dict[str, Any]],
    test_mode: bool = False,
    test_email: str = "",
    delay_seconds: float = 1.2,
) -> str:
    """
    Initializes an email dispatch job and launches the worker thread.
    Returns unique job_id.
    """
    job_id = str(uuid.uuid4())[:8]
    EMAIL_JOBS[job_id] = {
        "id": job_id,
        "status": "queued",
        "total": len(rows),
        "processed": 0,
        "succeeded": 0,
        "failed": 0,
        "cancelled": False,
        "test_mode": test_mode,
        "test_email": test_email,
        "logs": [],
        "created_at": time.time(),
    }

    t = threading.Thread(
        target=run_email_batch_worker,
        kwargs={
            "job_id": job_id,
            "smtp_config": smtp_config,
            "email_column": email_column,
            "subject_template": subject_template,
            "body_template": body_template,
            "rows": rows,
            "generated_files": generated_files,
            "test_mode": test_mode,
            "test_email": test_email,
            "delay_seconds": delay_seconds,
        },
        daemon=True,
    )
    t.start()

    return job_id


def get_email_job(job_id: str) -> Optional[Dict[str, Any]]:
    return EMAIL_JOBS.get(job_id)


def cancel_email_job(job_id: str) -> bool:
    job = EMAIL_JOBS.get(job_id)
    if job and job["status"] in ("queued", "running"):
        job["cancelled"] = True
        return True
    return False
