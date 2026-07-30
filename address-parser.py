"""
Universal QA Toolkit — Address Normalization & Postal Mapping Engine (address-parser.py)
Provides country-specific postal code validation, province mapping, and address formatting.
Author: Azeez
"""

import re
import sys
import json
import argparse

# Belgian Postal Code Ranges -> Official Provinces
BELGIUM_PROVINCES = [
    (1000, 1299, "Brussels-Capital Region"),
    (1300, 1499, "Walloon Brabant"),
    (1500, 1999, "Flemish Brabant"),
    (2000, 2999, "Antwerp"),
    (3000, 3499, "Flemish Brabant"),
    (3500, 3999, "Limburg"),
    (4000, 4999, "Liège"),
    (5000, 5999, "Namur"),
    (6000, 6599, "Hainaut"),
    (6600, 6999, "Luxembourg (BE)"),
    (7000, 7999, "Hainaut"),
    (8000, 8999, "West Flanders"),
    (9000, 9999, "East Flanders")
]

# Country-specific Postal Code Regex Patterns
POSTAL_REGEX = {
    "BE": r"^\d{4}$",
    "LU": r"^\d{4}$",
    "US": r"^\d{5}(-\d{4})?$",
    "DE": r"^\d{5}$",
    "FR": r"^\d{5}$",
    "NL": r"^\d{4}\s?[A-Z]{2}$",
    "GB": r"^[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}$"
}

def get_province_be(postal_code):
    """Return Belgian province for a 4-digit postal code."""
    pc_clean = re.sub(r"\D", "", str(postal_code or ""))
    if not pc_clean or len(pc_clean) != 4:
        return ""
    code = int(pc_clean)
    for start, end, province in BELGIUM_PROVINCES:
        if start <= code <= end:
            return province
    return ""

def validate_postal_code(postal_code, country_code="BE"):
    """Check if postal code matches country regex."""
    pattern = POSTAL_REGEX.get(country_code.upper())
    if not pattern:
        return True
    return bool(re.match(pattern, str(postal_code).strip(), re.IGNORECASE))

def format_address(street, postal_code, city, province=None, country="Belgium"):
    """Assemble a standard formatted_address string."""
    parts = []
    if street:
        parts.append(str(street).strip(", "))
    
    city_line = ""
    if postal_code and city:
        city_line = f"{postal_code} {city}"
    elif city:
        city_line = str(city)
    elif postal_code:
        city_line = str(postal_code)
    
    if city_line:
        parts.append(city_line)
    if province:
        parts.append(str(province))
    if country:
        parts.append(str(country))

    return ", ".join(parts)

def main():
    parser = argparse.ArgumentParser(description="Address Normalization Engine (address-parser.py)")
    parser.add_argument("--country", default="BE", help="Country ISO code (default: BE)")
    parser.add_argument("--postal", help="Postal code to map or validate")
    parser.add_argument("--address", help="Street address")
    parser.add_argument("--city", help="City name")
    parser.add_argument("--format", action="store_true", help="Assemble full formatted address")

    args = parser.parse_args()

    result = {}
    if args.postal:
        valid = validate_postal_code(args.postal, args.country)
        province = get_province_be(args.postal) if args.country.upper() == "BE" else ""
        result = {
            "postal_code": args.postal,
            "country": args.country,
            "is_valid": valid,
            "province": province
        }

    if args.format or (args.address and args.city):
        prov = result.get("province") or ""
        formatted = format_address(args.address, args.postal, args.city, prov, "Belgium" if args.country=="BE" else args.country)
        result["formatted_address"] = formatted

    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
