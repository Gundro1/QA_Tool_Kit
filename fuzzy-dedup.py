import pandas as pd
import argparse
import sys
import os
from difflib import SequenceMatcher

def string_similarity(a, b):
    if not isinstance(a, str) or not isinstance(b, str):
        return 0.0
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()

def find_fuzzy_duplicates(excel_path, name_column="business_name", city_column="city", threshold=0.85):
    if not os.path.exists(excel_path):
        print(f"Error: File '{excel_path}' not found.")
        sys.exit(1)

    print(f"Loading dataset: {excel_path}")
    df = pd.read_excel(excel_path)

    if name_column not in df.columns:
        print(f"Error: Column '{name_column}' not found. Available columns: {list(df.columns)}")
        sys.exit(1)

    print(f"Scanning {len(df):,} rows for fuzzy duplicate business listings (threshold: {threshold*100:.0f}% similarity)...")

    duplicates = []
    
    # Group by city first if city column exists to speed up comparison
    if city_column in df.columns:
        groups = df.groupby(city_column)
    else:
        groups = [("All", df)]

    for city_val, group in groups:
        names = group[name_column].dropna().tolist()
        indices = group.index.tolist()
        
        n_len = len(names)
        for i in range(n_len):
            for j in range(i + 1, n_len):
                n1, n2 = names[i], names[j]
                # Skip exact matches (handled by DUP-01)
                if n1.lower().strip() == n2.lower().strip():
                    continue
                score = string_similarity(n1, n2)
                if score >= threshold:
                    duplicates.append({
                        "row_1": indices[i] + 2,  # 1-based Excel row indexing
                        "business_name_1": n1,
                        "row_2": indices[j] + 2,
                        "business_name_2": n2,
                        "city": city_val,
                        "similarity_score": f"{score*100:.1f}%"
                    })

    print("\n" + "="*60)
    print("FUZZY DUPLICATE DETECTION RESULTS")
    print("="*60)
    print(f"Total Fuzzy Duplicate Pairs Found: {len(duplicates):,}")
    print("="*60)

    if duplicates:
        print("\nTop 15 Fuzzy Duplicate Pairs:")
        dup_df = pd.DataFrame(duplicates)
        for row in dup_df.head(15).itertuples():
            print(f"  Row {row.row_1} vs Row {row.row_2} ({row.similarity_score}): '{row.business_name_1}' <--> '{row.business_name_2}' [{row.city}]")

def main():
    parser = argparse.ArgumentParser(description="High-Speed Fuzzy Duplicate Store Listing Detector")
    parser.add_argument("excel_path", help="Path to target Excel dataset")
    parser.add_argument("--name-col", default="business_name", help="Business name column (default: business_name)")
    parser.add_argument("--city-col", default="city", help="City column (default: city)")
    parser.add_argument("--threshold", type=float, default=0.85, help="Similarity ratio threshold (0.5 to 1.0, default: 0.85)")
    args = parser.parse_args()

    find_fuzzy_duplicates(args.excel_path, args.name_col, args.city_col, args.threshold)

if __name__ == "__main__":
    main()
