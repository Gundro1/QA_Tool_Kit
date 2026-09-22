"""
Universal QA Toolkit — Fuzzy Duplicate & Name-Variant Detector (fuzzy-dedup.py)

Three result tiers, so near-miss names do not drown the real problems:
  spelling_variant       One name written several ways ('Bags & More' / 'Bags&More',
                         'Dosenbach + Sport' / 'Dosenbach +Sport', 'X Ltd.' / 'X'): identical
                         after ignoring case, accents, spaces, punctuation and a trailing
                         legal-form suffix. Checked across
                         the whole dataset; each variant becomes its own franchise group.
  same_address_duplicate Similar or variant names at the same normalised address in the
                         same city: very likely one branch listed twice.
  similar_name           Similar names in the same city with nothing contradicting a match.
                         Review only.
Pairs that evidence says are different businesses are counted as suppressed, not
reported: different website domains (Pull & Bear vs Bull & Bear, NRB vs NRBC Bank,
Kia vs Skoda dealers) or the same website with different addresses (two branches of
one brand, e.g. two Ibis Styles hotels). --show-suppressed lists them too.

Uses rapidfuzz when installed (much faster on large cities); falls back to difflib.
"""

import argparse
from collections import defaultdict
from difflib import SequenceMatcher

import numpy as np
import pandas as pd

import qa_common as qc

try:
    from rapidfuzz import fuzz, process
except ImportError:  # optional speed-up
    fuzz = process = None

_CHUNK = 500  # rows per rapidfuzz cdist block: 500 x 70k names x 1 byte = 35 MB


def string_similarity(a, b):
    if not isinstance(a, str) or not isinstance(b, str):
        return 0.0
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def _similar_pairs(names, threshold):
    """Yield (i, j, score) for name pairs with similarity >= threshold (0..1)."""
    n = len(names)
    if n < 2:
        return
    if process is not None:
        cutoff = int(np.ceil(threshold * 100))
        for start in range(0, n, _CHUNK):
            block = process.cdist(names[start:start + _CHUNK], names, scorer=fuzz.ratio,
                                  score_cutoff=cutoff, dtype=np.uint8, workers=-1)
            rows, cols = block.nonzero()
            for r, c in zip(rows, cols):
                i = start + int(r)
                if i < c:
                    yield i, int(c), float(block[r, c]) / 100
        return
    for i in range(n):
        a = names[i]
        for j in range(i + 1, n):
            b = names[j]
            la, lb = len(a), len(b)
            if 2 * min(la, lb) / (la + lb) < threshold:  # upper bound of ratio()
                continue
            m = SequenceMatcher(None, a, b)
            if m.real_quick_ratio() >= threshold and m.quick_ratio() >= threshold:
                score = m.ratio()
                if score >= threshold:
                    yield i, j, score


def _prepare(df, name_column, city_column, address_column, website_column):
    work = pd.DataFrame({
        "sheet": df[qc.SHEET_COL],
        "row": df[qc.ROW_COL].astype(int),
        "name": df[name_column].str.strip(),
    })
    work["norm"] = work["name"].map(qc.norm_text)
    work["fold"] = work["name"].map(qc.brand_key)
    work["city"] = df[city_column].map(qc.norm_text) if city_column in df.columns else ""
    work["address"] = df[address_column].map(qc.norm_text) if address_column in df.columns else ""
    work["domain"] = df[website_column].map(qc.url_domain) if website_column in df.columns else ""
    return work[work["fold"] != ""]


def _refs(rows):
    return ", ".join(qc.row_ref(s, r) for s, r in zip(rows["sheet"], rows["row"]))


def spelling_variants(work):
    findings = []
    for _key, grp in work.groupby("fold", sort=False):
        spellings = grp["name"].value_counts()
        if len(spellings) < 2:
            continue
        case_only = grp["norm"].nunique() == 1
        findings.append({
            "tier": "spelling_variant",
            "name_1": spellings.index[0],
            "name_2": " | ".join(spellings.index[1:]),
            "similarity": 1.0,
            "city": "",
            "case_only": case_only,
            "reason": ("case/spacing only" if case_only
                       else "differs only in punctuation, accents, spacing or a legal suffix (Ltd, GmbH, d.o.o.)")
                      + "; counts: " + ", ".join(f"{n!r}={c}" for n, c in spellings.items()),
            "rows": _refs(grp),
        })
    return findings


def _classify(rows_a, rows_b, keep_different_domains):
    """Different website domains outweigh a shared address: two banks on the same
    road or two brands in one multi-brand dealership share an address but are
    different businesses (NRB / NRBC Bank, Kia / Skoda dealer networks)."""
    addr_a = set(rows_a["address"]) - {""}
    addr_b = set(rows_b["address"]) - {""}
    shared = addr_a & addr_b
    dom_a = set(rows_a["domain"]) - {""}
    dom_b = set(rows_b["domain"]) - {""}
    if dom_a and dom_b and not (dom_a & dom_b) and not keep_different_domains:
        return "suppressed_different_websites", f"{sorted(dom_a)[0]} vs {sorted(dom_b)[0]}"
    if shared:
        return "same_address_duplicate", f"same address: {sorted(shared)[0]!r}"
    if dom_a and dom_b and not (dom_a & dom_b):
        return "similar_name", f"different websites ({sorted(dom_a)[0]} vs {sorted(dom_b)[0]})"
    if dom_a & dom_b and addr_a and addr_b:
        return "suppressed_same_brand_other_branch", f"one website ({sorted(dom_a & dom_b)[0]}), different addresses"
    return "similar_name", "similar names, no contradicting evidence"


def similar_names(work, threshold, keep_different_domains):
    findings, suppressed = [], defaultdict(int)
    for city, grp in work.groupby("city", sort=False):
        by_fold = {k: g for k, g in grp.groupby("fold", sort=False)}
        keys = list(by_fold)
        labels = [by_fold[k]["norm"].iat[0] for k in keys]
        for i, j, score in _similar_pairs(labels, threshold):
            rows_a, rows_b = by_fold[keys[i]], by_fold[keys[j]]
            tier, reason = _classify(rows_a, rows_b, keep_different_domains)
            if tier.startswith("suppressed"):
                suppressed[tier] += 1
            findings.append({
                "tier": tier,
                "name_1": rows_a["name"].iat[0],
                "name_2": rows_b["name"].iat[0],
                "similarity": round(score, 3),
                "city": city,
                "reason": reason,
                "rows": _refs(pd.concat([rows_a, rows_b])),
            })
    return findings, dict(suppressed)


def find_fuzzy_duplicates(excel_path, name_column="business_name", city_column="city", threshold=0.85,
                          address_column="address", website_column="website", output=None, top=15,
                          sheet=None, keep_different_domains=False, show_suppressed=False, engine=None):
    with qc.timed("Load"):
        df = qc.load_dataset(excel_path, sheet=sheet, required_columns=[name_column], engine=engine)
    if city_column not in df.columns:
        qc.LOG.warning("Column '%s' not found: comparing names across the whole dataset", city_column)

    engine_name = "rapidfuzz" if process is not None else "difflib (pip install rapidfuzz for speed)"
    print(f"Scanning {len(df):,} rows for fuzzy duplicate business listings "
          f"(threshold: {threshold*100:.0f}% similarity, engine: {engine_name})...")

    with qc.timed("Prepare"):
        work = _prepare(df, name_column, city_column, address_column, website_column)
    with qc.timed("Spelling variants"):
        variants = spelling_variants(work)
    with qc.timed("Similar names"):
        pairs, suppressed = similar_names(work, threshold, keep_different_domains)

    reported = variants + [p for p in pairs if not p["tier"].startswith("suppressed")]
    tiers = defaultdict(int)
    for f in reported:
        tiers[f["tier"]] += 1

    print("\n" + "=" * 60)
    print("FUZZY DUPLICATE DETECTION RESULTS")
    print("=" * 60)
    print(f"Spelling variants (one name, several spellings): {tiers['spelling_variant']:,}")
    print(f"Same-address duplicates (similar names)        : {tiers['same_address_duplicate']:,}")
    print(f"Similar names to review                        : {tiers['similar_name']:,}")
    print(f"Suppressed as different businesses             : {sum(suppressed.values()):,} {dict(suppressed) or ''}")
    print(f"Total Fuzzy Duplicate Pairs Found: {tiers['same_address_duplicate'] + tiers['similar_name']:,}")
    print("=" * 60)

    order = {"same_address_duplicate": 0, "spelling_variant": 1, "similar_name": 2}
    # Case-only variants rank last: a lower-cased group key already merges them.
    ranked = sorted(reported, key=lambda f: (order[f["tier"]], f.get("case_only", False), -f["similarity"]))
    if ranked:
        print(f"\nTop {top} findings:")
        for f in ranked[:top]:
            print(f"  [{f['tier']}] {f['name_1']!r} <--> {f['name_2']!r} "
                  f"({f['similarity']*100:.1f}%) [{f['city'] or 'all'}] {f['reason']}")

    if output:
        records = ranked + ([p for p in pairs if p["tier"].startswith("suppressed")] if show_suppressed else [])
        qc.write_records(records, output)
    return ranked, suppressed


def main():
    parser = argparse.ArgumentParser(description="High-Speed Fuzzy Duplicate Store Listing Detector")
    parser.add_argument("excel_path", help="Path to target Excel dataset")
    parser.add_argument("--name-col", default="business_name", help="Business name column (default: business_name)")
    parser.add_argument("--city-col", default="city", help="City column (default: city)")
    parser.add_argument("--address-col", default="address", help="Address column used as evidence (default: address)")
    parser.add_argument("--website-col", default="website", help="Website column used as evidence (default: website)")
    parser.add_argument("--threshold", type=float, default=0.85, help="Similarity ratio threshold (0.5 to 1.0, default: 0.85)")
    parser.add_argument("--sheet", default=None, help="Only this sheet (default: every sheet with the name column)")
    parser.add_argument("--output", help="Write every finding to this .csv or .json file")
    parser.add_argument("--top", type=int, default=15, help="Findings printed to the console (default: 15)")
    parser.add_argument("--keep-different-domains", action="store_true",
                        help="Report similar names even when their websites are different domains")
    parser.add_argument("--show-suppressed", action="store_true", help="Include suppressed pairs in --output")
    parser.add_argument("--engine", default=None, help="Excel reader engine (default: calamine if installed)")
    qc.add_logging_args(parser)
    args = parser.parse_args()
    qc.setup_logging(args)
    if not 0.5 <= args.threshold <= 1.0:
        parser.error("--threshold must be between 0.5 and 1.0")

    find_fuzzy_duplicates(args.excel_path, args.name_col, args.city_col, args.threshold,
                          address_column=args.address_col, website_column=args.website_col,
                          output=args.output, top=args.top, sheet=args.sheet,
                          keep_different_domains=args.keep_different_domains,
                          show_suppressed=args.show_suppressed, engine=args.engine)


if __name__ == "__main__":
    main()
