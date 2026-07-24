"""
Document Visual Verification
------------------------------
Renders a Word document to page images so an edit can actually be looked at,
instead of only being checked through python-docx's data model (which can
miss real layout problems, like a leftover paragraph creating a visible gap).

Converts through Word itself (docx2pdf, via COM automation) so the preview
matches exactly what Word would show, then renders each PDF page to a PNG.

Requires Microsoft Word installed on this machine (used for the docx->PDF
step) plus the docx2pdf and PyMuPDF ("fitz") Python packages. Windows/Word
only -- there is no Word-free fallback here, since the goal is a faithful
preview, not an approximation.

Usage:
    python docx_preview.py <file.docx>
    python docx_preview.py <file.docx> --pages 1,3-5
    python docx_preview.py <file.docx> -o <output_dir> --dpi 200
    python docx_preview.py <file.pdf>          (skips the docx->PDF step)
"""
import argparse
import sys
from pathlib import Path


def parse_pages(spec: str | None, total_pages: int) -> list[int]:
    if not spec:
        return list(range(total_pages))
    pages = set()
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-")
            pages.update(range(int(a) - 1, int(b)))
        else:
            pages.add(int(part) - 1)
    return sorted(p for p in pages if 0 <= p < total_pages)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="docx_preview",
        description="Render a Word document to page images for real visual verification, "
                    "instead of guessing from the underlying XML.")
    ap.add_argument("input", help="Path to a .docx (or .pdf) file")
    ap.add_argument("-p", "--pages", default=None,
                     help="Which pages to render, e.g. '1,3-5'. Default: all pages.")
    ap.add_argument("-o", "--out-dir", default=None,
                     help="Where to save the page images. Default: <input>_preview folder next to the input file.")
    ap.add_argument("--dpi", type=int, default=150, help="Render resolution. Default 150.")
    args = ap.parse_args(argv)

    in_path = Path(args.input)
    if not in_path.exists():
        print(f"ERROR: File not found: {in_path}")
        return 2

    out_dir = Path(args.out_dir) if args.out_dir else in_path.parent / f"{in_path.stem}_preview"
    out_dir.mkdir(parents=True, exist_ok=True)

    if in_path.suffix.lower() == ".pdf":
        pdf_path = in_path
    elif in_path.suffix.lower() == ".docx":
        try:
            f = open(in_path, "r+b")
            f.close()
        except PermissionError:
            print(f"ERROR: {in_path.name} is open in another program (likely Word). Close it and try again.")
            return 3
        try:
            from docx2pdf import convert
        except ImportError:
            print("ERROR: docx2pdf is not installed. Run: pip install docx2pdf")
            return 4
        pdf_path = out_dir / f"{in_path.stem}.pdf"
        print(f"Converting {in_path.name} to PDF via Word...")
        convert(str(in_path), str(pdf_path))
    else:
        print(f"ERROR: Unsupported file type: {in_path.suffix}. Use .docx or .pdf.")
        return 5

    try:
        import fitz
    except ImportError:
        print("ERROR: PyMuPDF is not installed. Run: pip install PyMuPDF")
        return 6

    doc = fitz.open(str(pdf_path))
    total = doc.page_count
    page_indices = parse_pages(args.pages, total)

    saved = []
    for i in page_indices:
        page = doc[i]
        pix = page.get_pixmap(dpi=args.dpi)
        img_path = out_dir / f"page_{i + 1}.png"
        pix.save(str(img_path))
        saved.append(img_path)

    print(f"\nRendered {len(saved)} of {total} page(s) to: {out_dir}")
    for p in saved:
        print(f"  {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
