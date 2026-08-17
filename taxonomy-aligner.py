import pandas as pd
import argparse
import sys
import os

def align_franchise_taxonomy(excel_path, franchise_col="franchise_name", subcat_col="subcategory", output_path=None):
    if not os.path.exists(excel_path):
        print(f"Error: File '{excel_path}' not found.")
        sys.exit(1)

    print(f"Loading dataset: {excel_path}")
    df = pd.read_excel(excel_path)

    if franchise_col not in df.columns or subcat_col not in df.columns:
        print(f"Error: Required columns '{franchise_col}' or '{subcat_col}' not in dataset.")
        print(f"Available columns: {list(df.columns)}")
        sys.exit(1)

    print(f"Analyzing intra-franchise subcategory consistency for {df[franchise_col].nunique():,} unique franchise brands...")

    misalignments = []
    corrections_made = 0

    for fname, group in df.groupby(franchise_col):
        subcats = group[subcat_col].dropna()
        if len(subcats) == 0:
            continue
        
        # Determine majority subcategory
        subcat_counts = subcats.value_counts()
        majority_subcat = subcat_counts.index[0]
        
        # Check for minority outliers
        outliers = group[group[subcat_col] != majority_subcat]
        if len(outliers) > 0 and len(subcat_counts) > 1:
            for idx, row in outliers.iterrows():
                misalignments.append({
                    "row_number": idx + 2, # Excel 1-based indexing
                    "franchise_name": fname,
                    "current_subcategory": row[subcat_col],
                    "expected_majority_subcategory": majority_subcat,
                    "majority_share": f"{subcat_counts.iloc[0]}/{len(group)} branches"
                })
                # Fix in dataframe
                df.at[idx, subcat_col] = majority_subcat
                corrections_made += 1

    print("\n" + "="*60)
    print("TAXONOMY ALIGNMENT AUDIT RESULTS")
    print("="*60)
    print(f"Franchise Brands Audited       : {df[franchise_col].nunique():,}")
    print(f"Subcategory Outlier Rows Found : {len(misalignments):,}")
    print("="*60)

    if misalignments:
        print("\nSample Taxonomy Outliers Standardized:")
        m_df = pd.DataFrame(misalignments)
        for r in m_df.head(15).itertuples():
            print(f"  Row {r.row_number} [{r.franchise_name}]: '{r.current_subcategory}' --> Realigned to '{r.expected_majority_subcategory}' ({r.majority_share})")

    if output_path:
        df.to_excel(output_path, index=False)
        print(f"\nSaved aligned clean dataset to: {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Intra-Franchise Subcategory Majority Taxonomy Aligner")
    parser.add_argument("excel_path", help="Path to input Excel dataset")
    parser.add_argument("--franchise-col", default="franchise_name", help="Franchise name column (default: franchise_name)")
    parser.add_argument("--subcat-col", default="subcategory", help="Subcategory column (default: subcategory)")
    parser.add_argument("--output", help="Optional output Excel file path to save cleaned dataset")
    args = parser.parse_args()

    align_franchise_taxonomy(args.excel_path, args.franchise_col, args.subcat_col, args.output)

if __name__ == "__main__":
    main()
