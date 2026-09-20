import base64
import io
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import pymupdf as fitz


# Font mapping for standard PDF fonts (fully offline & built into PyMuPDF/PDF standard)
FONT_MAP = {
    ("sans-serif", False, False): "helv",
    ("sans-serif", True, False): "hebo",
    ("sans-serif", False, True): "heit",
    ("sans-serif", True, True): "hebi",

    ("serif", False, False): "tiro",
    ("serif", True, False): "tibo",
    ("serif", False, True): "tiit",
    ("serif", True, True): "tibi",

    ("monospace", False, False): "cour",
    ("monospace", True, False): "cobo",
    ("monospace", False, True): "coit",
    ("monospace", True, True): "cobi",
}

ALIGN_MAP = {
    "left": fitz.TEXT_ALIGN_LEFT,
    "center": fitz.TEXT_ALIGN_CENTER,
    "right": fitz.TEXT_ALIGN_RIGHT,
    "justify": fitz.TEXT_ALIGN_JUSTIFY,
}


def hex_to_rgb(hex_code: str) -> Tuple[float, float, float]:
    """Convert hex color string (e.g. #1E3A8A or 1E3A8A) to float RGB (0.0 - 1.0)."""
    if not hex_code:
        return (0.0, 0.0, 0.0)
    hex_code = hex_code.lstrip("#")
    if len(hex_code) == 3:
        hex_code = "".join(c * 2 for c in hex_code)
    if len(hex_code) != 6:
        return (0.0, 0.0, 0.0)
    try:
        r = int(hex_code[0:2], 16) / 255.0
        g = int(hex_code[2:4], 16) / 255.0
        b = int(hex_code[4:6], 16) / 255.0
        return (r, g, b)
    except ValueError:
        return (0.0, 0.0, 0.0)


def get_font_name(family: str, bold: bool = False, italic: bool = False) -> str:
    """Resolve standard PDF font identifier."""
    family_key = family.lower() if family else "sans-serif"
    if any(k in family_key for k in ["script", "cursive", "brush", "handwriting"]):
        # Map cursive/script to Times Italic for elegant PDF output
        return "tibi" if bold else "tiit"
    elif "serif" in family_key and "sans" not in family_key:
        fam = "serif"
    elif "mono" in family_key or "cour" in family_key:
        fam = "monospace"
    else:
        fam = "sans-serif"

    return FONT_MAP.get((fam, bool(bold), bool(italic)), "helv")


def inspect_pdf(pdf_path: str) -> Dict[str, Any]:
    """
    Inspects PDF template:
    - Page dimensions & count
    - AcroForm fields (names, types, rects)
    """
    doc = fitz.open(pdf_path)
    page_count = len(doc)
    if page_count == 0:
        doc.close()
        raise ValueError("PDF has 0 pages.")

    page = doc[0]
    rect = page.rect
    width = float(rect.width)
    height = float(rect.height)

    fields = []
    # PyMuPDF extracts widgets (AcroForm form fields)
    for widget in page.widgets():
        w_rect = widget.rect
        fields.append({
            "name": widget.field_name or f"Field_{len(fields) + 1}",
            "type": widget.field_type_string,
            "rect": {
                "x0": float(w_rect.x0),
                "y0": float(w_rect.y0),
                "x1": float(w_rect.x1),
                "y1": float(w_rect.y1),
                "width": float(w_rect.width),
                "height": float(w_rect.height),
                # Normalized coordinates (0.0 - 1.0)
                "norm_x": float(w_rect.x0 / width),
                "norm_y": float(w_rect.y0 / height),
                "norm_w": float(w_rect.width / width),
                "norm_h": float(w_rect.height / height),
            },
            "value": widget.field_value or "",
        })

    doc.close()
    return {
        "page_count": page_count,
        "width": width,
        "height": height,
        "has_acroform": len(fields) > 0,
        "acroform_fields": fields,
    }


def render_page_to_png_bytes(pdf_path: str, page_num: int = 0, dpi: int = 150) -> bytes:
    """Render a PDF page to PNG image bytes for canvas background."""
    doc = fitz.open(pdf_path)
    if page_num >= len(doc):
        page_num = 0
    page = doc[page_num]
    pix = page.get_pixmap(dpi=dpi)
    png_bytes = pix.tobytes("png")
    doc.close()
    return png_bytes


def render_page_to_base64(pdf_path: str, page_num: int = 0, dpi: int = 150) -> str:
    """Render a PDF page to base64 data URI."""
    png_bytes = render_page_to_png_bytes(pdf_path, page_num=page_num, dpi=dpi)
    encoded = base64.b64encode(png_bytes).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def compute_auto_shrink_fontsize(
    text: str,
    font_name: str,
    target_width: float,
    target_height: float,
    desired_size: float,
    min_size: float = 6.0,
    padding: float = 4.0,
) -> float:
    """
    Calculates the largest font size (<= desired_size) that fits
    within target_width and target_height.
    """
    if not text:
        return desired_size

    effective_w = max(10.0, target_width - padding * 2)
    effective_h = max(10.0, target_height - padding * 2)

    try:
        font = fitz.Font(font_name)
    except Exception:
        font = fitz.Font("helv")

    lines = text.split("\n")
    current_size = desired_size

    # Check horizontal length for the longest line
    max_line_len = max(font.text_length(line, fontsize=1.0) for line in lines)
    if max_line_len > 0:
        size_for_w = effective_w / max_line_len
        current_size = min(current_size, size_for_w)

    # Check vertical height (line spacing ~ 1.2 * fontsize)
    total_lines = len(lines)
    size_for_h = effective_h / (total_lines * 1.25)
    current_size = min(current_size, size_for_h)

    # Constrain to min_size and desired_size
    current_size = max(min_size, min(desired_size, current_size))
    return round(current_size, 1)


def stamp_pdf(
    template_path: str,
    fields: List[Dict[str, Any]],
    row_data: Dict[str, str],
    output_path: Optional[str] = None,
    page_num: int = 0,
) -> Tuple[bytes, List[str]]:
    """
    Stamps fields onto a PDF template.
    `fields` is a list of field configurations:
    {
        "id": str,
        "binding": str,         # Column name or placeholder e.g. "{{Name}}"
        "x": float,             # Normalized 0..1 or PDF points
        "y": float,             # Normalized 0..1 or PDF points
        "width": float,
        "height": float,
        "is_normalized": bool,  # True if coordinates are 0..1
        "font_family": "sans-serif" | "serif" | "monospace",
        "font_size": 24,
        "auto_shrink": True,
        "min_font_size": 8,
        "bold": False,
        "italic": False,
        "color": "#000000",
        "align": "left" | "center" | "right",
        "is_acroform": False,
        "acroform_name": ""
    }
    Returns:
        (pdf_bytes, list_of_warnings)
    """
    from .data_service import interpolate_text

    doc = fitz.open(template_path)
    if page_num >= len(doc):
        page_num = 0
    page = doc[page_num]
    page_w = float(page.rect.width)
    page_h = float(page.rect.height)

    all_warnings = []

    # Map of existing AcroForm widgets on the page
    acro_widgets = {w.field_name: w for w in page.widgets() if w.field_name}

    for f_cfg in fields:
        binding = f_cfg.get("binding", "")
        if not binding:
            continue

        resolved_text, warnings = interpolate_text(binding, row_data)
        all_warnings.extend(warnings)

        # Coordinate resolution
        is_norm = f_cfg.get("is_normalized", True)
        if is_norm:
            x0 = f_cfg["x"] * page_w
            y0 = f_cfg["y"] * page_h
            w = f_cfg["width"] * page_w
            h = f_cfg["height"] * page_h
        else:
            x0 = float(f_cfg["x"])
            y0 = float(f_cfg["y"])
            w = float(f_cfg["width"])
            h = float(f_cfg["height"])

        rect = fitz.Rect(x0, y0, x0 + w, y0 + h)

        # Font and styling
        font_family = f_cfg.get("font_family", "sans-serif")
        bold = f_cfg.get("bold", False)
        italic = f_cfg.get("italic", False)
        font_name = get_font_name(font_family, bold, italic)
        desired_size = float(f_cfg.get("font_size", 20))
        auto_shrink = f_cfg.get("auto_shrink", True)
        min_size = float(f_cfg.get("min_font_size", 6))
        color_rgb = hex_to_rgb(f_cfg.get("color", "#000000"))
        align_str = f_cfg.get("align", "left").lower()
        align_val = ALIGN_MAP.get(align_str, fitz.TEXT_ALIGN_LEFT)

        if auto_shrink:
            actual_size = compute_auto_shrink_fontsize(
                resolved_text, font_name, w, h, desired_size, min_size=min_size
            )
        else:
            actual_size = desired_size

        # If it targets an AcroForm field specifically and user chose native form fill
        acro_name = f_cfg.get("acroform_name")
        if acro_name and acro_name in acro_widgets and f_cfg.get("use_native_acroform", False):
            widget = acro_widgets[acro_name]
            widget.field_value = resolved_text
            widget.update()
        else:
            # If an AcroForm field overlaps here and we are doing flat stamp, delete the widget so it doesn't collide
            if acro_name and acro_name in acro_widgets:
                page.delete_widget(acro_widgets[acro_name])

            # Flat overlay stamp using PyMuPDF insert_textbox
            line_height = actual_size * 1.25
            num_lines = max(1, len(resolved_text.split("\n")))
            text_block_height = num_lines * line_height

            # Vertically center text inside the user's bounding box
            y_offset = max(0.0, (h - text_block_height) / 2.0) if h > text_block_height else 0.0

            # Use an open bottom boundary so MuPDF font metrics never reject text due to tight padding
            effective_size = actual_size
            placed_success = False

            while effective_size >= min_size:
                stamp_rect = fitz.Rect(
                    x0,
                    y0 + y_offset,
                    x0 + w,
                    max(y0 + h, y0 + y_offset + effective_size * num_lines * 1.6 + 6),
                )
                rc = page.insert_textbox(
                    stamp_rect,
                    resolved_text,
                    fontsize=effective_size,
                    fontname=font_name,
                    color=color_rgb,
                    align=align_val,
                )
                if rc >= 0:
                    placed_success = True
                    break
                effective_size -= 0.5

            # Fallback: if insert_textbox still rejected, use insert_text directly so text is NEVER missing
            if not placed_success:
                baseline_y = y0 + y_offset + effective_size
                if align_val == fitz.TEXT_ALIGN_CENTER:
                    try:
                        text_w = fitz.Font(font_name).text_length(resolved_text, fontsize=effective_size)
                    except Exception:
                        text_w = len(resolved_text) * effective_size * 0.5
                    start_x = max(x0, x0 + (w - text_w) / 2.0)
                elif align_val == fitz.TEXT_ALIGN_RIGHT:
                    try:
                        text_w = fitz.Font(font_name).text_length(resolved_text, fontsize=effective_size)
                    except Exception:
                        text_w = len(resolved_text) * effective_size * 0.5
                    start_x = max(x0, x0 + w - text_w)
                else:
                    start_x = x0

                page.insert_text(
                    fitz.Point(start_x, baseline_y),
                    resolved_text,
                    fontsize=effective_size,
                    fontname=font_name,
                    color=color_rgb,
                )

    if output_path:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(out_p))
        doc.close()
        return b"", all_warnings
    else:
        out_bytes = doc.tobytes()
        doc.close()
        return out_bytes, all_warnings


def generate_sample_preview(
    template_path: str,
    fields: List[Dict[str, Any]],
    row_data: Dict[str, str],
    page_num: int = 0,
    dpi: int = 150,
) -> Tuple[str, List[str]]:
    """
    Renders a live WYSIWYG preview image (PNG base64) for a specific row.
    """
    stamped_bytes, warnings = stamp_pdf(
        template_path=template_path,
        fields=fields,
        row_data=row_data,
        output_path=None,
        page_num=page_num,
    )
    # Open the in-memory stamped PDF and render to image
    doc = fitz.open(stream=stamped_bytes, filetype="pdf")
    page = doc[page_num]
    pix = page.get_pixmap(dpi=dpi)
    png_bytes = pix.tobytes("png")
    doc.close()

    encoded = base64.b64encode(png_bytes).decode("ascii")
    data_uri = f"data:image/png;base64,{encoded}"
    return data_uri, warnings
