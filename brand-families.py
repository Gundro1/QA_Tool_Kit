"""
Universal QA Toolkit - Brand-Family Detector (brand-families.py)

One real brand written under several names: 'KFC' / 'Kfc' / 'KFC Iraq', 'Credit Bank' / 'Credit Bank of Iraq',
'Dosenbach + Sport' / 'Dosenbach +Sport'. fuzzy-dedup.py compares spellings inside one file, per city; this tool compares
NAMES with each other across the whole country and, when given several files, across files. Run it on the merged/compiled
dataset AND on the separate misrep + scraping files (each file's source label shows where a name came from): a pair that
only meets after the merge is the Iraq case.

Kinds (HIGH = fix or justify, MEDIUM = review):
  case_variant        HIGH    same name, different capitalisation (never rewritten to lower case)
  spelling_variant    HIGH    differs only in punctuation, accents, spacing
  country_qualifier   HIGH    same name once country words / Ltd / 'of' are ignored (Credit Bank = Credit Bank of Iraq)
  shared_domain       HIGH*   one own-website under several names (*MEDIUM when the names are unrelated: group portal)
  domain_family       MEDIUM  websites share the brand word (kfc.com / kfc.bz / kfcbd.bz)
  contained_name      MEDIUM  one name is the start/end of another
  branch_suffix       MEDIUM  name = brand + a city/region in the dataset
  abbreviation        MEDIUM  NBI vs National Bank of Iraq
  name_format         MEDIUM  listed acronym in Title Case ('Kfc'), ALL CAPS, all lower, "Hardee'S"

Nothing is renamed automatically. Review the report, then write a decisions file
  {"same": {"Kfc": "KFC", "Credit Bank of Iraq": "Credit Bank"}, "distinct": [["Orange", "Orange Money"]]}
and re-run with --decisions (distinct pairs stop being reported) and --apply OUT.xlsx (renames reviewed variants, writes a
'Brand Name Change Log' sheet). Per-country knowledge (country words, acronyms) lives in brand_name_rules.json.
"""
import argparse
import os
from collections import Counter

import pandas as pd

import brand_family as bf
import qa_common as qc


def _entries(paths, name_cols, website_col, sheet):
    entries = []
    for path in paths:
        label = os.path.splitext(os.path.basename(path))[0]
        df = qc.load_dataset(path, sheet=sheet, required_columns=[name_cols[0]])
        for col in name_cols:
            if col not in df.columns:
                continue
            for name, site, shn, row in zip(df[col], df[website_col] if website_col in df.columns else [""] * len(df),
                                            df[qc.SHEET_COL], df[qc.ROW_COL]):
                if str(name).strip():
                    entries.append({"name": name, "website": site, "source": label, "ref": f"{label}:{shn}!{row}:{col}"})
    return entries


def find_brand_families(paths, country=None, name_cols=("business_name", "franchise_name"), website_col="website",
                        decisions=None, sheet=None, output=None, top=15):
    paths = [paths] if isinstance(paths, str) else list(paths)
    entries = _entries(paths, list(name_cols), website_col, sheet)
    decisions = decisions or {}
    rules = bf.rules_with_decisions(bf.load_rules(country), decisions)
    findings = bf.find_families(entries, rules)
    kinds = Counter((f["severity"], f["kind"]) for f in findings)
    print("\n" + "=" * 60 + "\nBRAND-FAMILY RESULTS\n" + "=" * 60)
    print(f"{len({e['name'] for e in entries}):,} distinct names in {len(entries):,} cells over {len(paths)} file(s)")
    for (sev, kind), n in sorted(kinds.items(), key=lambda x: (x[0][0] != "HIGH", x[0][1])):
        print(f"  {sev:6} {kind:18} {n:,}")
    cross = sum(f["cross_source"] for f in findings)
    print(f"  of which names from different files: {cross:,}")
    for f in findings[:top]:
        print(f"  [{f['severity']}/{f['kind']}] {' | '.join(f['names'][:5])} -> {f['suggested']!r}: {f['reason'][:90]}")
    if output:
        qc.write_records([{**f, "names": " | ".join(f["names"]), "domains": ", ".join(f["domains"]),
                           "sources": ", ".join(f["sources"]),
                           "name_sources": "; ".join(f"{n}<-{','.join(s)}" for n, s in f["name_sources"].items()),
                           "counts": ", ".join(f"{n}={c}" for n, c in f["counts"].items())} for f in findings], output)
    return findings


def apply_to_workbook(path, decisions, out_path, name_cols=("business_name", "franchise_name")):
    """Rename reviewed variants in every sheet that has the name columns; log each change on its own sheet."""
    sheets = pd.read_excel(path, sheet_name=None, dtype=str, keep_default_na=False)
    log = []
    for name, df in sheets.items():
        cols = [c for c in name_cols if c in df.columns]
        if not cols:
            continue
        rows, changes = bf.apply_decisions(df.to_dict("records"), decisions, cols)
        sheets[name] = pd.DataFrame(rows, columns=df.columns)
        log += [{"sheet": name, "excel_row": c["row_index"] + 2, "field": c["field"], "old": c["old"], "new": c["new"]} for c in changes]
    sheets["Brand Name Change Log"] = pd.DataFrame(log, columns=["sheet", "excel_row", "field", "old", "new"])
    with pd.ExcelWriter(out_path) as xw:
        for name, df in sheets.items():
            df.to_excel(xw, sheet_name=name[:31], index=False)
    print(f"Renamed {len(log):,} cell(s); wrote {out_path}")
    return log


def main():
    ap = argparse.ArgumentParser(description="Detect one brand written under several names (within and across files)")
    ap.add_argument("files", nargs="+", help="One or more .xlsx/.csv datasets (pass misrep + scraping + merged together)")
    ap.add_argument("--country", help="ISO2 code for country words/acronyms in brand_name_rules.json (e.g. IQ)")
    ap.add_argument("--name-col", action="append", help="Name column(s); default business_name and franchise_name")
    ap.add_argument("--website-col", default="website")
    ap.add_argument("--sheet", default=None)
    ap.add_argument("--decisions", help="JSON with the review outcome: {'same': {variant: canonical}, 'distinct': [[a, b]]}")
    ap.add_argument("--apply", metavar="OUT.xlsx", help="Apply the 'same' decisions to the first file and write OUT.xlsx")
    ap.add_argument("--output", help="Write every finding to .csv or .json")
    ap.add_argument("--top", type=int, default=15)
    qc.add_logging_args(ap)
    args = ap.parse_args()
    qc.setup_logging(args)
    decisions = bf.load_decisions(args.decisions)
    cols = tuple(args.name_col) if args.name_col else ("business_name", "franchise_name")
    find_brand_families(args.files, args.country, cols, args.website_col, decisions, args.sheet, args.output, args.top)
    if args.apply:
        if not decisions.get("same"):
            ap.error("--apply needs --decisions with a non-empty 'same' map")
        apply_to_workbook(args.files[0], decisions, args.apply, cols)


if __name__ == "__main__":
    main()
