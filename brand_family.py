"""Brand-family detector: one real brand written under several names inside (or across) datasets.

Staging showed "KFC", "Kfc", KFC on kfc.com and KFC on kfcbd.bz as separate brands, and Iraq's merge put "Credit Bank"
(misrep file) beside "Credit Bank of Iraq" (scraping file). Repeating a name across branches is correct (see the
business_name rule); the defect is DIFFERENT names for the same brand. Exact grouping on business_name/franchise_name
can never see it, so this module compares names to each other.

Rules it follows:
  * Detection never rewrites a name to lower case; case is compared, not normalised away. A name that is only
    upper-/lower-case is a format finding unless it is a known acronym (rules file, per country).
  * It FLAGS and SUGGESTS a canonical spelling. Only `apply_decisions` renames, and only from a decisions file a person
    reviewed (`same` map) - these cases cannot be fully automated.
  * Findings carry `cross_source=True` when the names come from different files (misrep vs scraping vs prior round),
    which is the merge case QA hit on Iraq.

Pure standard library. Keep the three copies (scraping `bisviews/`, `QA_Tool_Kit/`, `misrep_toolkit/`) identical:
`tests/test_brand_family.py` fails when they drift.
"""
from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from urllib.parse import urlparse

RULES_FILE = Path(__file__).with_name("brand_name_rules.json")

_NON_ALNUM = re.compile(r"[\W_]+", re.UNICODE)
_UNFOLDED = str.maketrans({"đ": "d", "ł": "l", "ø": "o", "ß": "ss", "æ": "ae", "œ": "oe"})
SEVERITY = {"case_variant": "HIGH", "spelling_variant": "HIGH", "country_qualifier": "HIGH", "shared_domain": "HIGH",
            "domain_family": "MEDIUM", "contained_name": "MEDIUM", "branch_suffix": "MEDIUM", "abbreviation": "MEDIUM", "name_format": "MEDIUM"}
# listings/social hosts are not a brand's own site; two brands on them prove nothing
NOT_OWN_SITE = {"facebook.com", "fb.com", "instagram.com", "linktr.ee", "wixsite.com", "google.com", "business.site",
                "linkedin.com", "twitter.com", "x.com", "youtube.com", "tiktok.com", "wa.me", "wordpress.com", "blogspot.com"}
_SECOND_LEVEL = {"co", "com", "org", "net", "gov", "ac", "edu", "or", "ne", "go"}


def load_rules(country: str | None = None, path: Path | None = None, country_name: str | None = None) -> dict:
    """Merge the `_default` block with the country's block (lists are united, dicts are updated)."""
    data = json.loads((path or RULES_FILE).read_text(encoding="utf-8"))
    merged: dict = {"country_tokens": [], "qualifier_words": [], "stop_words": [], "acronyms": [], "generic_words": [],
                    "distinct_pairs": []}
    for block in (data.get("_default", {}), data.get((country or "").upper(), {})):
        for k, v in block.items():
            if isinstance(v, list):
                merged[k] = merged.get(k, []) + [x for x in v if x not in merged.get(k, [])]
            elif isinstance(v, dict):
                merged[k] = {**merged.get(k, {}), **v}
    if country_name:
        merged["country_tokens"] += [t for t in (country_name, country_name.split()[0]) if t not in merged["country_tokens"]]
    return merged


def _ascii(text: str) -> str:
    t = unicodedata.normalize("NFKD", unicodedata.normalize("NFKC", str(text or "")).casefold()).translate(_UNFOLDED)
    return "".join(c for c in t if not unicodedata.combining(c))


def tokens(name: str) -> list[str]:
    """Case-folded, accent-folded word tokens ('Crédit-Bank  Iraq' -> ['credit', 'bank', 'iraq']); Arabic etc. kept."""
    return [t for t in _NON_ALNUM.split(_ascii(name)) if t]


def case_key(name: str) -> str:
    """Detection key only (never written back): 'KFC' == 'Kfc' == ' kfc '."""
    return " ".join(str(name or "").split()).casefold()


_BLANK_SITE = {"nan", "none", "null", "n/a", "na", "-", ""}


def registrable_domain(url: str | None) -> str:
    if not url or str(url).strip().lower() in _BLANK_SITE:
        return ""
    host = (urlparse(url if "//" in str(url) else "//" + str(url)).hostname or "").lower().removeprefix("www.")
    parts = host.split(".")
    if len(parts) >= 3 and parts[-2] in _SECOND_LEVEL and len(parts[-1]) == 2:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def domain_label(url: str | None) -> str:
    dom = registrable_domain(url)
    return dom.split(".")[0] if dom else ""


def core_tokens(name: str, rules: dict) -> tuple[str, ...]:
    """Tokens left once country words, qualifiers ('group', 'ltd'), stop words ('of', 'the') are removed."""
    drop = {_ascii(x) for x in rules["country_tokens"] + rules["qualifier_words"] + rules["stop_words"]}
    toks = [t for t in tokens(name) if t not in drop]
    return tuple(toks) if toks else tuple(tokens(name))


def is_acronym(name: str, rules: dict) -> bool:
    return name in set(rules["acronyms"])


def format_problem(name: str, rules: dict) -> str | None:
    """Casing defect of a single name; scripts without case (Arabic, CJK) never trip it."""
    letters = [c for c in name if c.isalpha() and (c.isupper() or c.islower())]
    if len(letters) < 4 or is_acronym(name, rules):
        return None
    if all(c.isupper() for c in letters):
        return "ALL CAPS (not a listed acronym)"
    if all(c.islower() for c in letters):
        return "all lower case"
    return None


def _stats(entries: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for e in entries:
        name = " ".join(str(e.get("name") or "").split())
        if not name:
            continue
        s = out.setdefault(name, {"name": name, "n": 0, "domains": set(), "sources": set(), "refs": []})
        s["n"] += 1
        dom = registrable_domain(e.get("website"))
        if dom:
            s["domains"].add(dom)
        s["sources"].add(e.get("source") or "")
        if len(s["refs"]) < 6:
            s["refs"].append(e.get("ref") or "")
    return out


def _canonical(group: list[dict], rules: dict) -> str:
    """Suggestion only: a listed acronym wins, then a mixed-case spelling, then the most frequent, then the shortest."""
    acr = [g for g in group if is_acronym(g["name"], rules)]
    if acr:
        return max(acr, key=lambda g: g["n"])["name"]
    ok = [g for g in group if not format_problem(g["name"], rules)] or group
    return sorted(ok, key=lambda g: (-g["n"], len(g["name"]), g["name"]))[0]["name"]


def _finding(kind: str, group: list[dict], rules: dict, reason: str, severity: str | None = None) -> dict:
    sources = sorted(set().union(*(g["sources"] for g in group)))
    return {"kind": kind, "severity": severity or SEVERITY[kind], "names": [g["name"] for g in group],
            "counts": {g["name"]: g["n"] for g in group}, "suggested": _canonical(group, rules),
            "domains": sorted(set().union(*(g["domains"] for g in group))), "sources": sources,
            "name_sources": {g["name"]: sorted(g["sources"]) for g in group},
            "cross_source": len(sources) > 1, "reason": reason,
            "refs": "; ".join(r for g in group for r in g["refs"][:3])}


def _distinct(rules: dict) -> set[frozenset]:
    return {frozenset(case_key(x) for x in p) for p in rules["distinct_pairs"]}


def find_families(entries: list[dict], rules: dict | None = None, country: str | None = None) -> list[dict]:
    """entries: dicts with name, website, source, ref. Returns findings, most severe / cross-source first."""
    rules = rules or load_rules(country)
    stats = _stats(entries)
    names = list(stats)
    distinct = _distinct(rules)
    seen: set[tuple] = set()
    findings: list[dict] = []

    def emit(kind: str, group_names: list[str], reason: str, severity: str | None = None) -> None:
        key = (kind, frozenset(group_names))
        if key in seen or any(frozenset((case_key(a), case_key(b))) in distinct for a, b in combinations(group_names, 2)):
            return
        seen.add(key)
        findings.append(_finding(kind, [stats[n] for n in group_names], rules, reason, severity))

    # 1 case variants: identical except for capitalisation / spacing
    by_case = defaultdict(list)
    for n in names:
        by_case[case_key(n)].append(n)
    for grp in by_case.values():
        if len(grp) > 1:
            emit("case_variant", grp, "same name, different capitalisation: " + ", ".join(f"{n!r}x{stats[n]['n']}" for n in grp))
    # 2 spelling variants: same letters/digits once case, accents, punctuation, spaces are ignored
    by_sp = defaultdict(list)
    for n in names:
        by_sp["".join(tokens(n))].append(n)
    for grp in by_sp.values():
        if len(grp) > 1 and not all(case_key(n) == case_key(grp[0]) for n in grp):
            emit("spelling_variant", grp, "differs only in punctuation, accents or spacing")
    generic = {_ascii(w) for w in rules["generic_words"]}
    # 3 country / qualifier variants: 'Credit Bank' vs 'Credit Bank of Iraq' vs 'Credit Bank Iraq'
    by_core = defaultdict(list)
    for n in names:
        by_core[core_tokens(n, rules)].append(n)
    for core, grp in by_core.items():
        if len(grp) > 1 and len({"".join(tokens(n)) for n in grp}) > 1 and not set(core) <= generic:
            emit("country_qualifier", grp, f"same core name {' '.join(core)!r} once country/qualifier words are ignored")
    # 4 same own-website domain under different names
    by_dom = defaultdict(list)
    for n in names:
        for d in stats[n]["domains"]:
            if d not in NOT_OWN_SITE:
                by_dom[d].append(n)
    for dom, grp in by_dom.items():
        if len(grp) > 1:
            # names that open with the same word are one brand written several ways; unrelated names on one site are a
            # group portal (accor.com, marriott.com): worth a look, not a defect
            related = len({core_tokens(n, rules)[:1] for n in grp}) == 1
            emit("shared_domain", grp, f"one website ({dom}) under {len(grp)} names" + ("" if related else " (unrelated names: group portal?)"),
                 "HIGH" if related else "MEDIUM")
    # 5 domain family: kfc.com / kfc.bz / kfcbd.bz carrying the same brand word
    by_label = defaultdict(set)
    for n in names:
        for d in stats[n]["domains"]:
            if d not in NOT_OWN_SITE and domain_label(d):
                by_label[domain_label(d)].add(n)
    labels = sorted(by_label)
    brand_word = {n: "".join(core_tokens(n, rules)) for n in names}
    for i, x in enumerate(labels):
        if len(x) < 3:
            continue
        j = i + 1
        while j < len(labels) and labels[j].startswith(x):          # kfcbd extends kfc (sorted, so a contiguous run)
            y = labels[j]
            for a in by_label[x]:
                for b in by_label[y]:
                    if a != b and (brand_word[a] and y.startswith(brand_word[a]) or brand_word[b] and y.startswith(brand_word[b])):
                        emit("domain_family", [a, b], f"websites extend the same brand word ({x} / {y})")
            j += 1
    for x, grp in by_label.items():                                  # same label, different TLD (kfc.com / kfc.bz)
        if len(grp) > 1 and len({d for n in grp for d in stats[n]["domains"] if domain_label(d) == x}) > 1:
            ns = sorted(grp)
            if len(ns) <= 6:
                emit("domain_family", ns, f"websites share the brand word ({x}) on different domains")
    # 6 one name's words inside another's ('Credit Bank' in 'Credit Bank Baghdad Branch'), and 7 initialisms
    stop = {_ascii(x) for x in rules["stop_words"]}
    places = {t for p in rules.get("place_words", []) for t in tokens(p)} - generic    # runtime: cities/regions of the dataset
    cores = {n: core_tokens(n, rules) for n in names}
    first, last, initials = defaultdict(list), defaultdict(list), defaultdict(list)
    for n in names:
        c = cores[n]
        if c:
            first[c[0]].append(n)
            last[c[-1]].append(n)
        ft = [t for t in tokens(n) if t not in stop]
        if len(ft) >= 3:
            initials["".join(t[0] for t in ft)].append(n)
    for short in names:
        cs = cores[short]
        if not cs or set(cs) <= generic or (len(cs) == 1 and len(cs[0]) < 3):
            continue
        for long_ in set(first[cs[0]]) | set(last[cs[-1]]):
            cl = cores[long_]
            if long_ != short and len(cl) > len(cs) and (cl[:len(cs)] == cs or cl[-len(cs):] == cs):
                extra = set(cl) - set(cs)
                if extra and extra <= places:
                    emit("branch_suffix", [short, long_], f"{long_!r} is {short!r} plus a place name ({', '.join(sorted(extra))})")
                else:
                    emit("contained_name", [short, long_], f"{short!r} is the start or end of {long_!r}")
        letters = re.sub(r"[^A-Za-z]", "", short)
        if len(letters) >= 3 and short.upper() == short:
            for full in initials.get(letters.lower(), []):
                emit("abbreviation", [short, full], f"{short!r} is the initials of {full!r}")
    # 8 single-name casing defects: listed acronym written Title Case ('Kfc'), ALL CAPS / all lower, "Hardee'S"
    acr_map = {case_key(a): a for a in rules["acronyms"]}
    for n in names:
        listed = acr_map.get(case_key(n))
        if listed and n != listed:
            emit("name_format", [n], f"{n!r} is a listed acronym; write {listed!r}")
            findings[-1]["suggested"] = listed
            continue
        prob = format_problem(n, rules) or ("capital after apostrophe" if re.search(r"[a-z]'[A-Z]\b", n) else None)
        if prob:
            emit("name_format", [n], prob)
            if "apostrophe" in prob:
                findings[-1]["suggested"] = re.sub(r"(?<=[a-z]')[A-Z]\b", lambda m: m.group().lower(), n)
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    findings.sort(key=lambda f: (order[f["severity"]], not f["cross_source"], f["kind"], f["names"][0].casefold()))
    return findings


def apply_decisions(rows: list[dict], decisions: dict, name_fields=("business_name", "franchise_name")) -> tuple[list[dict], list[dict]]:
    """Rename reviewed variants. decisions = {"same": {"Kfc": "KFC", ...}}. Returns (new rows, change log); input untouched."""
    same = decisions.get("same", {})
    log: list[dict] = []
    out = []
    for i, row in enumerate(rows):
        new = dict(row)
        for f in name_fields:
            old = row.get(f)
            if old in same and same[old] != old:
                new[f] = same[old]
                log.append({"row_index": i, "field": f, "old": old, "new": same[old]})
        out.append(new)
    return out, log


def load_decisions(path: Path) -> dict:
    """{"same": {variant: canonical}, "distinct": [[a, b], ...]} - the human review of a findings sheet."""
    return json.loads(Path(path).read_text(encoding="utf-8")) if path and Path(path).exists() else {}


def rules_with_decisions(rules: dict, decisions: dict) -> dict:
    merged = dict(rules)
    merged["distinct_pairs"] = list(rules["distinct_pairs"]) + [list(p) for p in decisions.get("distinct", [])]
    return merged


def entries_from_rows(rows: list[dict], source: str, ref_key: str = "_row", sheet_key: str = "_sheet",
                      name_fields=("business_name", "franchise_name")) -> list[dict]:
    """Rows -> detector entries. Both name columns are fed: a mismatch between them is itself a family finding."""
    out = []
    for r in rows:
        for f in name_fields:
            if r.get(f):
                out.append({"name": str(r[f]), "website": r.get("website"), "source": source,
                            "ref": f"{r.get(sheet_key, '')}!{r.get(ref_key, '')}:{f}"})
    return out
