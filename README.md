# ARK holdings tracker

A daily archive of what ARK Invest's ETFs hold, reduced to the part you can
actually buy, published as a single self-contained page.

ARK overwrites one CSV per fund in place and keeps no history. Archiving each
day's file is therefore the whole point — everything else is rebuilt from it.

## Pipeline

Each step defaults to the newest data on disk, so ordinary runs take no arguments.

| Step | What it does | Cadence |
|------|--------------|---------|
| `fetch.py` | Downloads the 8 ETF files plus ARKVX into `data/raw/<date>/` | daily |
| `baseline.py` | Parses, collapses duplicates, merges across funds on CUSIP | daily |
| `tradeable.py` | Keeps US-listed equities; drops cash, private placements, bitcoin holdcos, foreign lines, OTC ADRs and IZRL | daily |
| `quotes.py` | Last price and 52-week range from Yahoo | daily |
| `fundamentals.py` | Market cap, sector, industry from the Nasdaq screener | daily |
| `financials.py` | Revenue, margin, cash, runway, dilution from SEC XBRL | quarterly, currently unused |
| `report.py` | Renders the bilingual HTML report | daily |
| `build_site.py` | Rebuilds every date into `site/` for publishing | daily |

```bash
python3 fetch.py && python3 baseline.py && python3 tradeable.py && \
python3 quotes.py && python3 fundamentals.py && python3 report.py --open
```

No API keys anywhere: ARK, Nasdaq Trader, the Nasdaq screener, Yahoo and SEC
EDGAR are all open endpoints.

## Things that will break, and how you'll know

**Fund renames.** ARK renamed ARKF and ARKX; the old filenames keep returning
HTTP 200 with data frozen at the rename date. `fetch.py` treats a fund lagging
the rest of the complex as a hard failure rather than a quiet stale read. ARKW
is scheduled to become the ARK Next Generation Technology ETF on 2026-09-07 —
expect that to trip.

**Ticker collisions.** Matching on ticker alone put Airbus on AAR Corp and
Titomic on a Treasury ETF. `listings.py` requires the issuer names to agree, and
`quotes.py` cross-checks every quote against ARK's own implied price.

**Nasdaq sector labels.** Frequently wrong — SpaceX is tagged Computer Software,
GE Aerospace as Consumer Electronics. Good enough to filter on, not to classify.

## Data

`data/raw/<date>/` holds the bytes exactly as ARK served them; everything under
`data/*.csv` is derived and reproducible. SEC company facts are cached under
`data/reference/companyfacts/` and excluded from git — they are large and
rebuildable.

## Publishing

`.github/workflows/update.yml` runs the pipeline on weekday mornings, commits
the day's CSVs, and deploys `site/` to GitHub Pages. Reports are not stored in
the repository; they are rebuilt from the committed CSVs on every run, so a
template change reflows the whole archive at once.

---

Holdings data, not investment advice.
