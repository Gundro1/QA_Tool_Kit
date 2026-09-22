import json

import openpyxl
import pandas as pd

from conftest import HEADER, load_tool, row, write_workbook

ta = load_tool("taxonomy-aligner.py")


def brand_rows(name, subcats, business_names=None):
    business_names = business_names or [name] * len(subcats)
    return [row(franchise_name=name, business_name=b, category="Cat", subcategory=s, franchise_flag="Y")
            for s, b in zip(subcats, business_names)]


def classes(results):
    return {(r["franchise_name"], r["classification"]) for r in results}


def test_classification(tmp_path, capsys):
    rows = (brand_rows("Clear", ["A"] * 9 + ["B"])
            + brand_rows("Petrol", ["Fuel"] * 9 + ["Car Wash"], ["Petrol"] * 9 + ["Petrol Car Wash"])
            + brand_rows("Bauhaus", ["Garden"] * 4 + ["DIY"] * 3)
            + brand_rows("Tie", ["A", "A", "B", "B"])
            + brand_rows("Mixed", ["A"] * 9 + ["B"]))
    allow = tmp_path / "allow.txt"
    allow.write_text("# intentionally mixed\nmixed\n", encoding="utf-8")
    path = write_workbook(tmp_path / "d.xlsx", {"Franchise": [HEADER, *rows]})
    results, _ = ta.align_franchise_taxonomy(path, allowlist=ta.qc.load_list_file(str(allow)))
    assert classes(results) == {
        ("Clear", "realign"), ("Petrol", "format_variant"), ("Bauhaus", "mixed_review"),
        ("Tie", "mixed_review"), ("Mixed", "allowlisted"),
    }


def test_output_changes_only_realigned_cells_and_keeps_sheets(tmp_path, capsys):
    path = write_workbook(tmp_path / "d.xlsx", {
        "Franchise": [HEADER, *brand_rows("Clear", ["A"] * 4 + ["B"]), *brand_rows("Bauhaus", ["G"] * 4 + ["D"] * 3)],
        "Change log": [["source_row", "note"], [2, "kept"]],
    })
    out = tmp_path / "out.xlsx"
    ta.align_franchise_taxonomy(path, output_path=str(out))
    wb = openpyxl.load_workbook(out)
    assert wb.sheetnames == ["Franchise", "Change log"]
    subcats = [c.value for c in wb["Franchise"]["J"][1:]]
    assert subcats == ["A"] * 5 + ["G"] * 4 + ["D"] * 3  # Clear realigned, Bauhaus untouched


def test_taxonomy_loader_handles_title_rows_and_merged_categories(tmp_path):
    grid = tmp_path / "tax.xlsx"
    write_workbook(grid, {"Regular": [
        ["Bisviews — Categories", None, None],
        ["Category", "Subcategory", "Type"],
        ["▼  REGULAR", None, None],
        ["Shopping & Fashion", "Clothing", "Regular"],
        [None, "Footwear", None],
        ["Travel & Vacation", "Hotels", "Regular"],
    ]})
    tax = ta.load_taxonomy(str(grid))
    assert tax == {"Clothing": {"Shopping & Fashion"}, "Footwear": {"Shopping & Fashion"},
                   "Hotels": {"Travel & Vacation"}}
    seeds = tmp_path / "subcategories.json"
    seeds.write_text(json.dumps([{"name": "Clothing", "category": "Shopping & Fashion"}]), encoding="utf-8")
    assert ta.load_taxonomy(str(seeds)) == {"Clothing": {"Shopping & Fashion"}}


def test_check_against_taxonomy():
    df = pd.DataFrame({
        "category": ["Shop", "Shop", "Travel", "Shop"],
        "subcategory": ["Clothing", "clothing ", "Clothing", "Home & Furniture"],
        "_sheet": "S", "_row": [2, 3, 4, 5],
    })
    found = {f["row"]: f["issue"] for f in ta.check_against_taxonomy(df, {"Clothing": {"Shop"}}, "category", "subcategory")}
    assert found == {3: "subcategory_spelling_differs", 4: "subcategory_under_wrong_category",
                     5: "subcategory_not_in_taxonomy"}
