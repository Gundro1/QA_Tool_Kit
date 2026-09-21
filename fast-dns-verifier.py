"""
Universal QA Toolkit — Fast DNS Domain Verifier (fast-dns-verifier.py)

Resolves every website domain in a dataset with the OS resolver (fast, parallel),
then separates "dead" from "could not check":

  resolves        the OS resolver returned an address
  nxdomain        the domain does not exist, confirmed over DNS-over-HTTPS
                  (dns.google, then Cloudflare) -> genuinely dead
  no_address      the domain exists but has no A/AAAA record
  unknown         timeouts or resolver failures on every path -> NOT evidence
                  that the site is down (sandboxes, VPNs and flaky networks do this)
  social_listing  a Facebook/Instagram/Maps/... page in the website column

A local resolver failure is never reported as dead on its own: sandbox DNS once
flagged even mercator.si as unreachable. Every lookup has a timeout and retries.

--http adds an HTTP probe per live domain (HEAD, then GET). 401/403/429/503 count
as reachable-but-blocking-bots, not dead; a redirect to another registrable
domain is reported (moved, parked or acquired sites).
"""

import argparse
import socket
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

import qa_common as qc

DOH_PROVIDERS = (
    ("https://dns.google/resolve", {}),
    ("https://cloudflare-dns.com/dns-query", {"accept": "application/dns-json"}),
)
_DOH_LIMIT = threading.Semaphore(8)  # be polite to public resolvers
_BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def clean_url(url_str):
    """Kept for callers of the old API: the host of a URL, or None."""
    host = qc.host_from_url(url_str)
    return host or None


def _getaddrinfo(host, timeout):
    """socket.getaddrinfo has no timeout; run it in a daemon thread and give up
    after `timeout` seconds so one hanging lookup cannot stall the whole run."""
    box = {}

    def target():
        try:
            box["result"] = socket.getaddrinfo(host, 80)
        except Exception as exc:  # gaierror, UnicodeError, ...
            box["error"] = exc

    t = threading.Thread(target=target, daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        return "timeout", None
    if "error" in box:
        return "error", box["error"]
    return "ok", box["result"]


def system_lookup(host, timeout=3.0, retries=2):
    """Return ('resolves'|'nxdomain_local'|'unknown', detail)."""
    detail = ""
    for attempt in range(retries + 1):
        status, value = _getaddrinfo(host, timeout)
        if status == "ok":
            return "resolves", "OS resolver"
        if status == "error" and isinstance(value, socket.gaierror) and value.errno == socket.EAI_NONAME:
            return "nxdomain_local", f"OS resolver: {value}"
        detail = "OS resolver timeout" if status == "timeout" else f"OS resolver: {value}"
        time.sleep(0.5 * (attempt + 1))
    return "unknown", detail


def doh_lookup(host, timeout=5.0):
    """Ask public DNS-over-HTTPS resolvers. Return ('resolves'|'nxdomain'|
    'no_address'|'unknown', detail)."""
    try:
        import requests
    except ImportError:
        return "unknown", "requests not installed; DNS-over-HTTPS skipped"
    try:
        name = host.encode("idna").decode("ascii")
    except UnicodeError:
        return "unknown", "invalid host name"
    last = "no DNS-over-HTTPS answer"
    with _DOH_LIMIT:
        for url, headers in DOH_PROVIDERS:
            provider = urlparse(url).hostname
            try:
                statuses = []
                for rtype in ("A", "AAAA"):
                    resp = requests.get(url, params={"name": name, "type": rtype}, headers=headers, timeout=timeout)
                    data = resp.json()
                    statuses.append(data.get("Status"))
                    if data.get("Status") == 0 and data.get("Answer"):
                        return "resolves", f"{provider} {rtype}"
                if 3 in statuses:
                    return "nxdomain", f"{provider}: NXDOMAIN"
                if statuses and all(s == 0 for s in statuses):
                    return "no_address", f"{provider}: no A/AAAA record"
                last = f"{provider}: DNS status {statuses}"
            except Exception as exc:  # network error, bad JSON
                last = f"{provider}: {type(exc).__name__}"
    return "unknown", last


def http_probe(host, timeout=8.0):
    try:
        import requests
    except ImportError:
        return "http_skipped", "requests not installed"
    headers = {"User-Agent": _BROWSER_UA}
    for scheme in ("https", "http"):
        url = f"{scheme}://{host}/"
        try:
            resp = requests.head(url, headers=headers, timeout=timeout, allow_redirects=True)
            if resp.status_code in (405, 501) or resp.status_code >= 500:
                resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True, stream=True)
            final = qc.url_domain(resp.url)
            moved = f"; redirects to {final}" if final and final != qc.registrable_domain(host) else ""
            code = resp.status_code
            if code < 400:
                return "http_ok", f"{code}{moved}"
            if code in (401, 403, 429, 503):
                return "http_blocked", f"{code} (bot protection; site is up){moved}"
            return "http_error", f"{code}{moved}"
        except Exception as exc:
            last = f"{scheme}: {type(exc).__name__}"
    return "http_unreachable", last + " (not proof the site is down)"


def verify_domain_dns(domain, timeout=3.0, retries=2, use_doh=True):
    """Return (domain, status, detail)."""
    if not domain:
        return domain, "unknown", "Empty domain"
    host = domain.split(":")[0]
    status, detail = system_lookup(host, timeout, retries)
    if status == "resolves":
        return domain, "resolves", detail
    if not use_doh:
        return domain, "unknown", detail + " (not confirmed; run without --no-doh to confirm)"
    doh_status, doh_detail = doh_lookup(host)
    if doh_status == "no_address" and not host.startswith("www."):
        # Some sites only publish an address for www.<domain>.
        www_status, www_detail = doh_lookup("www." + host)
        if www_status == "resolves":
            return domain, "resolves", f"www.{host} via {www_detail} (bare domain has no address)"
    if doh_status == "unknown":
        return domain, "unknown", f"{detail}; {doh_detail}"
    return domain, doh_status, f"{doh_detail} (local: {detail})"


def verify_dataset_domains(excel_path, url_column="website", max_workers=50, timeout=3.0, retries=2,
                           use_doh=True, http=False, output=None, sheet=None, engine=None):
    with qc.timed("Load"):
        df = qc.load_dataset(excel_path, sheet=sheet, required_columns=[url_column], engine=engine)

    rows_by_host = defaultdict(list)
    social = defaultdict(list)
    for url, sh, row in zip(df[url_column], df[qc.SHEET_COL], df[qc.ROW_COL]):
        if not str(url).strip():
            continue
        ref = qc.row_ref(sh, row)
        label = qc.social_or_listing(url)
        if label:
            social[label].append(ref)
            continue
        host = qc.host_from_url(url, keep_www=True)
        rows_by_host[host or f"(unparseable) {str(url).strip()}"].append(ref)

    domains = sorted(h for h in rows_by_host if not h.startswith("(unparseable)"))
    print(f"Extracted {len(domains):,} unique domain names to verify "
          f"(timeout {timeout:.0f}s, {retries} retries, DNS-over-HTTPS confirmation {'on' if use_doh else 'off'})...")

    results = {}
    with qc.timed("DNS"), ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(verify_domain_dns, d, timeout, retries, use_doh): d for d in domains}
        for n, future in enumerate(as_completed(futures), 1):
            dom, status, msg = future.result()
            results[dom] = (status, msg)
            if n % 500 == 0:
                qc.LOG.info("  %s/%s domains checked", f"{n:,}", f"{len(domains):,}")

    if http:
        live = [d for d, (s, _) in results.items() if s == "resolves"]
        with qc.timed("HTTP"), ThreadPoolExecutor(max_workers=min(max_workers, 20)) as executor:
            futures = {executor.submit(http_probe, d): d for d in live}
            for future in as_completed(futures):
                d = futures[future]
                h_status, h_detail = future.result()
                results[d] = (results[d][0], results[d][1], h_status, h_detail)

    counts = defaultdict(int)
    for v in results.values():
        counts[v[0]] += 1
    unparseable = [h for h in rows_by_host if h.startswith("(unparseable)")]

    print("\n" + "=" * 50)
    print("DNS SOCKET VERIFICATION RESULTS")
    print("=" * 50)
    print(f"Total Unique Domains Tested: {len(domains):,}")
    print(f"Resolving                   : {counts['resolves']:,}")
    print(f"Dead (NXDOMAIN, confirmed)  : {counts['nxdomain']:,}")
    print(f"No address record           : {counts['no_address']:,}")
    print(f"Unknown (could not check)   : {counts['unknown']:,}  <- not evidence of a dead site")
    print(f"Social/listing URLs         : {sum(len(v) for v in social.values()):,} rows {dict((k, len(v)) for k, v in social.items()) or ''}")
    print(f"Unparseable website values  : {len(unparseable):,}")
    if http:
        hc = defaultdict(int)
        for v in results.values():
            if len(v) > 2:
                hc[v[2]] += 1
        print(f"HTTP probe                  : {dict(hc)}")
    print("=" * 50)

    for status in ("nxdomain", "no_address", "unknown"):
        bad = [d for d, v in results.items() if v[0] == status][:10]
        if bad:
            print(f"\nSample [{status}]:")
            for d in bad:
                print(f"  - {d}: {results[d][1]} (rows: {', '.join(rows_by_host[d][:5])})")

    if output:
        records = []
        for d, v in sorted(results.items()):
            records.append({"domain": d, "status": v[0], "detail": v[1],
                            "http_status": v[2] if len(v) > 2 else "", "http_detail": v[3] if len(v) > 3 else "",
                            "row_count": len(rows_by_host[d]), "rows": " ".join(rows_by_host[d])})
        for label, refs in social.items():
            records.append({"domain": label, "status": "social_listing", "detail": "not an official website",
                            "row_count": len(refs), "rows": " ".join(refs)})
        for h in unparseable:
            records.append({"domain": h, "status": "unparseable", "detail": "", "row_count": len(rows_by_host[h]),
                            "rows": " ".join(rows_by_host[h])})
        qc.write_records(records, output)
    return results


def main():
    parser = argparse.ArgumentParser(description="Fast Zero-Cost DNS Socket Domain Verifier")
    parser.add_argument("excel_path", help="Path to input Excel dataset")
    parser.add_argument("--column", default="website", help="Column name containing URLs/domains (default: website)")
    parser.add_argument("--workers", type=int, default=50, help="Parallel worker threads (default: 50)")
    parser.add_argument("--timeout", type=float, default=3.0, help="Seconds per OS lookup attempt (default: 3)")
    parser.add_argument("--retries", type=int, default=2, help="Retries after a timeout or resolver error (default: 2)")
    parser.add_argument("--no-doh", action="store_true", help="Do not confirm failures over DNS-over-HTTPS")
    parser.add_argument("--http", action="store_true", help="Also probe each live domain over HTTP(S)")
    parser.add_argument("--output", help="Write every domain with its status and rows to this .csv or .json file")
    parser.add_argument("--sheet", default=None, help="Only this sheet (default: every sheet with the column)")
    parser.add_argument("--engine", default=None, help="Excel reader engine (default: calamine if installed)")
    qc.add_logging_args(parser)
    args = parser.parse_args()
    qc.setup_logging(args)

    verify_dataset_domains(args.excel_path, args.column, args.workers, timeout=args.timeout, retries=args.retries,
                           use_doh=not args.no_doh, http=args.http, output=args.output, sheet=args.sheet,
                           engine=args.engine)


if __name__ == "__main__":
    main()
