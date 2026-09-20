import pymupdf as fitz
import openpyxl
from pathlib import Path


def generate_sample_assets(output_dir: Path, row_count: int = 10):
    """
    Generates a sample flat certificate PDF, an AcroForm certificate PDF,
    and a sample Excel spreadsheet for quick out-of-the-box testing.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    flat_pdf_path = output_dir / "sample_certificate_template.pdf"
    acro_pdf_path = output_dir / "sample_fillable_template.pdf"
    excel_path = output_dir / f"sample_data_{row_count}.xlsx"

    # 1. Flat Certificate Template
    if not flat_pdf_path.exists():
        doc = fitz.open()
        # US Letter Landscape: 792 x 612 points
        page = doc.new_page(width=792, height=612)

        # Draw decorative borders
        # Outer border
        page.draw_rect(
            fitz.Rect(20, 20, 772, 592),
            color=(0.12, 0.23, 0.54), # Navy blue #1E3A8A
            width=4,
        )
        # Inner thin gold border
        page.draw_rect(
            fitz.Rect(28, 28, 764, 584),
            color=(0.85, 0.65, 0.13), # Gold #D9A521
            width=1.5,
        )
        # Corner decorative accents
        for x, y, dx, dy in [(36, 36, 40, 40), (756, 36, -40, 40), (36, 576, 40, -40), (756, 576, -40, -40)]:
            page.draw_line(fitz.Point(x, y), fitz.Point(x + dx, y), color=(0.85, 0.65, 0.13), width=2)
            page.draw_line(fitz.Point(x, y), fitz.Point(x, y + dy), color=(0.85, 0.65, 0.13), width=2)

        # Certificate Header Text
        page.insert_textbox(
            fitz.Rect(50, 70, 742, 120),
            "DOCUNEXT ACADEMY OF EXCELLENCE",
            fontsize=15,
            fontname="helv",
            color=(0.3, 0.35, 0.4),
            align=fitz.TEXT_ALIGN_CENTER,
        )

        page.insert_textbox(
            fitz.Rect(50, 120, 742, 190),
            "CERTIFICATE OF COMPLETION",
            fontsize=32,
            fontname="hebo",
            color=(0.12, 0.23, 0.54),
            align=fitz.TEXT_ALIGN_CENTER,
        )

        page.insert_textbox(
            fitz.Rect(50, 200, 742, 230),
            "PROUDLY PRESENTED TO",
            fontsize=13,
            fontname="helv",
            color=(0.4, 0.45, 0.5),
            align=fitz.TEXT_ALIGN_CENTER,
        )

        # Decorative line for name
        page.draw_line(fitz.Point(180, 295), fitz.Point(612, 295), color=(0.8, 0.82, 0.85), width=1)

        page.insert_textbox(
            fitz.Rect(50, 310, 742, 340),
            "for successfully completing all professional curriculum requirements in",
            fontsize=13,
            fontname="helv",
            color=(0.4, 0.45, 0.5),
            align=fitz.TEXT_ALIGN_CENTER,
        )

        # Decorative line for course
        page.draw_line(fitz.Point(220, 395), fitz.Point(572, 395), color=(0.8, 0.82, 0.85), width=1)

        # Signatures and Date sections
        page.draw_line(fitz.Point(120, 510), fitz.Point(300, 510), color=(0.6, 0.6, 0.6), width=1)
        page.insert_textbox(
            fitz.Rect(120, 515, 300, 540),
            "Date of Issue",
            fontsize=11,
            fontname="helv",
            color=(0.4, 0.4, 0.4),
            align=fitz.TEXT_ALIGN_CENTER,
        )

        page.draw_line(fitz.Point(492, 510), fitz.Point(672, 510), color=(0.6, 0.6, 0.6), width=1)
        page.insert_textbox(
            fitz.Rect(492, 515, 672, 540),
            "Authorized Signature",
            fontsize=11,
            fontname="helv",
            color=(0.4, 0.4, 0.4),
            align=fitz.TEXT_ALIGN_CENTER,
        )

        doc.save(str(flat_pdf_path))
        doc.close()

    # 2. AcroForm Fillable PDF Template
    if not acro_pdf_path.exists():
        doc = fitz.open()
        page = doc.new_page(width=792, height=612)

        # Draw borders
        page.draw_rect(fitz.Rect(20, 20, 772, 592), color=(0.1, 0.35, 0.25), width=3) # Forest green
        page.insert_textbox(
            fitz.Rect(50, 100, 742, 160),
            "OFFICIAL ACCREDITATION CERTIFICATE",
            fontsize=28,
            fontname="hebo",
            color=(0.1, 0.35, 0.25),
            align=fitz.TEXT_ALIGN_CENTER,
        )
        page.insert_textbox(
            fitz.Rect(50, 180, 742, 210),
            "This certifies that:",
            fontsize=14,
            fontname="helv",
            color=(0.3, 0.3, 0.3),
            align=fitz.TEXT_ALIGN_CENTER,
        )

        # AcroForm text fields
        # Name field
        w_name = fitz.Widget()
        w_name.rect = fitz.Rect(150, 230, 642, 280)
        w_name.field_name = "recipient_name"
        w_name.field_type = fitz.PDF_WIDGET_TYPE_TEXT
        w_name.text_fontsize = 22
        w_name.text_color = (0.1, 0.35, 0.25)
        page.add_widget(w_name)

        page.insert_textbox(
            fitz.Rect(50, 310, 742, 335),
            "has demonstrated mastery in:",
            fontsize=13,
            fontname="helv",
            color=(0.3, 0.3, 0.3),
            align=fitz.TEXT_ALIGN_CENTER,
        )

        # Course field
        w_course = fitz.Widget()
        w_course.rect = fitz.Rect(180, 350, 612, 395)
        w_course.field_name = "course_title"
        w_course.field_type = fitz.PDF_WIDGET_TYPE_TEXT
        w_course.text_fontsize = 18
        page.add_widget(w_course)

        # Date field
        w_date = fitz.Widget()
        w_date.rect = fitz.Rect(120, 480, 300, 510)
        w_date.field_name = "issue_date"
        w_date.field_type = fitz.PDF_WIDGET_TYPE_TEXT
        w_date.text_fontsize = 12
        page.add_widget(w_date)

        # ID field
        w_id = fitz.Widget()
        w_id.rect = fitz.Rect(492, 480, 672, 510)
        w_id.field_name = "certificate_id"
        w_id.field_type = fitz.PDF_WIDGET_TYPE_TEXT
        w_id.text_fontsize = 12
        page.add_widget(w_id)

        doc.save(str(acro_pdf_path))
        doc.close()

    # 3. Sample Excel Spreadsheet
    excel_path = output_dir / f"sample_data_{row_count}.xlsx"
    if not excel_path.exists():
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Certificates"

        headers = ["Recipient Name", "Recipient Email", "Course Title", "Completion Date", "Grade", "Certificate ID"]
        ws.append(headers)

        first_names = [
            "Dr. Alexandra", "Marcus Aurelius", "Dr. Sophia", "Devon", "Elena", "Carlos", "Aisha",
            "Benjamin", "Priya", "Taro", "Liam", "Olivia", "Noah", "Emma", "Lucas", "Ava",
            "Mateo", "Isabella", "Ethan", "Mia", "Alexander", "Charlotte", "Daniel", "Amelia",
            "Henry", "Harper", "Sebastian", "Evelyn", "Jack", "Abigail", "Victoria", "Gabriel"
        ]
        last_names = [
            "Bennett", "Vance", "Chen", "Jamieson", "Rostova", "Mendoza-Cruz", "Al-Mansoor",
            "O'Connor", "Patel", "Takahashi", "Smith", "Johnson", "Williams", "Brown", "Jones",
            "Garcia", "Miller", "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
            "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez"
        ]
        courses = [
            "Advanced Web Development & Cloud Computing",
            "Executive Leadership & Strategic Management",
            "Bioinformatics and Genomic Analytics",
            "Cloud Architecture & Cybersecurity",
            "Quantitative Financial Modeling",
            "Full-Stack Distributed Systems Engineering",
            "Software Architecture & Database Systems",
            "Renewable Energy Grid Design",
            "Product Strategy & Human-Computer Interaction",
            "High Performance Computing with Rust & C++",
            "Biomedical Engineering & Laboratory Systems",
            "Mobile Application Development & Architecture"
        ]
        grades = ["Distinction", "High Honors", "Honors", "Distinction", "Merit", "High Honors"]

        for i in range(row_count):
            fn = first_names[i % len(first_names)]
            ln = last_names[(i * 3) % len(last_names)]
            course = courses[(i * 2) % len(courses)]
            grade = grades[i % len(grades)]
            day = 10 + (i % 18)
            date_str = f"2026-05-{day:02d}"
            cert_id = f"CERT-2026-{i + 1:04d}"
            safe_fn = fn.replace("Dr. ", "").strip().lower().replace(" ", "")
            safe_ln = ln.lower().replace("-", "").replace("'", "")
            email_addr = f"{safe_fn}.{safe_ln}{i + 1}@example.com"
            ws.append([f"{fn} {ln}", email_addr, course, date_str, grade, cert_id])

        wb.save(str(excel_path))
        wb.close()

    return {
        "flat_pdf": str(flat_pdf_path.resolve()),
        "acro_pdf": str(acro_pdf_path.resolve()),
        "excel": str(excel_path.resolve()),
    }
