"""
Universal QA Toolkit — Data Integrity & Pre-Audit Checker (data-validator.py)
Performs fast sanity checks on raw datasets: null counts, duplicate detection, encoding issues, schema rules.
Author: Azeez

Checks (each is skipped when its columns are absent):
  * null coverage per column
  * duplicates on --dedup-key: exact (as typed) and normalised (case/spacing/width)
  * full-row exact duplicates
  * mojibake (UTF-8 read as Windows-1252), replacement characters, lossy '?', HTML
  * postal codes against the row's country (country_code column, else --country)
  * franchise rules: flag values, missing franchise_name, Solo-row hygiene,
    branch_count vs actual rows, row on the wrong sheet, placeholder names
  * website field: social/listing page instead of a website, malformed URL
  * Google plus codes inside address text
Every sheet with data columns is checked; row numbers are real Excel rows.
"""

import os
import json
import re
import argparse
from collections import defaultdict

import pandas as pd

import qa_common as qc

# --------------------------------------------------------------------------
# Encoding checks
# --------------------------------------------------------------------------

# UTF-8 bytes shown as Windows-1252 text: a lead byte 0xC2-0xF4 followed by
# continuation bytes 0x80-0xBF. Built from the codec so the classes are exact.
def _cp1252_chars(byte_range):
    chars = []
    for b in byte_range:
        try:
            chars.append(bytes([b]).decode("cp1252"))
        except UnicodeDecodeError:
            pass
    return "".join(chars)


_LEAD = re.escape(_cp1252_chars(range(0xC2, 0xF5)))
_CONT = re.escape(_cp1252_chars(range(0x80, 0xC0)))
MOJIBAKE_CANDIDATE = re.compile(f"[{_LEAD}][{_CONT}]+")
REPLACEMENT_PATTERN = re.compile("\uFFFD|ï¿½")
LOSSY_QMARK_PATTERN = re.compile(r"[^\W\d_]\?+[^\W\d_]")
HTML_TAG_PATTERN = re.compile(r"</?[A-Za-z][^<>]*>|&[a-zA-Z]+;|&#\d+;")


def is_mojibake(text):
    """True only when a lead/continuation run really decodes as UTF-8, so
    legitimate text like 'SÃO PAULO' or 'CÂMARA' is not flagged."""
    for match in MOJIBAKE_CANDIDATE.finditer(text):
        try:
            match.group(0).encode("cp1252").decode("utf-8")
            return True
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
    return False


# --------------------------------------------------------------------------
# Postal codes
# --------------------------------------------------------------------------

POSTAL_PATTERNS = {
    "AT": r"\d{4}", "BD": r"\d{4}", "BE": r"\d{4}", "CH": r"\d{4}", "DK": r"\d{4}",
    "LU": r"(L-)?\d{4}", "NO": r"\d{4}", "SI": r"\d{4}", "AU": r"\d{4}",
    "DE": r"\d{5}", "DZ": r"\d{5}", "ES": r"\d{5}", "FI": r"\d{5}", "FR": r"\d{5}",
    "HR": r"\d{5}", "IQ": r"\d{5}", "IT": r"\d{5}", "US": r"\d{5}(-\d{4})?",
    "CZ": r"\d{3} ?\d{2}", "SK": r"\d{3} ?\d{2}", "SE": r"\d{3} ?\d{2}",
    "PL": r"\d{2}-\d{3}", "PT": r"\d{4}-\d{3}", "CL": r"\d{7}", "VN": r"\d{6}",
    "IN": r"\d{6}", "NL": r"\d{4} ?[A-Z]{2}",
    "GB": r"[A-Z]{1,2}\d[A-Z\d]? ?\d[A-Z]{2}",
}
# Countries without a postal-code system: any value is reported, blanks are fine.
NO_POSTAL_SYSTEM = {"AE", "AO", "QA", "HK"}


def check_postal(df, default_country):
    if "postal_code" not in df.columns:
        return [], {}
    if "country_code" in df.columns:
        countries = df["country_code"].str.strip().str.upper()
        if default_country:
            countries = countries.where(countries != "", default_country.upper())
    else:
        countries = pd.Series(default_country.upper() if default_country else "", index=df.index)

    findings, skipped = [], defaultdict(int)
    codes = df["postal_code"].str.strip()
    for country, idx in codes.groupby(countries).groups.items():
        values = codes.loc[idx]
        values = values[values != ""]
        if values.empty:
            continue
        if country in NO_POSTAL_SYSTEM:
            for i, v in values.items():
                findings.append(_finding(df, i, "postal_code", v, "postal_code_where_none_exist",
                                         f"{country} has no postal-code system"))
            continue
        pattern = POSTAL_PATTERNS.get(country)
        if not pattern:
            skipped[country or "(no country)"] += len(values)
            continue
        ok = values.str.fullmatch(pattern, flags=re.IGNORECASE)
        width = _pure_digit_width(pattern)
        for i, v in values[~ok].items():
            if width and v.isdigit() and len(v) < width:
                check = "postal_code_leading_zero_lost"
                detail = f"{country} codes have {width} digits; zeros were likely dropped when stored as a number"
            elif re.fullmatch(r"\d+\.0", v):
                check = "postal_code_numeric_artifact"
                detail = "value was stored as a number"
            else:
                check = "invalid_postal_code"
                detail = f"does not match the {country} format"
            findings.append(_finding(df, i, "postal_code", v, check, detail))
    return findings, dict(skipped)


def _pure_digit_width(pattern):
    m = re.fullmatch(r"\\d\{(\d+)\}", pattern)
    return int(m.group(1)) if m else 0


# --------------------------------------------------------------------------
# Franchise rules
# --------------------------------------------------------------------------

def check_franchise(df, flag_values, placeholder_check=True):
    needed = {"franchise_flag", "franchise_name"}
    if not needed.issubset(df.columns):
        return []
    yes, no = flag_values
    findings = []
    flag = df["franchise_flag"].str.strip()
    name = df["franchise_name"].str.strip()

    for i in df.index[~flag.isin([yes, no])]:
        findings.append(_finding(df, i, "franchise_flag", flag[i], "franchise_flag_value",
                                 f"expected exactly '{yes}' or '{no}'"))

    # Downstream checks read the flag leniently ('Yes', 'TRUE'); the exact spelling
    # is reported once above, so a spelling problem does not hide the others.
    lowered = flag.str.lower()
    is_yes = (flag == yes) | lowered.isin(qc.TRUE_TOKENS)
    is_no = (flag == no) | lowered.isin(qc.FALSE_TOKENS)
    for i in df.index[is_yes & (name == "")]:
        findings.append(_finding(df, i, "franchise_name", "", "franchise_name_missing",
                                 "franchise row without franchise_name"))

    if placeholder_check:
        for i in df.index[is_yes & name.map(qc.looks_like_placeholder_name)]:
            findings.append(_finding(df, i, "franchise_name", name[i], "franchise_name_placeholder",
                                     "placeholder text would merge unrelated businesses into one franchise"))

    solo_dirty = is_no & (name != "")
    if "branch_count" in df.columns:
        solo_dirty |= is_no & (df["branch_count"].str.strip() != "")
    for i in df.index[solo_dirty]:
        findings.append(_finding(df, i, "franchise_name/branch_count", name[i], "solo_row_has_franchise_fields",
                                 "non-franchise row should leave franchise_name and branch_count blank"))

    sheet_lower = df[qc.SHEET_COL].str.lower()
    solo_sheet = sheet_lower.str.contains(r"solo|non[-_ ]?franchise")
    franchise_sheet = sheet_lower.str.contains("franchise") & ~solo_sheet
    wrong_sheet = (solo_sheet & is_yes) | (franchise_sheet & is_no)
    for i in df.index[wrong_sheet]:
        findings.append(_finding(df, i, "franchise_flag", flag[i], "row_on_wrong_sheet",
                                 f"flag '{flag[i]}' on sheet '{df.at[i, qc.SHEET_COL]}'"))

    if "branch_count" in df.columns:
        findings.extend(_branch_count_findings(df, is_yes, name))
    return findings


def _branch_count_findings(df, is_yes, name):
    """branch_count must equal the number of rows carrying the franchise_name.
    Counted per country when a country_code column exists, so a brand present
    in several countries of a combined file is not reported."""
    findings = []
    keys = name.map(qc.norm_text)
    if "country_code" in df.columns:
        keys = keys.where(keys == "", df["country_code"].str.strip().str.upper() + "|" + keys)
    actual = keys[is_yes & (keys != "")].value_counts()
    counts = df["branch_count"].str.strip()
    for i in df.index[is_yes & (keys != "")]:
        stated = counts[i]
        n = int(actual[keys[i]])
        if stated == "":
            findings.append(_finding(df, i, "branch_count", "", "branch_count_missing", f"{n} rows carry this franchise_name"))
            continue
        try:
            value = float(stated)
        except ValueError:
            findings.append(_finding(df, i, "branch_count", stated, "branch_count_not_numeric", ""))
            continue
        if value != n:
            findings.append(_finding(df, i, "branch_count", stated, "branch_count_mismatch",
                                     f"{n} rows carry franchise_name '{name[i]}'"
                                     + (f" in {df.at[i, 'country_code']}" if "country_code" in df.columns else "")))
    return findings


# --------------------------------------------------------------------------
# Website and address
# --------------------------------------------------------------------------

PLUS_CODE_PATTERN = re.compile(r"\b[23456789CFGHJMPQRVWX]{4,8}\+[23456789CFGHJMPQRVWX]{2,3}\b")


def check_website(df, column="website"):
    if column not in df.columns:
        return []
    findings = []
    for i, value in df[column].str.strip().items():
        if not value:
            continue
        social = qc.social_or_listing(value)
        if social:
            findings.append(_finding(df, i, column, value, "website_is_social_or_listing",
                                     f"{social} page, not the business's own website"))
        elif qc.is_placeholder(value):
            findings.append(_finding(df, i, column, value, "website_placeholder", ""))
        elif "." not in qc.host_from_url(value):
            findings.append(_finding(df, i, column, value, "website_malformed", "no valid host name"))
    return findings


def check_plus_codes(df):
    findings = []
    for col in ("address", "formatted_address"):
        if col not in df.columns:
            continue
        hits = df[col].str.contains(PLUS_CODE_PATTERN, na=False)
        for i in df.index[hits]:
            findings.append(_finding(df, i, col, df.at[i, col], "plus_code_in_address",
                                     "Google plus code instead of a street address"))
    return findings


# --------------------------------------------------------------------------
# Encoding, whitespace
# --------------------------------------------------------------------------

def check_encoding(df, url_columns=("website",)):
    findings = []
    prefilter = re.compile(f"{MOJIBAKE_CANDIDATE.pattern}|{REPLACEMENT_PATTERN.pattern}|\\?|<|&")
    for col in qc.data_columns(df):
        series = df[col]
        candidates = series[series.str.contains(prefilter, na=False)]
        for i, val in candidates.items():
            if REPLACEMENT_PATTERN.search(val):
                findings.append(_finding(df, i, col, val, "Mojibake/Encoding Corruption", "replacement character"))
            elif is_mojibake(val):
                findings.append(_finding(df, i, col, val, "Mojibake/Encoding Corruption", "UTF-8 text decoded as Windows-1252"))
            elif col not in url_columns and "://" not in val and LOSSY_QMARK_PATTERN.search(val):
                findings.append(_finding(df, i, col, val, "Lossy Encoding ('?' replacement)", "letters replaced by '?'"))
            elif col not in url_columns and HTML_TAG_PATTERN.search(val):
                findings.append(_finding(df, i, col, val, "Unstripped HTML Tag", ""))
    return findings


def check_whitespace(df):
    findings = []
    for col in qc.data_columns(df):
        series = df[col]
        bad = (series != series.str.strip()) | series.str.contains(r"\s{2,}", na=False)
        for i in df.index[bad]:
            findings.append(_finding(df, i, col, series[i], "untrimmed_or_double_spaces",
                                     "splits otherwise identical values in exact-match checks"))
    return findings


# --------------------------------------------------------------------------
# Duplicates
# --------------------------------------------------------------------------

def check_duplicates(df, keys):
    """Exact duplicates on the key (original behaviour), plus a normalised pass that
    also catches case / spacing / width variants ('38B' vs '38b', 'Mall' vs ' Mall')."""
    exact_mask = df.duplicated(subset=keys, keep=False)
    blank_key = (df[keys].apply(lambda s: s.str.strip() == "")).any(axis=1)
    normed = df[keys].apply(lambda s: s.map(qc.norm_text))
    norm_mask = normed.duplicated(keep=False) & ~blank_key

    findings = []
    groups = normed[norm_mask].groupby(list(normed.columns), sort=False).groups
    for _key, idx in groups.items():
        refs = [qc.row_ref(df.at[i, qc.SHEET_COL], df.at[i, qc.ROW_COL]) for i in idx]
        variant = df.loc[idx, keys].drop_duplicates().shape[0] > 1
        for i in idx:
            findings.append(_finding(
                df, i, ",".join(keys), " | ".join(df.loc[i, keys]),
                "duplicate_key_variant" if variant else "duplicate_key",
                f"{len(idx)} rows share this key: {', '.join(refs)}",
            ))
    summary = {
        "keys_checked": keys,
        "duplicate_rows": int(exact_mask.sum()),
        "unique_rows": int(len(df) - exact_mask.sum()),
        "duplicate_rows_normalized": int(norm_mask.sum()),
        "rows_with_blank_key_part": int(blank_key.sum()),
    }
    return summary, findings


def check_full_row_duplicates(df):
    cols = qc.data_columns(df)
    mask = df.duplicated(subset=cols, keep=False)
    findings = [
        _finding(df, i, "(all columns)", df.at[i, cols[0]] if cols else "", "exact_duplicate_row", "")
        for i in df.index[mask]
    ]
    return int(mask.sum()), findings


# --------------------------------------------------------------------------

def _finding(df, i, column, value, check, detail):
    return {
        "sheet": df.at[i, qc.SHEET_COL],
        "row": int(df.at[i, qc.ROW_COL]),
        "column": column,
        "value": value,
        "type": check,
        "detail": detail,
    }


def audit_dataset(file_path, checks=None, dedup_key=None, country_code=None, sheet=None,
                  output=None, samples=10, flag_values=("Y", "N"), engine=None):
    """Run automated sanity checks on an Excel or CSV file."""
    with qc.timed("Load"):
        df = qc.load_dataset(file_path, sheet=sheet, engine=engine)
    cols = qc.data_columns(df)
    total_rows = len(df)
    results = {
        "dataset": os.path.basename(file_path),
        "sheets": {s: int(n) for s, n in df[qc.SHEET_COL].value_counts(sort=False).items()},
        "total_rows": total_rows,
        "total_columns": len(cols),
        "issues_summary": {},
        "findings": [],
    }
    findings = []

    with qc.timed("Null coverage"):
        null_summary = {}
        for col in cols:
            empty_count = int((df[col].str.strip() == "").sum())
            if empty_count > 0:
                null_summary[col] = {
                    "empty_rows": empty_count,
                    "empty_percentage": f"{(empty_count / total_rows) * 100:.1f}%",
                }
        results["null_coverage"] = null_summary

    with qc.timed("Duplicates"):
        full_dupes, full_findings = check_full_row_duplicates(df)
        results["exact_duplicate_rows_all_columns"] = full_dupes
        findings += full_findings
        if dedup_key:
            requested = [k.strip() for k in dedup_key.split(",") if k.strip()]
            keys = [k for k in requested if k in df.columns]
            missing = [k for k in requested if k not in df.columns]
            if missing:
                qc.LOG.warning("Dedup key column(s) not found and ignored: %s", missing)
            if keys:
                results["duplicates"], dup_findings = check_duplicates(df, keys)
                findings += dup_findings

    with qc.timed("Encoding"):
        enc = check_encoding(df)
        findings += enc
        results["encoding_issues_count"] = len(enc)
        if enc:
            results["encoding_samples"] = enc[:samples]

    with qc.timed("Postal codes"):
        postal, skipped = check_postal(df, country_code)
        findings += postal
        results["invalid_postal_codes_count"] = len(postal)
        if postal:
            results["invalid_postal_samples"] = postal[:samples]
        if skipped:
            results["postal_check_skipped_no_pattern"] = skipped

    with qc.timed("Franchise, website, address"):
        findings += check_franchise(df, flag_values)
        findings += check_website(df)
        findings += check_plus_codes(df)
        findings += check_whitespace(df)

    by_type = defaultdict(list)
    for f in findings:
        by_type[f["type"]].append(f)
    results["issues_summary"] = {t: len(v) for t, v in sorted(by_type.items(), key=lambda kv: -len(kv[1]))}
    results["findings"] = [f for v in by_type.values() for f in v[:samples]]
    if output:
        qc.write_records(findings, output)
        results["findings_file"] = os.path.abspath(output)

    print(json.dumps(results, indent=2, ensure_ascii=False))
    return results, findings


def main():
    parser = argparse.ArgumentParser(description="Data Integrity Checker (data-validator.py)")
    parser.add_argument("file", help="Path to Excel or CSV file")
    parser.add_argument("--dedup-key", help="Comma-separated column names to check for duplicates")
    parser.add_argument("--country", default=None,
                        help="Country code for rows without a country_code value (postal-code rules). "
                             "The country_code column is used when present.")
    parser.add_argument("--sheet", default=None, help="Only check this sheet (name or 0-based index). Default: every data sheet")
    parser.add_argument("--output", help="Write every finding to this .csv or .json file")
    parser.add_argument("--samples", type=int, default=10, help="Findings shown per check in the JSON summary (default: 10)")
    parser.add_argument("--flag-values", default="Y,N", help="Allowed franchise_flag values as YES,NO (default: Y,N)")
    parser.add_argument("--engine", default=None, help="Excel reader engine (default: calamine if installed, else openpyxl)")
    qc.add_logging_args(parser)

    args = parser.parse_args()
    qc.setup_logging(args)
    flags = tuple(v.strip() for v in args.flag_values.split(","))
    if len(flags) != 2:
        parser.error("--flag-values takes exactly two values, e.g. Y,N")
    audit_dataset(args.file, dedup_key=args.dedup_key, country_code=args.country, sheet=args.sheet,
                  output=args.output, samples=args.samples, flag_values=flags, engine=args.engine)


if __name__ == "__main__":
    main()
