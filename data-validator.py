"""
Universal QA Toolkit — Data Integrity & Pre-Audit Checker (data-validator.py)
Performs fast sanity checks on raw datasets: null counts, duplicate detection, encoding issues, schema rules.
Author: Azeez
"""

import os
import sys
import json
import re
import argparse
import pandas as pd

# Mojibake & Encoding corruption regex patterns
MOJIBAKE_PATTERN = re.compile(r"Ã.|Â.|â€.|ï¿½|\?\?|\uFFFD")
HTML_TAG_PATTERN = re.compile(r"<[^>]+>|&[a-z]+;|&#\d+;")

def audit_dataset(file_path, checks=None, dedup_key=None, country_code="BE"):
    """Run automated sanity checks on an Excel or CSV file."""
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.", file=sys.stderr)
        sys.exit(1)

    df = pd.read_excel(file_path, dtype=str) if file_path.endswith(('.xlsx', '.xls')) else pd.read_csv(file_path, dtype=str)
    df = df.fillna("")

    total_rows = len(df)
    results = {
        "dataset": os.path.basename(file_path),
        "total_rows": total_rows,
        "total_columns": len(df.columns),
        "issues_summary": {},
        "findings": []
    }

    # 1. Null / Blank Value Coverage
    null_summary = {}
    for col in df.columns:
        empty_count = int((df[col].str.strip() == "").sum())
        if empty_count > 0:
            null_summary[col] = {
                "empty_rows": empty_count,
                "empty_percentage": f"{(empty_count / total_rows) * 100:.1f}%"
            }
    results["null_coverage"] = null_summary

    # 2. Duplicate Detection
    if dedup_key:
        keys = [k.strip() for k in dedup_key.split(",") if k.strip() in df.columns]
        if keys:
            dupes = df[df.duplicated(subset=keys, keep=False)]
            dupe_count = len(dupes)
            results["duplicates"] = {
                "keys_checked": keys,
                "duplicate_rows": dupe_count,
                "unique_rows": total_rows - dupe_count
            }

    # 3. Encoding & Mojibake Check
    encoding_issues = []
    for idx, row in df.iterrows():
        row_num = idx + 2
        for col in df.columns:
            val = str(row[col])
            if MOJIBAKE_PATTERN.search(val):
                encoding_issues.append({
                    "row": row_num,
                    "column": col,
                    "value": val,
                    "type": "Mojibake/Encoding Corruption"
                })
            elif HTML_TAG_PATTERN.search(val):
                encoding_issues.append({
                    "row": row_num,
                    "column": col,
                    "value": val,
                    "type": "Unstripped HTML Tag"
                })

    results["encoding_issues_count"] = len(encoding_issues)
    if encoding_issues:
        results["encoding_samples"] = encoding_issues[:10]

    # 4. Postal Code Integrity Check
    if "postal_code" in df.columns:
        invalid_postal = []
        for idx, row in df.iterrows():
            pc = str(row["postal_code"]).strip()
            if country_code == "BE" and pc and not re.match(r"^\d{4}$", pc):
                invalid_postal.append({"row": idx + 2, "postal_code": pc})
        results["invalid_postal_codes_count"] = len(invalid_postal)
        if invalid_postal:
            results["invalid_postal_samples"] = invalid_postal[:10]

    print(json.dumps(results, indent=2))

def main():
    parser = argparse.ArgumentParser(description="Data Integrity Checker (data-validator.py)")
    parser.add_argument("file", help="Path to Excel or CSV file")
    parser.add_argument("--dedup-key", help="Comma-separated column names to check for duplicates")
    parser.add_argument("--country", default="BE", help="Country code for validation rules")

    args = parser.parse_args()
    audit_dataset(args.file, dedup_key=args.dedup_key, country_code=args.country)

if __name__ == "__main__":
    main()
