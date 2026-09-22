"""
Universal QA Toolkit — Brand Existence & Misrepresentation Screener (brand-existence-checker.py)

Keyword screening that decides which brands need a manual (web) check. It does NOT
verify presence online: a brand with no flags is reported as "No Flags", not as
verified. Rules are configurable per country with --rules (JSON), because the
defaults were tuned on Swiss data (German B2B words).

Rules (defaults in DEFAULT_RULES):
  edit_instructions   supervisor notes left in the brand text
  b2b_keywords        construction / engineering / consulting firms (whole words)
  hotel_brands        hotel brands that must START the name ('ibis ...', not 'Optika Ibis')
  hotel_words         generic accommodation words anywhere in the name
  accommodation_words a category/subcategory containing one of these is already
                      filed as accommodation -> no hotel flag
  location suffix     franchise name = another brand in the file + one of its cities
                      ('Hotel Kompas Bled' next to 'Hotel Kompas')
"""
import re

import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import os
import sys
import argparse
from datetime import datetime

import qa_common as qc

DEFAULT_RULES = {
    "edit_instructions": ["update the postal code", "add street number", "corrupted"],
    "b2b_keywords": ["ingenieure", "architektur", "consulting", "holding", "bau", "berater",
                     "contractor", "construction"],
    "hotel_brands": ["ibis", "radisson"],
    "hotel_words": ["hotel", "hotels"],
    "accommodation_words": ["hotel", "accommodation", "hostel", "resort", "lodging", "travel"],
}


def load_rules(path=None):
    rules = {k: list(v) for k, v in DEFAULT_RULES.items()}
    if path:
        custom = qc.load_json(path)
        unknown = set(custom) - set(rules)
        if unknown:
            print(f"Error: Unknown rule keys in {path}: {sorted(unknown)}", file=sys.stderr)
            sys.exit(1)
        rules.update(custom)
    return rules


def _words_pattern(words):
    return re.compile(r"\b(?:" + "|".join(re.escape(w) for w in words) + r")\b", re.IGNORECASE) if words else None


def screen_brand(name, category_text, cities, rules, country_code, all_brands=None):
    """Return (status, reason, action) for one brand."""
    lower = name.lower()
    if any(w in lower for w in rules["edit_instructions"]):
        return ("Misrepresentation", "Corrupted brand string containing supervisor edit instruction.",
                "REMOVE / MERGE — Clean and merge under canonical brand name.")
    b2b = _words_pattern(rules["b2b_keywords"])
    if b2b and b2b.search(name):
        return ("Misrepresentation", "Industrial construction, B2B engineering, or architectural firm with no retail store chain.",
                "REMOVE / RECLASSIFY — B2B entity, not a consumer retail franchise.")
    hotel_brand = re.match(r"(?:" + "|".join(re.escape(b) for b in rules["hotel_brands"]) + r")\b", lower) \
        if rules["hotel_brands"] else None
    hotel_word = _words_pattern(rules["hotel_words"])
    is_hotel = bool(hotel_brand) or bool(hotel_word and hotel_word.search(name))
    filed_as_stay = any(w in category_text.lower() for w in rules["accommodation_words"])
    if is_hotel and not filed_as_stay:
        return ("Manual Review", "Hotel name filed outside an accommodation category.",
                "ALIGN TAXONOMY — Confirm subcategory matches 'Hotels & Accommodations'.")
    tokens = qc.norm_text(name)
    for city in sorted({qc.norm_text(c) for c in cities if str(c).strip()}, key=len, reverse=True):
        base = tokens[: -len(city)].strip()
        # Only when the name without the city is ANOTHER brand in the file: many real
        # companies carry a city in their name (Elektro Maribor, Lekarna Ljubljana).
        if len(city) > 2 and tokens.endswith(" " + city) and base in (all_brands or ()):
            return ("Manual Review", f"Brand name is '{base.title()}' plus its city ('{city.title()}'); "
                    "the rows are split from that brand.",
                    "STRIP LOCATION SUFFIX — Clean franchise_name to pure brand name.")
    return ("No Flags", f"No screening rule matched. Presence in {country_code} was not checked online.",
            "NONE — verify on the brand's official store locator if in doubt.")


def run_brand_existence_audit(excel_path, country_code="CH", auditor=None, output_dir=None, rules=None,
                              sheet=None, engine=None):
    auditor = auditor or os.environ.get("QA_AUDITOR", "QA")
    rules = rules or load_rules()
    out_dir = os.path.abspath(output_dir or os.path.join(os.path.dirname(excel_path), "QA_Verification_Output"))
    os.makedirs(out_dir, exist_ok=True)

    country_code = country_code.upper()
    base_name = os.path.splitext(os.path.basename(excel_path))[0]
    out_excel = os.path.join(out_dir, f"{country_code}_Brand_Existence_Verification_{auditor}.xlsx")

    with qc.timed("Load"):
        df = qc.load_dataset(excel_path, sheet=sheet, engine=engine)
    if "franchise_flag" in df.columns:
        df = df[df["franchise_flag"].str.strip().str.lower().isin(qc.TRUE_TOKENS)]
    total_rows = len(df)

    fname_col = "franchise_name" if "franchise_name" in df.columns else ("business_name" if "business_name" in df.columns else df.columns[0])
    web_col = "website" if "website" in df.columns else "url"
    city_col = "city" if "city" in df.columns else "admin_level_1"
    cat_col = "category" if "category" in df.columns else df.columns[1]
    sub_col = "subcategory" if "subcategory" in df.columns else None

    df = df[df[fname_col].str.strip() != ""]
    brand_groups = df.groupby(df[fname_col].str.strip())
    all_brands = {qc.norm_text(b) for b in brand_groups.groups}
    verification_data = []

    for bname, group in brand_groups:
        count = len(group)
        urls = [str(u) for u in group[web_col].unique() if str(u).strip() != ''] if web_col in group.columns else []
        main_url = urls[0] if urls else "N/A"
        cities = [c for c in group[city_col].unique() if str(c).strip()] if city_col in group.columns else []
        city_sample = ", ".join(str(c) for c in cities[:3])
        if len(cities) > 3:
            city_sample += f" (+{len(cities)-3} more)"

        b_clean = str(bname).strip()
        cats = [c for c in group[cat_col].unique() if str(c).strip()] if cat_col in group.columns else []
        cat_val = str(cats[0]) if cats else "General"
        category_text = " ".join(cats + ([str(v) for v in group[sub_col].unique()] if sub_col else []))

        tld_hint = f".{country_code.lower()}"
        has_local_domain = "Yes" if any(tld_hint in u.lower() for u in urls) else "No"

        status, reason, action = screen_brand(b_clean, category_text, cities, rules, country_code, all_brands)

        verification_data.append({
            "brand_name": b_clean,
            "category": cat_val,
            "branch_count": count,
            "status": status,
            "sample_website": main_url,
            "sample_cities": city_sample,
            "domain_hint": has_local_domain,
            "reason": reason,
            "action_required": action
        })

    vdf = pd.DataFrame(verification_data)
    vdf.sort_values(by=["status", "branch_count"], ascending=[True, False], inplace=True)

    print(f"Generating Excel report: {out_excel}")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Brand Presence Audit"
    ws.views.sheetView[0].showGridLines = True

    font_title = Font(name="Calibri", size=16, bold=True, color="1F4E78")
    font_sub = Font(name="Calibri", size=11, italic=True, color="595959")
    font_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    font_body = Font(name="Calibri", size=11, color="000000")
    
    fill_header = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    fill_verified = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
    fill_review = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
    fill_misrep = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")

    ws.cell(row=1, column=1, value=f"{country_code} Franchise Brand Existence & Misrepresentation Audit").font = font_title
    ws.cell(row=2, column=1, value=f"Dataset: {base_name} | Auditor: {auditor} | Total Brands: {len(vdf)} | Total Rows: {total_rows:,}").font = font_sub

    headers = ["Brand Name", "Category", "Branch Count", f"Domain Hint (.{country_code.lower()})", "Status", "Sample Website", "Evidence / Issue Reason", "Action Required"]
    for col_num, h in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col_num, value=h)
        cell.font = font_header
        cell.fill = fill_header

    for r_idx, row in enumerate(vdf.itertuples(index=False), 5):
        ws.cell(row=r_idx, column=1, value=row.brand_name).font = font_body
        ws.cell(row=r_idx, column=2, value=row.category).font = font_body
        ws.cell(row=r_idx, column=3, value=row.branch_count).font = font_body
        ws.cell(row=r_idx, column=4, value=row.domain_hint).font = font_body
        ws.cell(row=r_idx, column=5, value=row.status).font = font_body
        ws.cell(row=r_idx, column=6, value=row.sample_website).font = font_body
        ws.cell(row=r_idx, column=7, value=row.reason).font = font_body
        ws.cell(row=r_idx, column=8, value=row.action_required).font = font_body

        st_cell = ws.cell(row=r_idx, column=5)
        if row.status == "No Flags":
            st_cell.fill = fill_verified
        elif row.status == "Manual Review":
            st_cell.fill = fill_review
        else:
            st_cell.fill = fill_misrep

    wb.save(out_excel)
    counts = vdf["status"].value_counts().to_dict()
    print(f"Screened {len(vdf):,} brands: {counts}")
    print("Note: 'No Flags' means no screening rule matched; brand presence was not verified online.")
    print(f"Audit completed! Report saved to: {out_excel}")
    return vdf

def main():
    parser = argparse.ArgumentParser(description="Brand Existence & Misrepresentation Screening (keyword rules)")
    parser.add_argument("excel_path", help="Path to target Excel dataset")
    parser.add_argument("--country", default="CH", help="Country ISO code (default: CH)")
    parser.add_argument("--auditor", default=None,
                        help="Name used in the report file name (default: $QA_AUDITOR, else 'QA')")
    parser.add_argument("--output-dir", default=None,
                        help="Report folder (default: QA_Verification_Output next to the input file)")
    parser.add_argument("--rules", default=None, help="JSON file overriding the screening keyword lists")
    parser.add_argument("--sheet", default=None, help="Only this sheet (default: every data sheet)")
    parser.add_argument("--engine", default=None, help="Excel reader engine (default: calamine if installed)")
    qc.add_logging_args(parser)
    args = parser.parse_args()
    qc.setup_logging(args)

    run_brand_existence_audit(args.excel_path, args.country, args.auditor, output_dir=args.output_dir,
                              rules=load_rules(args.rules), sheet=args.sheet, engine=args.engine)


if __name__ == "__main__":
    main()
