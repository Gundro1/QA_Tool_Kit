import pytest

import qa_common as qc
from conftest import HEADER, row, write_workbook


@pytest.mark.parametrize("a,b", [("Konzum 38B", "konzum  38b"), (" Nike Mall", "NIKE MALL ")])
def test_norm_text_ignores_case_and_spacing(a, b):
    assert qc.norm_text(a) == qc.norm_text(b)


@pytest.mark.parametrize("a,b", [("Bags & More", "Bags&More"), ("Müller", "MULLER"), ("Dr. Max", "Dr.Max")])
def test_fold_ignores_punctuation_and_accents(a, b):
    assert qc.fold(a) == qc.fold(b)


def test_brand_key_drops_trailing_legal_suffix_only():
    assert qc.brand_key("Popular Diagnostic Centre Ltd.") == qc.brand_key("Popular Diagnostic Centre")
    assert qc.brand_key("Fielmann AG") == qc.brand_key("Fielmann")
    assert qc.brand_key("AB") == "ab"  # never strip the whole name


@pytest.mark.parametrize("url,host", [
    ("HTTPS://www.Shop.Mango.com:443/x?y", "shop.mango.com"),
    ("konzum.hr", "konzum.hr"),
    ("not publicly disclosed", ""),
    ("", ""),
])
def test_host_from_url(url, host):
    assert qc.host_from_url(url) == host


def test_host_keeps_www_for_dns():
    assert qc.host_from_url("https://www.tlscontact.com", keep_www=True) == "www.tlscontact.com"


@pytest.mark.parametrize("host,domain", [
    ("shop.mango.com", "mango.com"), ("www.avis.com.hr", "avis.com.hr"), ("ae.hm.com", "hm.com"),
])
def test_registrable_domain(host, domain):
    assert qc.registrable_domain(host) == domain


def test_social_or_listing():
    assert qc.social_or_listing("https://www.facebook.com/brand") == "facebook.com"
    assert qc.social_or_listing("https://m.facebook.com/brand") == "facebook.com"
    assert qc.social_or_listing("https://brand.com") == ""


def test_placeholder_names():
    assert qc.looks_like_placeholder_name("Brand-Operated / Independent")
    assert qc.looks_like_placeholder_name("Not Publicly Disclosed")
    assert not qc.looks_like_placeholder_name("Independence Bank")  # whole word only
    assert not qc.looks_like_placeholder_name("Zara")


def test_load_dataset_reads_all_data_sheets_and_skips_logs(tmp_path):
    path = write_workbook(tmp_path / "d.xlsx", {
        "Franchise": [HEADER, row(business_name="A"), row(business_name="B")],
        "Solo": [HEADER, row(business_name="C")],
        "Change log": [["source_row", "column", "old_value"], [2, "city", "x"]],
    })
    df = qc.load_dataset(path)
    assert list(df["business_name"]) == ["A", "B", "C"]
    assert list(df[qc.SHEET_COL]) == ["Franchise", "Franchise", "Solo"]
    assert list(df[qc.ROW_COL]) == [2, 3, 2]
    assert (df == "").sum().sum() > 0 and not df.isna().any().any()


def test_load_dataset_required_columns(tmp_path):
    path = write_workbook(tmp_path / "d.xlsx", {"Issues log": [["category", "detail"], ["x", "y"]],
                                                "Data": [HEADER, row(website="a.com")]})
    df = qc.load_dataset(path, required_columns=["website"])
    assert list(df[qc.SHEET_COL]) == ["Data"]


def test_load_dataset_missing_column_exits(tmp_path):
    path = write_workbook(tmp_path / "d.xlsx", {"Data": [HEADER, row()]})
    with pytest.raises(SystemExit):
        qc.load_dataset(path, required_columns=["nope"])


def test_generic_mode_uses_widest_sheet_even_when_a_log_comes_first(tmp_path):
    path = write_workbook(tmp_path / "d.xlsx", {
        "Change log": [["source_row", "note"], [2, "x"]],
        "Franchise": [HEADER, row(business_name="A")],
    })
    df = qc.load_dataset(path)
    assert list(df[qc.SHEET_COL]) == ["Franchise"]
