# DocuNext: Bulk PDF Stamping & Email Suite

**DocuNext** is a self-hosted, offline-capable web suite for bulk-generating personalized PDF certificates/documents from templates and Excel/CSV spreadsheets, with built-in bulk email dispatch and Test Mode verification.

---

## Key Features

1. **100% Offline & Zero External Network Calls**:
   - Runs strictly on `localhost`.
   - Zero CDN dependencies (all styles, scripts, and fonts are bundled or native).
2. **Flexible Template Support**:
   - **Flat PDF Templates**: Rendered at high DPI as a canvas background for interactive field placement.
   - **Fillable AcroForm PDFs**: Detects existing form fields, visualizes their boundaries, and automatically matches them to spreadsheet columns.
3. **Interactive Drag-and-Drop Canvas**:
   - Sidebar column chips can be dragged directly onto the canvas to place fields.
   - 8-point interactive resize handles and drag-to-reposition.
   - Live preview updating in real-time with sample spreadsheet rows.
4. **Intelligent Text Styling & Auto-Shrink**:
   - Customize font family (Helvetica, Times-Roman, Courier), size, color, bold/italic, and text alignment.
   - **Auto-shrink font fitting**: Automatically decreases font size if long names would overflow the bounding box.
   - Supports both direct column binding and multi-column placeholder syntax (e.g. `{{First Name}} {{Last Name}} - Class of 2026`).
5. **Auto-Match Column Headers**:
   - Fuzzy and semantic token matching between PDF form fields and spreadsheet headers (handling spaces, underscores, and special characters).
6. **Project Save & Reuse**:
   - Save complete field layouts, bindings, styles, and filename patterns to JSON project files to easily reuse layouts on future spreadsheets.
7. **Dynamic Filename Pattern**:
   - Customize output filenames using column tags (e.g. `{Recipient Name}_{Course Title}.pdf`).
   - Automatically sanitizes invalid characters and prevents collisions.
8. **High-Capacity Background Job Worker**:
   - Generation runs in a background worker pool with a live progress bar, processed row counter, and warning log for missing/blank cells.
   - Comfortably handles batches of thousands of certificates without freezing the browser.
9. **Export & Output**:
   - Download all generated certificates in **1 click as a ZIP archive**.
   - Direct download and view links for individual PDFs.
   - All files persist locally in the `output/` directory.

---

## Quick Start

### Option 1: One-Click Windows Launcher (Recommended)
Double-click `run.bat` (or right-click `run.ps1` and select "Run with PowerShell").
- Automatically detects Python, sets up a local virtual environment (`.venv`), installs dependencies, starts the FastAPI server, and launches your browser to `http://localhost:8000`.

### Option 2: Manual Terminal Run
```powershell
# 1. Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start server
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```
Then open your browser to `http://localhost:8000`.

### Option 3: Docker (Optional)
```bash
docker compose up --build
```
Access the app at `http://localhost:8000`.

---

## Out-of-the-Box Demo

To test immediately without preparing any files:
1. Click **"+ Demo: Flat"** in the top navigation bar.
2. The app will automatically generate an elegant landscape certificate template, 10 sample student rows in Excel, and pre-place fields.
3. Switch between rows using the `< Prev Row / Next >` buttons to see names dynamically adapt.
4. Click **"Next: Generate"** -> **"Generate 10 certificates"** to watch the live progress bar and download the ZIP!
