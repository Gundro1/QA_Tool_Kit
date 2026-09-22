# Field issues found while using the data-QA tools

This ledger lists every problem we hit running the toolkit on real franchise datasets
between 2026-09-15 and 2026-09-21: 11 country datasets (Angola, Bangladesh, Belgium,
Croatia, Czech Republic, Finland, Luxembourg, Slovakia, Slovenia, Switzerland, UAE;
67,533 rows in total), plus Slovenia and Iraq audits. Each entry gives what we saw,
why it happened, and what this branch changes.

Entries marked *(code review)* were found by reading the code, not in a run.

Kinds: **FP** false positive, **FN** missed issue (true gap), **BUG** wrong output
or crash, **PERF** too slow, **OPS** install, output or usability problem.

The numbers under *Verified* come from re-running the changed tool on the same files.

---

## All data tools

| # | Kind | What happened | Cause | Change |
|---|---|---|---|---|
| G1 | FN | A workbook with `Franchise` and `Solo` sheets was only half checked. | Every script called `pd.read_excel(path)`, which reads the first sheet only. | `qa_common.load_dataset` reads every data sheet and adds `_sheet` / `_row` so findings point at the real cell. Sheets without the data columns (`Change log`, `Issues log`) are skipped and logged. `--sheet` restricts to one sheet. |
| G2 | BUG | *(code review)* Row numbers could point at the wrong row. | `idx + 2` assumes one sheet and no dropped rows; `fuzzy-dedup` also paired `dropna()` names with un-dropped indices. | Row numbers come from `_row`, set at load time. |
| G3 | PERF | Loading the 67,533-row file took 19 s of every run. | openpyxl is slow on large workbooks. | Uses the `calamine` engine when `python-calamine` is installed: 2.5 s, identical values on all 11 datasets (0 cells differ). Falls back to openpyxl. `--engine` overrides. |
| G4 | OPS | Only the top 10–15 findings were printed; there was no way to get the full list for a fix script. | Console output only. | `--output file.csv|json` on every data tool writes every finding with sheet and row. |
| G5 | OPS | No way to see which step was slow, and progress text mixed with JSON on stdout. | `print` only. | Shared logging to stderr (`-v` / `-q`) with per-stage timings. Results stay on stdout, so `data-validator.py ... > report.json` still works. |
| G6 | OPS | `pip install -r requirements.txt` failed on Linux (`No matching distribution found for pywin32`). | `pywin32` and `docx2pdf` are Windows-only and only used by the two preview scripts. | Kept, with `; sys_platform == "win32"` markers. Works on Windows, Linux and macOS. |

## data-validator.py

| # | Kind | What happened | Cause | Change |
|---|---|---|---|---|
| V1 | FN | Duplicates were undercounted: Croatia 54 of 78 rows, Slovakia 0 of 6, UAE 48 of 50. The missed rows differed only in case or spacing (`Konzum … 38B` / `38b`, `Nike …  Mall`). | `df.duplicated` compares text exactly. | Adds `duplicate_rows_normalized` (case-, width- and whitespace-insensitive). The exact count is unchanged for comparison. *Verified:* 280 rows on the 11 datasets, matching the manual QA count (45 exact + 235 same-branch). |
| V2 | FP | Rows with a blank address counted as duplicates of each other. | `''` equals `''`. | The normalised pass skips rows with a blank key part and reports how many (`rows_with_blank_key_part`). |
| V3 | FP | Any value containing `Ã` or `Â` + a character was flagged as mojibake, including legitimate Portuguese/French capitals (`SÃO PAULO`, `CÂMARA`). Angola data is Portuguese. | The regex `Ã.|Â.` matches ordinary letters. | A run is flagged only if it really decodes as UTF-8 after re-encoding as Windows-1252 (`SÃ£o` → `São`). `U+FFFD` and `ï¿½` are still flagged. Lossy `?` replacement is its own type and not applied to URLs. |
| V4 | FP/FN | Postal codes were checked against the Belgian format only. `--country SI` or `HR` silently checked nothing. The default was `BE`. | One hard-coded `if country_code == "BE"`. | Per-row country from `country_code` (else `--country`), with patterns for 28 countries. Countries without postal codes (AE, AO, QA, HK) report any value. Unknown countries are skipped and listed. |
| V5 | FN | Finland had 2,673 postal codes with leading zeros stripped (`100` for `00100`). | Codes stored as numbers. | `postal_code_leading_zero_lost` and `postal_code_numeric_artifact`. *Verified:* 2,673. |
| V6 | FN | Franchise rules were not checked at all: `franchise_flag` spelled `Yes`/`TRUE` (55,409 rows), franchise rows without `franchise_name`, placeholder names that merge unrelated shops into one franchise (`Brand-Operated / Independent`, `Not Publicly Disclosed`: 424 UAE rows), Solo rows carrying `franchise_name`/`branch_count`, a `branch_count` that doesn't match the rows, rows on the wrong sheet for their flag. | No schema rules. | Runs automatically when `franchise_flag` and `franchise_name` exist; `--flag-values` sets the allowed pair. `branch_count` is counted per `country_code`, so a brand present in several countries of a combined file is not reported. *Verified:* 55,409 flag spellings, 424 placeholders, 0 branch-count mismatches, all matching the manual reports. |
| V7 | FN | Social-media pages in the website column (47 rows still open after correction), placeholder text as website, malformed URLs. | Not checked. | `website_is_social_or_listing`, `website_placeholder`, `website_malformed`. |
| V8 | FN | Google plus codes (`69FQ+GFM`) used as street addresses (71 cells). | Not checked. | `plus_code_in_address`. *Verified:* 71. |
| V9 | FN | `issues_summary` and `findings` in the JSON were always empty. | Never filled. | Filled: counts per check, and `--samples N` findings per check. |
| V10 | PERF | 28.7 s on 67,533 rows. | `iterrows()` over every cell. | Vectorised checks: 12.3 s including all the new checks, most of it loading. |
| V11 | FN | Leading/trailing or doubled spaces split otherwise identical values. | Not checked. | `untrimmed_or_double_spaces`. |

## fuzzy-dedup.py

| # | Kind | What happened | Cause | Change |
|---|---|---|---|---|
| F1 | PERF | 745 s (12.4 min) on 67,533 rows. The earlier run over the 11 datasets had to be given a 25-minute timeout per file. | Pure-Python `SequenceMatcher` over every pair in each city. | `rapidfuzz` `cdist` in blocks, over unique names only. *Verified:* 16 s for the same file. A difflib fallback with ratio upper-bound pre-filters is kept for installs without rapidfuzz, and a test checks both give the same pairs. |
| F2 | FP | Top pairs were different businesses: NRB Bank / NRBC Bank, Kia / Skoda dealer networks, Pomurske lekarne (pharmacies) / Pomurske mlekarne (dairy), Bull & Bear / Pull & Bear, two different Ibis Styles hotels. | Name similarity was the only signal. | Other columns are used as evidence. Different website domains mean different businesses, even at a shared address such as one road or a multi-brand dealer. The same website at different addresses means two branches of one brand. These pairs are counted as *suppressed* with the reason, and listed with `--show-suppressed`. *Verified:* all of the above are suppressed. |
| F3 | FN | Real spelling variants were buried among the false positives: `Bags & More` / `Bags&More` (hiding 4 duplicate branches in Slovenia) was only found by reading past the top pairs, and `Dosenbach + Sport` / `Dosenbach +Sport` was the only plausible hit in Switzerland's top 15. Variants in different cities were never compared, and case-only variants were skipped. | Pairs were compared only within one city and ranked by similarity alone. | New `spelling_variant` tier: names equal after ignoring case, accents, spaces, punctuation and a trailing legal suffix (`Ltd`, `AG`, `d.o.o.` …), across the whole file. *Verified:* 51 variant groups on the 11 datasets, e.g. `Dr. Max`/`Dr.Max`, `Raiffeisenbank`/`Raiffeisen Bank`, `Fielmann`/`Fielmann Ag`, `Popular Diagnostic Centre`/`… Ltd.`. Case-only variants rank last. |
| F4 | FN | Two names at the same address were reported the same as two names across town. | No address evidence. | `same_address_duplicate` tier, ranked first. |
| F5 | BUG | *(code review)* Crash on numeric names (`'int' object has no attribute 'lower'`), and rows with a blank city were never compared. | `read_excel` without `dtype=str`; `groupby` drops NaN keys. | Loaded as text; blank city is its own block. |

## taxonomy-aligner.py

| # | Kind | What happened | Cause | Change |
|---|---|---|---|---|
| T1 | FP | It proposed realigning Bauhaus (4 of 7 rows) and Petrol (302 of 303), which are genuinely different store formats: a DIY store versus a garden centre, a fuel station versus a car wash. On all 11 datasets it flagged 560 UAE and 59 Croatia rows, many of them mixed-format brands. | Any minority subcategory was "fixed" to the majority, with no confidence threshold. | Outliers are classified first: `realign` (clear majority), `format_variant` (the outlier rows use another storefront name, e.g. `Petrol Avtopralnice`), `mixed_review` (tie, weak majority below `--min-share`, or fewer than `--min-rows` rows), `allowlisted` (`--allowlist` file). Only `realign` rows are changed. *Verified:* on the Slovenia file, Petrol is `format_variant`, Bauhaus is `mixed_review`, and 0 rows are changed. |
| T2 | BUG | *(code review)* `--output` wrote a single-sheet workbook: the Solo sheet and the Change log were lost. | `df.to_excel(output_path)`. | Copies the workbook with openpyxl and changes only the realigned cells. *Verified:* on Croatia, both sheets were kept and exactly 25 cells changed. Writing over the input file is refused. |
| T3 | FN | 237 rows (UAE 198, Angola 39) used subcategory names the importer does not know (`Clothing & Apparel`, `Footwear`, `Home & Furniture`), and all of them would have failed at import. No QA check caught this. | No reference taxonomy. | `--taxonomy file` checks every row for an exact match against the official list: `subcategory_not_in_taxonomy`, `subcategory_under_wrong_category`, `subcategory_spelling_differs`. Reads CSV/XLSX, finding the header row itself and forward-filling merged category cells, or a JSON seed list. *Verified:* Angola 39, UAE 199, plus 5 UAE rows under the wrong category that had not been reported. |
| T4 | FP | `Konzum` and `KONZUM` were audited as two brands. | Grouped on raw text. | Grouped on normalised text; the most common spelling is displayed. |

## fast-dns-verifier.py

| # | Kind | What happened | Cause | Change |
|---|---|---|---|---|
| D1 | FP | In a sandbox, even `mercator.si` (the country's largest retailer) was reported dead, so none of the results could be trusted. | One `getaddrinfo` attempt; any failure counted as dead. | Every failure is re-checked over DNS-over-HTTPS (dns.google, then Cloudflare). Only a confirmed NXDOMAIN is `nxdomain`. Failures that cannot be confirmed are `unknown`, labelled "not evidence of a dead site". *Verified live:* the OS resolver timed out on `www.mercator.si`, DoH resolved it, and it was reported as resolving. |
| D2 | PERF | Re-checks were slow and stalled on DNS timeouts. | `getaddrinfo` has no timeout. | Each lookup runs in a daemon thread with `--timeout` (3 s) and `--retries` (2) with backoff. A test enforces the timeout. |
| D3 | FP | `tlscontact.com` was reported as having no address. | The script stripped `www.`, but some sites only publish an address for `www.<domain>`. | Looks up the host as written and falls back to `www.` before reporting `no_address`. |
| D4 | FN | Social-media URLs were resolved and counted as valid websites. | Not distinguished. | Reported separately as `social_listing`. |
| D5 | FN | A resolving domain says nothing about the site: parked, moved or bot-blocked sites all resolve. We also saw that an HTTP failure alone (curl `000`) is unreliable, because big sites block bots. | DNS only. | Optional `--http` probe (HEAD, then GET, browser user agent). 401/403/429/503 = `http_blocked`, which means the site is up. A redirect to another registrable domain is reported. A connection failure is labelled "not proof the site is down". |
| D6 | OPS | Failed domains couldn't be traced back to rows. | Domain list only. | `--output` lists every domain with its status and `sheet!row` references. |

## brand-existence-checker.py

| # | Kind | What happened | Cause | Change |
|---|---|---|---|---|
| B1 | FP | On Slovenia it flagged `Optika Ibis` (an optician) as a hotel chain. It also flagged hotels already filed under Travel & Vacation for "taxonomy alignment". | Substring match on `ibis`/`hotel`/`radisson`, whatever the category. | Hotel brands must start the name; the generic hotel words are whole words; rows already in an accommodation category are not flagged. *Verified on Slovenia:* 9 review flags became 3, each worth checking (`Hotel Planja` filed under Sports; `Hotel Kompas Bled` split from `Hotel Kompas`; `Kopitarna Maribor` split from `Kopitarna`). |
| B2 | FP | Any name containing `bank` with more than 3 words was flagged as having a "canton/city suffix" (`UniCredit Banka Slovenija d.d.`; the rule would equally flag `National Bank of Pakistan`). | Word-count heuristic. | Replaced by a general location-suffix rule: flag only when the name minus one of its own cities is *another brand in the same file*. Real company names that include a city (`Elektro Maribor`, `Lekarna Ljubljana`) are not flagged. |
| B3 | FP | Unflagged brands were labelled "Verified Present — Active franchise brand verified operating in SI", but nothing was verified. | Wording. | Status `No Flags`, reason "No screening rule matched. Presence in SI was not checked online." The script now calls itself a screener. |
| B4 | OPS | Keyword lists are German/Swiss (`bau`, `ingenieure`, `berater`) and not configurable. | Hard-coded. | `--rules rules.json` overrides any list (`b2b_keywords`, `hotel_brands`, `hotel_words`, `accommodation_words`, `edit_instructions`). |
| B5 | OPS | Reports landed in a `QA_Verification_Output` folder next to the input. Reading it back with a relative path failed (FileNotFoundError), and running on a backup copy wrote into the backups folder. | Output location fixed to the input's folder. | `--output-dir`; the default is unchanged but the absolute path is printed. |
| B6 | OPS | Reports run by other people were named `*_Azeez.xlsx`. | `--auditor` defaulted to `Azeez`. | Defaults to `$QA_AUDITOR`, else `QA`. `--auditor` still works. |
| B7 | OPS | `UserWarning: This pattern is interpreted as a regular expression, and has match groups`. | Capturing group in the B2B regex. | Non-capturing group. |
| B8 | FN | *(code review)* Solo rows (`franchise_flag = N`) were screened as franchise brands. | No flag filter. | Only franchise rows are screened when the column exists. |

## excel-ops.py, pdf-print.py

| # | Kind | What happened | Cause | Change |
|---|---|---|---|---|
| E1 | BUG | *(code review)* `excel-ops.py clean data.xlsx` overwrote the file with only its first sheet. | Single-sheet read and write, output defaulting to the input. | Every sheet is cleaned and written back. Writing a multi-sheet workbook to `.csv` is refused. |
| E2 | OPS | *(code review)* `merge` and `read` silently ignored all but the first sheet. | Default `sheet_name=0`. | Warns when other sheets exist; `merge --sheet` picks one. |
| P1 | OPS | `pdf-print.py` could not find a browser on Linux: only Windows paths were searched. | Windows-only discovery. | Also `CHROME_PATH`, `google-chrome`/`chromium`/`microsoft-edge` on `PATH`, and the macOS app bundles. The file URL is built with `Path.as_uri()` (it was `file:///` + a POSIX path, giving four slashes). |

## Documentation

| # | Kind | What happened | Change |
|---|---|---|---|
| X1 | OPS | The `CLAUDE.md` template in `AI-ASSISTANT-GUIDE.md` told assistants to sign every audit report as "Azeez", so reports by other people were misattributed. | The template now says to use the name of the person who ran the audit. |

## Not changed here (known limits, for discussion)

- **Address heuristics at scale.** An address-collision check on the 11 datasets flagged 21,642 rows (a third of the data): mall and office-tower addresses are shared by many businesses. City/state consistency flagged 17,251 rows, and missing house numbers 13,895. In Iraq, landmark-style addresses are normal and need locale-aware severity. These checks are not in this repository, but if they are added they need a shared-building allowlist and per-country severity.
- **Brand identity.** No script can tell that `Triumph` rows are motorcycle dealers rather than the lingerie brand, that `Sanitas` rows are bathroom showrooms rather than the insurer, or that `centrepoint.com` is a Thai hotel group rather than the UAE retailer. Those needed store-locator checks by a person. `fuzzy-dedup` and `data-validator` narrow down where to look.
- **Fix scripts should fail loudly on zero matches.** A typo (`Terme Zrece` for `Terme Zreče`) once made a fix silently touch 0 rows. `taxonomy-aligner --output` only writes rows it matched, but any future fix tool should stop when a rule matches nothing.
