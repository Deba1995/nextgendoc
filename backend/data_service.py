import csv
import difflib
import io
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import openpyxl


def clean_cell_value(val: Any) -> str:
    """Convert any cell value to a clean string representation."""
    if val is None:
        return ""
    if isinstance(val, float):
        # Format whole floats as integers e.g. 100.0 -> 100
        if val.is_integer():
            return str(int(val))
    return str(val).strip()


def parse_spreadsheet(file_path: str, max_preview_rows: int = 10) -> Dict[str, Any]:
    """
    Parses an .xlsx or .csv file.
    Returns:
        {
            "filename": str,
            "headers": list[str],
            "total_rows": int,
            "preview_rows": list[dict[str, str]],
            "all_rows": list[dict[str, str]]
        }
    """
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext == ".csv":
        headers, rows = _parse_csv(path)
    elif ext in [".xlsx", ".xlsm", ".xltx"]:
        headers, rows = _parse_excel(path)
    else:
        raise ValueError(f"Unsupported spreadsheet format '{ext}'. Please upload an .xlsx or .csv file.")

    return {
        "filename": path.name,
        "headers": headers,
        "total_rows": len(rows),
        "preview_rows": rows[:max_preview_rows],
        "all_rows": rows,
    }


def _parse_csv(path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    """Parse CSV with encoding fallback and dialect sniffing."""
    encodings = ["utf-8-sig", "utf-8", "latin-1", "cp1252"]
    content = None
    for enc in encodings:
        try:
            with open(path, "r", encoding=enc) as f:
                content = f.read()
            break
        except UnicodeDecodeError:
            continue

    if content is None:
        raise ValueError("Could not decode CSV file with supported encodings (UTF-8, Latin-1, CP1252).")

    f = io.StringIO(content)
    try:
        sample = content[:4096]
        dialect = csv.Sniffer().sniff(sample)
    except Exception:
        dialect = csv.excel

    f.seek(0)
    reader = csv.reader(f, dialect=dialect)
    try:
        raw_headers = next(reader)
    except StopIteration:
        return [], []

    headers = _clean_headers(raw_headers)
    rows = []
    for raw_row in reader:
        row_dict = {}
        for i, header in enumerate(headers):
            val = raw_row[i] if i < len(raw_row) else ""
            row_dict[header] = clean_cell_value(val)
        rows.append(row_dict)

    return headers, rows


def _parse_excel(path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    """Parse Excel using openpyxl (read_only for high performance)."""
    wb = openpyxl.load_workbook(filename=str(path), read_only=True, data_only=True)
    sheet = wb.active
    if sheet is None:
        wb.close()
        return [], []

    rows_iter = sheet.iter_rows(values_only=True)
    try:
        raw_headers = next(rows_iter)
    except StopIteration:
        wb.close()
        return [], []

    headers = _clean_headers(list(raw_headers) if raw_headers else [])
    rows = []
    for raw_row in rows_iter:
        # Check if entire row is empty
        if not raw_row or all(v is None or str(v).strip() == "" for v in raw_row):
            continue
        row_dict = {}
        for i, header in enumerate(headers):
            val = raw_row[i] if i < len(raw_row) else ""
            row_dict[header] = clean_cell_value(val)
        rows.append(row_dict)

    wb.close()
    return headers, rows


def _clean_headers(raw_headers: List[Any]) -> List[str]:
    """Clean and deduplicate headers, handling empty or special characters."""
    headers = []
    seen = {}
    for idx, h in enumerate(raw_headers):
        clean_name = str(h).strip() if h is not None else ""
        if not clean_name:
            clean_name = f"Column_{idx + 1}"
        
        # Deduplicate if exact same header name occurs multiple times
        if clean_name in seen:
            seen[clean_name] += 1
            final_name = f"{clean_name}_{seen[clean_name]}"
        else:
            seen[clean_name] = 1
            final_name = clean_name
        headers.append(final_name)
    return headers


def normalize_string_for_matching(text: str) -> str:
    """Normalize text for fuzzy auto-matching."""
    # Lowercase and keep only alphanumeric chars
    return re.sub(r"[^a-z0-9]", "", text.lower())


def auto_match_headers(
    template_fields: List[str], spreadsheet_headers: List[str], threshold: float = 0.55
) -> List[Dict[str, Any]]:
    """
    Match template/AcroForm fields to spreadsheet column headers.
    Returns:
        list of {
            "field_name": str,
            "matched_header": Optional[str],
            "confidence": float,
            "candidates": list[{"header": str, "score": float}]
        }
    """
    results = []
    used_headers = set()

    # Pre-normalize spreadsheet headers
    normalized_headers = [(h, normalize_string_for_matching(h)) for h in spreadsheet_headers]

    for field in template_fields:
        norm_field = normalize_string_for_matching(field)
        field_tokens = set(t for t in re.findall(r"[a-z0-9]+", field.lower()) if len(t) >= 2)
        best_match = None
        best_score = 0.0
        candidates = []

        for original_h, norm_h in normalized_headers:
            if not norm_h or not norm_field:
                continue

            score = 0.0
            header_tokens = set(t for t in re.findall(r"[a-z0-9]+", original_h.lower()) if len(t) >= 2)
            common_tokens = field_tokens.intersection(header_tokens)

            if norm_field == norm_h:
                score = 1.0
            elif norm_field in norm_h or norm_h in norm_field:
                # High score if one is a substring of the other (e.g. 'name' in 'recipient_name')
                score = 0.85
            elif common_tokens:
                # If there are matching semantic words (e.g. 'date' in 'issue_date' and 'Completion Date')
                overlap_ratio = len(common_tokens) / min(len(field_tokens), len(header_tokens))
                score = 0.65 + (0.25 * overlap_ratio)
            else:
                score = difflib.SequenceMatcher(None, norm_field, norm_h).ratio()

            candidates.append({"header": original_h, "score": round(score, 3)})

            if score > best_score:
                best_score = score
                best_match = original_h

        candidates.sort(key=lambda c: c["score"], reverse=True)

        matched_header = best_match if best_score >= threshold else None
        results.append({
            "field_name": field,
            "matched_header": matched_header,
            "confidence": round(best_score, 3),
            "candidates": candidates[:3],
        })

    return results


def interpolate_text(template_text: str, row_data: Dict[str, str]) -> Tuple[str, List[str]]:
    """
    Replaces {{Column Name}} or {Column Name} in template_text with values from row_data.
    Also handles when template_text is just a plain column name.
    Returns:
        (resolved_text, list_of_warnings)
    """
    warnings = []
    if not template_text:
        return "", warnings

    # If template_text matches a column name directly without curly braces
    if template_text in row_data:
        val = row_data.get(template_text, "")
        if val == "":
            warnings.append(f"Column '{template_text}' is blank.")
        return val, warnings

    # Match {{Key}} or {Key}
    def replacer(match):
        key = match.group(1).strip()
        if key in row_data:
            val = row_data[key]
            if val == "":
                warnings.append(f"Column '{key}' is blank.")
            return val
        else:
            # Case-insensitive / normalized lookup fallback
            norm_key = normalize_string_for_matching(key)
            for k, v in row_data.items():
                if normalize_string_for_matching(k) == norm_key:
                    if v == "":
                        warnings.append(f"Column '{k}' is blank.")
                    return v
            warnings.append(f"Column '{key}' not found in spreadsheet.")
            return match.group(0)

    # First replace {{...}}
    res = re.sub(r"\{\{([^}]+)\}\}", replacer, template_text)
    # Then replace single {...} if not already processed
    res = re.sub(r"\{([^{}]+)\}", replacer, res)

    return res, warnings


def build_filename(
    pattern: str, row_data: Dict[str, str], row_index: int, existing_names: set
) -> str:
    """
    Builds a sanitized filename from a pattern like '{Name}_{Course}.pdf'.
    Falls back to row number on collision or blank output.
    """
    if not pattern:
        pattern = "Certificate_{Row}"

    # Replace placeholders
    rendered, _ = interpolate_text(pattern, row_data)
    rendered = rendered.replace("{Row}", str(row_index + 1))
    rendered = rendered.replace("{{Row}}", str(row_index + 1))

    # Strip any trailing or duplicate extension
    base = re.sub(r"\.pdf$", "", rendered, flags=re.IGNORECASE).strip()

    # Sanitize invalid filename characters on Windows/Linux (\ / : * ? " < > |)
    safe_base = re.sub(r'[\\/*?:"<>|]', "_", base).strip()
    if not safe_base:
        safe_base = f"Certificate_{row_index + 1}"

    candidate = f"{safe_base}.pdf"
    counter = 1
    while candidate.lower() in existing_names:
        candidate = f"{safe_base}_{counter}.pdf"
        counter += 1

    existing_names.add(candidate.lower())
    return candidate
