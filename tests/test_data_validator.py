import pytest

from conftest import HEADER, load_tool, row, write_workbook

dv = load_tool("data-validator.py")


def types(findings):
    out = {}
    for f in findings:
        out[f["type"]] = out.get(f["type"], 0) + 1
    return out


@pytest.mark.parametrize("text,expected", [
    ("SÃO PAULO", False),        # legitimate Portuguese capitals
    ("CÂMARA MUNICIPAL", False),
    ("Zürich", False),
    ("SÃ£o Paulo", True),         # 'ã' shown as UTF-8 bytes in Windows-1252
    ("ZÃ¼rich", True),
    ("Cafâ€™s", True),
])
def test_mojibake_detection(text, expected):
    assert dv.is_mojibake(text) is expected


def run(tmp_path, sheets, **kw):
    path = write_workbook(tmp_path / "d.xlsx", sheets)
    _, findings = dv.audit_dataset(path, **kw)
    return findings


def test_postal_codes_are_country_aware(tmp_path, capsys):
    findings = run(tmp_path, {"Franchise": [
        HEADER,
        row(country_code="FI", postal_code="100"),      # zeros lost
        row(country_code="FI", postal_code="00100"),    # ok
        row(country_code="BE", postal_code="L-1234"),   # Luxembourg code in Belgium
        row(country_code="AE", postal_code="12345"),    # UAE has no postal codes
        row(country_code="ZZ", postal_code="whatever"),  # unknown country: skipped
    ]})
    t = types(findings)
    assert t["postal_code_leading_zero_lost"] == 1
    assert t["invalid_postal_code"] == 1
    assert t["postal_code_where_none_exist"] == 1


def test_franchise_rules(tmp_path, capsys):
    findings = run(tmp_path, {
        "Franchise": [
            HEADER,
            row(country_code="LU", franchise_flag="Y", franchise_name="Acme", branch_count="2", business_name="Acme"),
            row(country_code="LU", franchise_flag="Yes", franchise_name="Acme", branch_count="2", business_name="Acme"),
            row(country_code="BE", franchise_flag="Y", franchise_name="Acme", branch_count="1", business_name="Acme"),
            row(country_code="LU", franchise_flag="Y", franchise_name="", business_name="Nameless"),
            row(country_code="LU", franchise_flag="Y", franchise_name="Brand-Operated / Independent", branch_count="1"),
            row(country_code="LU", franchise_flag="N", business_name="Solo in franchise sheet"),
        ],
        "Solo": [HEADER, row(country_code="LU", franchise_flag="N", franchise_name="Leftover", branch_count="1")],
    })
    t = types(findings)
    assert t["franchise_flag_value"] == 1           # 'Yes' spelling reported once...
    assert "branch_count_mismatch" not in t         # ...but still counted: LU Acme = 2, BE Acme = 1
    assert t["franchise_name_missing"] == 1
    assert t["franchise_name_placeholder"] == 1
    assert t["solo_row_has_franchise_fields"] == 1
    assert t["row_on_wrong_sheet"] == 1


def test_duplicates_normalised_and_blank_keys(tmp_path, capsys):
    path = write_workbook(tmp_path / "d.xlsx", {"Franchise": [
        HEADER,
        row(business_name="Konzum", address="Ilica 38B", city="Zagreb"),
        row(business_name="Konzum", address="Ilica 38b", city="Zagreb"),
        row(business_name="Nike", address="", city="Dubai"),
        row(business_name="Nike", address="", city="Dubai"),
    ]})
    results, _ = dv.audit_dataset(path, dedup_key="business_name,address,city")
    d = results["duplicates"]
    assert d["duplicate_rows"] == 2                 # exact, original behaviour (blank addresses match)
    assert d["duplicate_rows_normalized"] == 2      # 38B/38b caught, blank-address rows not called duplicates
    assert d["rows_with_blank_key_part"] == 2


def test_website_and_plus_code_checks(tmp_path, capsys):
    findings = run(tmp_path, {"Franchise": [
        HEADER,
        row(website="https://www.facebook.com/brand"),
        row(website="not publicly disclosed"),
        row(website="https://brand.com"),
        row(address="69FQ+GFM, Baghdad"),
    ]})
    t = types(findings)
    assert t["website_is_social_or_listing"] == 1
    assert t["website_placeholder"] == 1
    assert t["plus_code_in_address"] == 1


def test_change_log_sheet_is_not_checked(tmp_path, capsys):
    path = write_workbook(tmp_path / "d.xlsx", {
        "Franchise": [HEADER, row(franchise_flag="Y", franchise_name="A", branch_count="1")],
        "Change log": [["source_row", "column", "old_value", "new_value"], [2, "x", "a", "b"], [2, "x", "a", "b"]],
    })
    results, findings = dv.audit_dataset(path)
    assert results["sheets"] == {"Franchise": 1}
    assert results["exact_duplicate_rows_all_columns"] == 0
