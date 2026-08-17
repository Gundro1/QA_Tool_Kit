import socket
import pandas as pd
import argparse
import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

def clean_url(url_str):
    if not isinstance(url_str, str) or not url_str.strip():
        return None
    url = url_str.strip()
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url
    try:
        parsed = urlparse(url)
        return parsed.netloc or parsed.path.split('/')[0]
    except Exception:
        return None

def verify_domain_dns(domain):
    if not domain:
        return domain, False, "Empty domain"
    # Strip port if present
    domain_clean = domain.split(':')[0]
    try:
        # Fast DNS socket resolution (10ms)
        socket.getaddrinfo(domain_clean, 80)
        return domain, True, "Resolved"
    except socket.gaierror as e:
        return domain, False, f"DNS Error: {e}"
    except Exception as e:
        return domain, False, f"Error: {e}"

def verify_dataset_domains(excel_path, url_column="website", max_workers=50):
    if not os.path.exists(excel_path):
        print(f"Error: File '{excel_path}' not found.")
        sys.exit(1)

    print(f"Loading dataset: {excel_path}")
    df = pd.read_excel(excel_path)
    
    if url_column not in df.columns:
        print(f"Error: Column '{url_column}' not found in dataset. Available columns: {list(df.columns)}")
        sys.exit(1)

    raw_urls = df[url_column].dropna().unique()
    domains = set(clean_url(u) for u in raw_urls if clean_url(u))
    print(f"Extracted {len(domains):,} unique domain names to verify using DNS sockets...")

    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(verify_domain_dns, dom): dom for dom in domains}
        for future in as_completed(futures):
            dom, is_valid, msg = future.result()
            results[dom] = (is_valid, msg)

    valid_count = sum(1 for v, m in results.values() if v)
    invalid_count = len(results) - valid_count
    
    print("\n" + "="*50)
    print("DNS SOCKET VERIFICATION RESULTS")
    print("="*50)
    print(f"Total Unique Domains Tested: {len(domains):,}")
    print(f"Valid / Resolving Domains : {valid_count:,} ({valid_count/len(domains)*100:.1f}%)" if domains else "0")
    print(f"Failed / Unreachable Domains: {invalid_count:,}")
    print("="*50)

    if invalid_count > 0:
        print("\nSample Failed Domains:")
        failed_sample = [d for d, (v, m) in results.items() if not v][:10]
        for d in failed_sample:
            print(f"  - {d}: {results[d][1]}")

def main():
    parser = argparse.ArgumentParser(description="Fast Zero-Cost DNS Socket Domain Verifier")
    parser.add_argument("excel_path", help="Path to input Excel dataset")
    parser.add_argument("--column", default="website", help="Column name containing URLs/domains (default: website)")
    parser.add_argument("--workers", type=int, default=50, help="Parallel worker threads (default: 50)")
    args = parser.parse_args()

    verify_dataset_domains(args.excel_path, args.column, args.workers)

if __name__ == "__main__":
    main()
