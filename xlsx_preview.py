"""
Excel Visual Verification
---------------------------
Renders an Excel workbook (or one sheet) to page images so a spreadsheet's
look -- colors, layout, styling -- can actually be seen, instead of only being
checked cell-by-cell through openpyxl's data model.

Converts through Excel itself (COM automation via pywin32), setting each sheet
to fit-to-width so columns aren't split across pages, exports to PDF, then
renders each page to a PNG with PyMuPDF.

Requires Microsoft Excel installed (Windows only), plus pywin32 and PyMuPDF.
Mirrors docx_preview.py for Word.

Usage:
    python xlsx_preview.py <file.xlsx>
    python xlsx_preview.py <file.xlsx> --sheet Mubeen
    python xlsx_preview.py <file.xlsx> -o previews --dpi 150
"""
import argparse
import sys
from pathlib import Path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="xlsx_preview",
        description="Render an Excel workbook to page images for real visual verification.")
    ap.add_argument("input", help="Path to a .xlsx / .xlsm file")
    ap.add_argument("-s", "--sheet", default=None,
                     help="Render only this sheet (by name). Default: all sheets.")
    ap.add_argument("-o", "--out-dir", default=None,
                     help="Where to save images. Default: <input>_preview next to the file.")
    ap.add_argument("--dpi", type=int, default=150, help="Render resolution. Default 150.")
    args = ap.parse_args(argv)

    in_path = Path(args.input).resolve()
    if not in_path.exists():
        print(f"ERROR: File not found: {in_path}")
        return 2
    if in_path.suffix.lower() not in (".xlsx", ".xlsm", ".xls"):
        print(f"ERROR: Not an Excel file: {in_path.suffix}")
        return 5

    try:
        f = open(in_path, "r+b"); f.close()
    except PermissionError:
        print(f"ERROR: {in_path.name} is open in another program (likely Excel). Close it and try again.")
        return 3

    out_dir = Path(args.out_dir) if args.out_dir else in_path.parent / f"{in_path.stem}_preview"
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = out_dir / f"{in_path.stem}.pdf"

    try:
        import win32com.client
    except ImportError:
        print("ERROR: pywin32 is not installed. Run: pip install pywin32")
        return 4

    excel = None
    wb = None
    try:
        excel = win32com.client.DispatchEx("Excel.Application")
        excel.Visible = False
        excel.DisplayAlerts = False
        wb = excel.Workbooks.Open(str(in_path), ReadOnly=True)

        # Fit each sheet to one page wide so columns don't split across pages.
        for ws in wb.Worksheets:
            if args.sheet and ws.Name != args.sheet:
                ws.Visible = False  # hide non-target sheets so only the one exports
                continue
            ws.PageSetup.Zoom = False
            ws.PageSetup.FitToPagesWide = 1
            ws.PageSetup.FitToPagesTall = False
            ws.PageSetup.Orientation = 2  # landscape

        # 0 = xlTypePDF
        wb.ExportAsFixedFormat(0, str(pdf_path))
    except Exception as e:
        print(f"ERROR during Excel export: {e}")
        return 6
    finally:
        try:
            if wb is not None:
                wb.Close(False)
        except Exception:
            pass
        try:
            if excel is not None:
                excel.Quit()
        except Exception:
            pass

    if not pdf_path.exists():
        print("ERROR: PDF was not produced.")
        return 7

    try:
        import fitz
    except ImportError:
        print("ERROR: PyMuPDF is not installed. Run: pip install PyMuPDF")
        return 8

    doc = fitz.open(str(pdf_path))
    saved = []
    for i in range(doc.page_count):
        pix = doc[i].get_pixmap(dpi=args.dpi)
        img_path = out_dir / f"page_{i + 1}.png"
        pix.save(str(img_path))
        saved.append(img_path)

    print(f"\nRendered {len(saved)} page(s) to: {out_dir}")
    for p in saved:
        print(f"  {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
