"""
Universal QA Toolkit — Headless HTML to PDF Compiler (pdf-print.py)
Uses Microsoft Edge or Chrome headless engine to compile pixel-perfect PDFs from HTML.
Author: Azeez
"""

import os
import sys
import argparse
import subprocess

def find_browser_binary():
    """Find local Microsoft Edge or Google Chrome binary path."""
    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        os.path.expanduser(r"~\AppData\Local\Microsoft\Edge\Application\msedge.exe")
    ]
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
    ]

    for p in edge_paths + chrome_paths:
        if os.path.exists(p):
            return p
    return None

def compile_html_to_pdf(html_file, output_pdf=None, landscape=False, print_background=True):
    """Compile HTML to PDF using headless Edge/Chrome."""
    if not os.path.exists(html_file):
        print(f"Error: HTML input file '{html_file}' not found.", file=sys.stderr)
        sys.exit(1)

    browser = find_browser_binary()
    if not browser:
        print("Error: Neither Microsoft Edge nor Google Chrome executable was found.", file=sys.stderr)
        sys.exit(1)

    abs_html = os.path.abspath(html_file)
    if not output_pdf:
        output_pdf = os.path.splitext(abs_html)[0] + ".pdf"
    abs_pdf = os.path.abspath(output_pdf)

    os.makedirs(os.path.dirname(abs_pdf), exist_ok=True)

    cmd = [
        browser,
        "--headless",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={abs_pdf}",
        f"file:///{abs_html.replace(os.sep, '/')}"
    ]

    if print_background:
        cmd.append("--no-margins")

    print(f"Compiling PDF via {os.path.basename(browser)}: '{html_file}' → '{abs_pdf}'...")
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if os.path.exists(abs_pdf) and os.path.getsize(abs_pdf) > 0:
            print(f"Successfully generated PDF report ({os.path.getsize(abs_pdf):,} bytes): '{abs_pdf}'")
        else:
            print("Error: PDF output file was not generated or is empty.", file=sys.stderr)
            sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Compilation Failed: {e.stderr.decode('utf-8', errors='ignore')}", file=sys.stderr)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Headless HTML to PDF Compiler (pdf-print.py)")
    parser.add_argument("html_file", help="Input HTML file path")
    parser.add_argument("-o", "--output", help="Output PDF file path")
    parser.add_argument("--landscape", action="store_true", help="Print in landscape mode")
    parser.add_argument("--no-background", action="store_true", help="Disable background graphics/colors")

    args = parser.parse_args()
    compile_html_to_pdf(args.html_file, args.output, args.landscape, not args.no_background)

if __name__ == "__main__":
    main()
