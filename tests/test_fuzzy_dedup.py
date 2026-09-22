from conftest import HEADER, load_tool, row, write_workbook

fd = load_tool("fuzzy-dedup.py")


def run(tmp_path, rows, **kw):
    path = write_workbook(tmp_path / "d.xlsx", {"Franchise": [HEADER, *rows]})
    ranked, suppressed = fd.find_fuzzy_duplicates(path, threshold=0.85, **kw)
    return ranked, suppressed


def test_spelling_variants_found_across_cities(tmp_path, capsys):
    ranked, _ = run(tmp_path, [
        row(business_name="Bags & More", city="Ljubljana"),
        row(business_name="Bags&More", city="Maribor"),
        row(business_name="Fielmann AG", city="Bern"),
        row(business_name="Fielmann", city="Basel"),
    ])
    variants = [f for f in ranked if f["tier"] == "spelling_variant"]
    assert len(variants) == 2


def test_different_websites_are_suppressed_even_at_same_address(tmp_path, capsys):
    ranked, suppressed = run(tmp_path, [
        row(business_name="NRB Bank", city="Dhaka", address="Nawab Yusuf Road", website="https://nrbbankbd.com"),
        row(business_name="NRBC Bank", city="Dhaka", address="Nawab Yusuf Road", website="https://nrbcommercialbank.com"),
        row(business_name="Pull & Bear", city="Dubai", website="https://pullandbear.com"),
        row(business_name="Bull & Bear", city="Dubai", website="https://bullandbeardifc.com"),
    ])
    assert ranked == []
    assert suppressed == {"suppressed_different_websites": 2}


def test_same_address_similar_names_is_a_duplicate(tmp_path, capsys):
    ranked, _ = run(tmp_path, [
        row(business_name="Dosenbach Sport", city="Zurich", address="Bahnhofstrasse 1", website="https://dosenbach.ch"),
        row(business_name="Dosenbach Sports", city="Zurich", address="Bahnhofstrasse 1", website="https://dosenbach.ch"),
    ])
    assert [f["tier"] for f in ranked] == ["same_address_duplicate"]


def test_same_website_different_address_is_another_branch(tmp_path, capsys):
    ranked, suppressed = run(tmp_path, [
        row(business_name="Ibis Styles Dubai Jumeira", city="Dubai", address="Jumeira Rd", website="https://all.accor.com"),
        row(business_name="Ibis Styles Dubai Deira", city="Dubai", address="Deira St", website="https://all.accor.com"),
    ])
    assert ranked == []
    assert suppressed == {"suppressed_same_brand_other_branch": 1}


def test_difflib_fallback_matches_rapidfuzz(monkeypatch):
    names = ["dosenbach sport", "dosenbach sports", "zara", "kfc"]
    fast = {(i, j) for i, j, _ in fd._similar_pairs(names, 0.85)}
    monkeypatch.setattr(fd, "process", None)
    slow = {(i, j) for i, j, _ in fd._similar_pairs(names, 0.85)}
    assert fast == slow == {(0, 1)}
