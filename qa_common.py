"""
Universal QA Toolkit — Shared helpers for the data-QA scripts (qa_common.py)
Loading every data sheet with real row numbers, text normalisation, URL/domain
helpers, logging with stage timings, and findings export.
Used by data-validator.py, fuzzy-dedup.py, taxonomy-aligner.py,
fast-dns-verifier.py and brand-existence-checker.py.
"""

import csv
import json
import logging
import os
import re
import sys
import time
import unicodedata
from contextlib import contextmanager
from urllib.parse import urlparse

import pandas as pd

# Columns added to every loaded frame so findings point at the real cell.
SHEET_COL = "_sheet"
ROW_COL = "_row"  # 1-based Excel row (the header is row 1)
META_COLS = (SHEET_COL, ROW_COL)

LOG = logging.getLogger("qa_toolkit")


# --------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------

def add_logging_args(parser):
    """-v / -q flags shared by every script. Logs go to stderr, results to stdout."""
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-v", "--verbose", action="store_true", help="Debug logging")
    group.add_argument("-q", "--quiet", action="store_true", help="Only warnings and errors")


def setup_logging(args=None):
    level = logging.INFO
    if args is not None and getattr(args, "verbose", False):
        level = logging.DEBUG
    elif args is not None and getattr(args, "quiet", False):
        level = logging.WARNING
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    LOG.handlers[:] = [handler]
    LOG.setLevel(level)
    LOG.propagate = False
    return LOG


@contextmanager
def timed(label):
    """Log how long a stage took, so slow steps on large datasets are visible."""
    start = time.perf_counter()
    try:
        yield
    finally:
        LOG.info("%s: %.1f s", label, time.perf_counter() - start)


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------

def _excel_engine(preferred=None):
    """python-calamine reads large workbooks ~8x faster than openpyxl with identical
    values; fall back to openpyxl when it is not installed."""
    if preferred:
        return preferred
    try:
        import python_calamine  # noqa: F401
        return "calamine"
    except ImportError:
        return None  # pandas default (openpyxl)


def load_dataset(path, sheet=None, required_columns=(), engine=None):
    """Read a CSV, or every data sheet of a workbook, into one string frame.

    * Blank cells become "" (never NaN), so string checks never crash.
    * `_sheet` / `_row` hold the source sheet and 1-based Excel row.
    * A sheet is a data sheet when it has every column in `required_columns`
      (or, when none are given, every column of the widest sheet). Companion
      sheets (Change log, Issues log, ...) are skipped and logged, so a workbook
      with a Franchise and a Solo sheet is checked in full, not just its first
      sheet.
    * `sheet` (name or 0-based index) restricts loading to one sheet.
    """
    if not os.path.exists(path):
        print(f"Error: File '{path}' not found.", file=sys.stderr)
        sys.exit(1)

    required = [c for c in required_columns if c]
    if str(path).lower().endswith(".csv"):
        frames = {"csv": pd.read_csv(path, dtype=str, keep_default_na=False)}
    else:
        kwargs = {"dtype": str, "keep_default_na": False}
        eng = _excel_engine(engine)
        if eng:
            kwargs["engine"] = eng
        target = sheet
        if isinstance(target, str) and target.isdigit():
            target = int(target)
        frames = pd.read_excel(path, sheet_name=None if target is None else target, **kwargs)
        if not isinstance(frames, dict):
            frames = {str(target): frames}

    frames = {name: df.rename(columns=lambda c: str(c).strip()).fillna("") for name, df in frames.items()}
    if not required and sheet is None and frames:
        # Generic mode: the widest sheet defines the data columns (log sheets are narrower).
        widest = max(frames.values(), key=lambda d: len(d.columns))
        required = [c for c in widest.columns if not c.startswith("Unnamed:")]

    kept = []
    for name, df in frames.items():
        missing = [c for c in required if c not in df.columns]
        if missing:
            if sheet is not None:
                _fail_missing(path, name, missing, df.columns)
            LOG.info("Skipping sheet '%s' (no %s column)", name, ", ".join(missing[:5]))
            continue
        df = df.astype(str)
        df[SHEET_COL] = str(name)
        df[ROW_COL] = range(2, len(df) + 2)
        kept.append(df)

    if not kept:
        first = next(iter(frames.values()), pd.DataFrame())
        _fail_missing(path, "(all sheets)", required, first.columns)

    data = pd.concat(kept, ignore_index=True, sort=False).fillna("")
    LOG.info(
        "Loaded %s rows from %s (%s)",
        f"{len(data):,}",
        os.path.basename(path),
        ", ".join(f"{d[SHEET_COL].iat[0]}: {len(d):,}" for d in kept if len(d)) or "no rows",
    )
    return data


def _fail_missing(path, sheet, missing, columns):
    print(
        f"Error: {os.path.basename(path)} [{sheet}] has no column(s) {missing}. "
        f"Available columns: {[c for c in columns]}",
        file=sys.stderr,
    )
    sys.exit(1)


def data_columns(df):
    return [c for c in df.columns if c not in META_COLS]


def row_ref(sheet, row):
    return f"{sheet}!{row}"


# --------------------------------------------------------------------------
# Text normalisation
# --------------------------------------------------------------------------

_WS = re.compile(r"\s+")
_NON_ALNUM = re.compile(r"[^0-9a-z]+")


def norm_text(value):
    """Case-, width- and whitespace-insensitive form: '  Nike  Mall ' == 'nike mall'.
    Use it for keys that should not split on '38B' vs '38b' or doubled spaces."""
    text = unicodedata.normalize("NFKC", str(value or ""))
    return _WS.sub(" ", text).strip().casefold()


def strip_accents(text):
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def fold(value):
    """Spelling-variant key: also ignores accents, punctuation and spaces.
    'Bags & More' == 'Bags&More' == 'BAGS-MORE'; 'Müller' == 'Muller'."""
    return _NON_ALNUM.sub("", strip_accents(norm_text(value)))


# Legal-form suffixes that do not change which brand a name refers to.
LEGAL_SUFFIXES = {
    "ltd", "limited", "llc", "lllc", "inc", "plc", "pvt", "corp", "co", "gmbh", "ag",
    "sa", "sas", "sarl", "srl", "spa", "bv", "nv", "doo", "dd", "sro", "as", "ab",
    "oy", "oyj", "kft", "sp", "zoo", "fzco", "fze", "fzllc", "spc",
}


def brand_key(value):
    """fold() after dropping trailing legal-form tokens, so 'Popular Diagnostic
    Centre Ltd.' and 'Popular Diagnostic Centre' share one key. At least one
    token is always kept ('AB' alone stays 'ab')."""
    tokens = [_NON_ALNUM.sub("", strip_accents(t)) for t in norm_text(value).split()]
    tokens = [t for t in tokens if t]
    while len(tokens) > 1 and tokens[-1] in LEGAL_SUFFIXES:
        tokens.pop()
    return "".join(tokens)


def is_blank(value):
    return not str(value or "").strip()


PLACEHOLDER_VALUES = {
    "n/a", "na", "none", "null", "nan", "-", "--", "unknown", "tbd", "tba",
    "not available", "not applicable", "not disclosed", "not publicly disclosed",
    "brand-operated / independent", "various", "multiple", "other", "misc",
}


def is_placeholder(value):
    return norm_text(value) in PLACEHOLDER_VALUES


# Brand-name placeholders seen in delivered datasets ('Brand-Operated / Independent',
# 'Not Publicly Disclosed'). Every row carrying one would become ONE franchise.
_PLACEHOLDER_NAME = re.compile(
    r"brand.?operated|\bindependent\b|not (publicly )?disclosed|not applicable|"
    r"^n/?a$|^various$|^unknown$|^unbranded$|^multiple$|^other$|^misc"
)


def looks_like_placeholder_name(value):
    text = norm_text(value)
    return bool(text) and (text in PLACEHOLDER_VALUES or bool(_PLACEHOLDER_NAME.search(text)))


TRUE_TOKENS = {"y", "yes", "true", "t", "1", "1.0"}
FALSE_TOKENS = {"n", "no", "false", "f", "0", "0.0"}


# --------------------------------------------------------------------------
# URLs and domains
# --------------------------------------------------------------------------

# Second-level labels under which a registrable domain has three labels (co.uk, com.hr).
_SECOND_LEVEL = {"co", "com", "org", "net", "gov", "ac", "edu", "or", "ne", "go"}

# A website column should hold the business's own site. These hosts are profiles,
# listings or link shorteners, not an official website.
SOCIAL_AND_LISTING_DOMAINS = {
    "facebook.com", "fb.com", "fb.me", "instagram.com", "twitter.com", "x.com",
    "linkedin.com", "tiktok.com", "youtube.com", "youtu.be", "pinterest.com",
    "snapchat.com", "wa.me", "whatsapp.com", "t.me", "telegram.me", "linktr.ee",
    "goo.gl", "g.page", "business.site", "maps.app.goo.gl", "tripadvisor.com",
    "yelp.com", "foursquare.com", "zomato.com", "talabat.com", "wolt.com",
}


def host_from_url(value, keep_www=False):
    """'HTTPS://www.Shop.Mango.com:443/x?y' -> 'shop.mango.com' ('' when there is no host).
    keep_www=True keeps a leading 'www.' (DNS lookups need the host as written)."""
    text = str(value or "").strip()
    if not text or is_placeholder(text) or " " in text:
        return ""
    if "://" not in text:
        text = "http://" + text
    try:
        host = urlparse(text).hostname or ""
    except ValueError:
        return ""
    host = host.strip(".").lower()
    if not keep_www and host.startswith("www."):
        host = host[4:]
    return host


def registrable_domain(host):
    """shop.mango.com -> mango.com; www.avis.com.hr -> avis.com.hr. Subdomains
    (store locators, language sites) of one registrable domain are one website."""
    labels = [p for p in str(host or "").split(".") if p]
    if len(labels) < 2:
        return str(host or "")
    keep = 3 if len(labels) >= 3 and labels[-2] in _SECOND_LEVEL else 2
    return ".".join(labels[-keep:])


def url_domain(value):
    return registrable_domain(host_from_url(value))


def social_or_listing(value):
    """Return the matched social/listing domain, or '' for an ordinary website."""
    host = host_from_url(value)
    if not host:
        return ""
    for domain in SOCIAL_AND_LISTING_DOMAINS:
        if host == domain or host.endswith("." + domain):
            return domain
    if host.startswith("google.") or ".google." in host:
        if "/maps" in str(value) or host.startswith("maps."):
            return "google maps"
    return ""


# --------------------------------------------------------------------------
# Config files
# --------------------------------------------------------------------------

def load_list_file(path):
    """One entry per line (blank lines and '#' comments ignored), or the first
    column of a CSV. Used for allowlists and reviewed-exception lists."""
    if not path:
        return []
    if not os.path.exists(path):
        print(f"Error: List file '{path}' not found.", file=sys.stderr)
        sys.exit(1)
    entries = []
    with open(path, encoding="utf-8-sig") as fh:
        if path.lower().endswith(".csv"):
            reader = csv.reader(fh)
            next(reader, None)  # header
            entries = [r[0].strip() for r in reader if r and r[0].strip()]
        else:
            for line in fh:
                line = line.split("#", 1)[0].strip()
                if line:
                    entries.append(line)
    return entries


def load_json(path):
    if not os.path.exists(path):
        print(f"Error: Config file '{path}' not found.", file=sys.stderr)
        sys.exit(1)
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------

def write_records(records, path):
    """Write a list of dicts to .csv or .json (by extension); returns the path."""
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    if path.lower().endswith(".json"):
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(records, fh, indent=2, ensure_ascii=False)
    else:
        fields = []
        for rec in records:
            for key in rec:
                if key not in fields:
                    fields.append(key)
        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fields or ["empty"])
            writer.writeheader()
            writer.writerows(records)
    LOG.info("Wrote %s record(s) to %s", f"{len(records):,}", os.path.abspath(path))
    return path
