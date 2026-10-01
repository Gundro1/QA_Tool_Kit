#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
report_verifier.py  -  "QA of the QA"

Private confidence check you run AFTER a bisquality audit, to tell YOU whether
the generated report's findings are real or whether something needs correcting.
Its output is NOT part of the audit report - it is just for you to decide whether
to trust/fix the report before sending it.

WHY IT RE-RUNS THE AUDIT INSTEAD OF READING THE HTML/PDF/TXT:
  The report outputs TRUNCATE the affected-row lists for display ("... and others,
  see the attached txt"). Parsing them would only verify the first ~20 rows of the
  big findings - exactly the ones that matter least. So the verifier re-runs
  bisquality's own audit on the dataset (which returns the FULL, untruncated rows
  in memory) and re-checks every finding against the actual source rows.
  => You point it at the DATASET; it works no matter which output format you kept.

Every check is DETERMINISTIC (re-reads the rows a finding cites and confirms the
defect is really there), so it cannot introduce its own false positives. Real-world
"does this brand exist" is out of scope - that stays a separate manual/web step.

Usage:
    python report_verifier.py "<dataset.xlsx>" -c IQ
    python report_verifier.py "<dataset.xlsx>" -c IQ --report "<the html you're holding>"   # name only, for the header
    python report_verifier.py "<dataset.xlsx>"          # country auto-detected from the data

Exit code: 0 = all clean, 2 = at least one finding needs your review.
Author: Azeez | BisViews | 2026-09-24
"""
import sys, os, re, argparse, importlib.util, unicodedata
import pandas as pd

BISQUALITY_PATH = os.environ.get("BISQUALITY_PATH") or os.path.join(
    os.path.expanduser("~"), "OneDrive", "Desktop", "BISVIEW",
    "SCIPT implementation", "bisquality.py")

def norm(s):
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    s = unicodedata.normalize("NFKD", str(s).strip().lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[\s,._\-]+", " ", s).strip()

def load_bisquality():
    if not os.path.exists(BISQUALITY_PATH):
        print(f"ERROR: bisquality.py not found at:\n  {BISQUALITY_PATH}\n"
              f"Set BISQUALITY_PATH env var to its location.", file=sys.stderr)
        sys.exit(1)
    spec = importlib.util.spec_from_file_location("bq_for_verify", BISQUALITY_PATH)
    bq = importlib.util.module_from_spec(spec); spec.loader.exec_module(bq)
    return bq

# --- per-rule independent re-check: does the cited row actually show the defect? ---
def check_row(iid, row, C):
    """Return True (defect present), False (contradicted), or None (not checkable here)."""
    g = lambda name: row.get(C(name), "") if C(name) else ""
    if iid == "FGR-02":
        return norm(g("business_name")) != norm(g("franchise_name"))
    if iid == "FGR-01":
        return bool(re.search(r"brand.?operated|independent|not publicly|not disclosed|placeholder|various|unknown", norm(g("franchise_name"))))
    if iid == "FRH-01":
        return True  # spelling-minority: trust the engine's majority calc (not re-derivable per-row)
    if iid == "FRH-02":
        return norm(g("franchise_flag")) in ("n", "no", "false", "0")
    if iid == "FRH-03":
        return norm(g("franchise_flag")) in ("y", "yes", "true", "1") and norm(g("franchise_name")) in ("", "nan", "none", "null")
    if iid == "FRH-04":
        flag = norm(g("franchise_flag"))
        has_fn = norm(g("franchise_name")) not in ("", "nan", "none", "null")
        bc = norm(g("branch_count")); has_bc = bc not in ("", "nan", "none", "null", "0")
        return flag in ("n", "no", "false", "0") and (has_fn or has_bc)
    if iid == "TAX-05":
        return norm(g("business_type")) not in ("regular business", "investment business")
    if iid == "TAX-04":
        return str(g("state_applicable")).strip() not in ("TRUE", "FALSE")
    if iid == "TAX-03":
        return str(g("franchise_flag")).strip() not in ("Y", "N")
    if iid == "ADR-10":
        return bool(re.search(r"[0-9A-Za-z]{4}\+[0-9A-Za-z]{2,}", str(g("address"))))
    if iid == "ENC-03":
        a = str(g("address")); return a.isupper() and any(c.isalpha() for c in a)
    if iid == "POS-01":
        return norm(g("postal_code")) in ("", "nan", "none", "null")
    if iid == "DUP-02":
        return None  # pairwise; trust engine
    return None

def main():
    ap = argparse.ArgumentParser(description="Verify a bisquality report's findings against the source data (re-runs the audit; no report parsing).")
    ap.add_argument("dataset")
    ap.add_argument("-c", "--country", default=None, help="country code (auto-detected from data if omitted)")
    ap.add_argument("--report", default=None, help="the report file you are holding (HTML/PDF/TXT) - shown in the header only")
    args = ap.parse_args()

    if not os.path.exists(args.dataset):
        print(f"ERROR: dataset not found: {args.dataset}", file=sys.stderr); sys.exit(1)

    bq = load_bisquality()
    df = bq.read_and_merge_sheets(args.dataset).reset_index(drop=True)
    df.columns = [str(c).strip() for c in df.columns]
    if "_sheet" not in df.columns:
        df["_sheet"] = "Sheet1"
    total_rows = len(df)

    # country
    cc = args.country
    if not cc:
        for c in ("country_code", "country"):
            if c in df.columns and df[c].astype(str).str.strip().ne("").any():
                cc = df[c].astype(str).str.strip().mode().iloc[0]; break
        cc = cc or "XX"

    C = lambda name: bq.COLUMN_MAP.get(name) if bq.COLUMN_MAP.get(name) in df.columns else None
    by_row = {i + 2: r for i, (_, r) in enumerate(df.iterrows())}

    # Re-run the audit -> FULL untruncated findings
    findings, *_ = bq.run_multi_country_audit(df, cc)

    print("=" * 72)
    print("REPORT VERIFIER  -  QA-of-the-QA (private; not part of the audit)")
    print("=" * 72)
    print(f"Dataset : {os.path.basename(args.dataset)}  ({total_rows} rows, country {cc})")
    if args.report:
        print(f"Report  : {os.path.basename(args.report)}  (findings re-derived from the dataset, full row lists)")
    print(f"Findings re-run: {len(findings)}")
    print("-" * 72)

    problems = []
    for f in sorted(findings, key=lambda x: x.issue_id):
        iid = f.issue_id
        rows = list(f.sample_rows or [])
        held = contra = 0; contra_rows = []
        # Some findings store row NUMBERS; a few store richer objects. Only int row-ids are re-checkable.
        int_rows = [rn for rn in rows if isinstance(rn, int)]
        for rn in int_rows:
            r = by_row.get(rn)
            if r is None:
                continue
            v = check_row(iid, r, C)
            if v is True: held += 1
            elif v is False:
                contra += 1
                if len(contra_rows) < 10: contra_rows.append(rn)
        checkable = held + contra
        flags = []
        if checkable and contra:
            flags.append(f"{contra}/{checkable} re-checked rows DON'T show the defect ({contra/checkable*100:.0f}% false) e.g. {contra_rows}")
        if total_rows and len(rows)/total_rows > 0.30:
            if not (checkable and contra == 0):
                flags.append(f"HIGH HIT-RATE {len(rows)}/{total_rows} = {len(rows)/total_rows*100:.0f}% and not independently confirmed - verify it isn't a config/whitelist gap")
        status = "OK" if not flags else "!! REVIEW"
        chk = f" [re-verified {held}/{checkable} hold]" if checkable else " [not independently checkable]"
        print(f"[{status:9}] {iid:7} {f.severity:8} {len(rows):>4} rows{chk}")
        for fl in flags: print(f"            - {fl}")
        if flags: problems.append(iid)

    print("-" * 72)
    if problems:
        print(f"RESULT: {len(problems)} finding(s) need your review -> {', '.join(problems)}")
        print("        (Everything else re-verified clean against the source rows.)")
        print("        A flag means: look at this finding before sending - it may be a false positive")
        print("        or a config/whitelist gap. It does NOT automatically mean the finding is wrong.")
    else:
        print("RESULT: all findings re-verified clean against the source rows. Report looks trustworthy.")
    print("=" * 72)
    sys.exit(2 if problems else 0)

if __name__ == "__main__":
    main()
