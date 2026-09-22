from conftest import load_tool

bc = load_tool("brand-existence-checker.py")
RULES = bc.load_rules()


def status(name, category="Shopping", cities=(), brands=()):
    return bc.screen_brand(name, category, list(cities), RULES, "SI", set(brands))[0]


def test_hotel_brand_must_start_the_name():
    assert status("Optika Ibis", "Health & Medical Opticians") == "No Flags"
    assert status("Ibis Styles", "Health") == "Manual Review"


def test_hotel_already_filed_as_accommodation_is_not_flagged():
    assert status("Hotel Kompas", "Travel & Vacation Hotels") == "No Flags"
    assert status("Hotel Planja", "Sports Gyms") == "Manual Review"


def test_city_suffix_only_when_it_splits_another_brand():
    assert status("Elektro Maribor", cities=["Maribor"], brands={"elektro maribor"}) == "No Flags"
    assert status("Hotel Kompas Bled", "Travel Hotels", cities=["Bled"],
                  brands={"hotel kompas", "hotel kompas bled"}) == "Manual Review"


def test_b2b_words_are_whole_words():
    assert status("Muster Bau AG") == "Misrepresentation"
    assert status("Bauhaus") == "No Flags"


def test_no_flags_does_not_claim_verification():
    _, reason, _ = bc.screen_brand("Zara", "Shopping", [], RULES, "SI")
    assert "not checked online" in reason
