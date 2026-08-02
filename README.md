# ARK holdings tracker

A daily archive of what ARK Invest's ETFs hold, reduced to the part you can
actually buy, published as a single self-contained page.

ARK overwrites one CSV per fund in place and keeps no history. Archiving each
day's file is therefore the whole point — everything else is rebuilt from it.

Nasdaq's stock screener behaves the same way, so the market cap leaderboard is
archived on the same principle: `leaders.html` ranks the 300 largest companies
trading on a US exchange, and can say who climbed and who dropped out only
because yesterday's ranking was written down.

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
| `leaders.py` | Snapshots the 300 largest companies on the US market, and quotes them | daily, after `fundamentals.py` |
| `xueqiu.py` | Year-to-date, trailing P/E and dividend yield, and a second opinion on market cap | daily, after `leaders.py` |
| `report.py` | Renders the bilingual HTML report | daily |
| `home.py` | Renders the daily brief: the day's moves and every source's freshness | daily |
| `thirteenf.py` | Ingests a manager's 13F filings as position snapshots | quarterly |
| `issuers.py` | Identifies the issuer behind a filing line: CUSIP + name -> US ticker | with each ingest |
| `build_site.py` | Rebuilds every date into `site/` for publishing | daily |

```bash
python3 fetch.py && python3 baseline.py && python3 tradeable.py && \
python3 quotes.py && python3 fundamentals.py && python3 report.py --open
```

`leaders.py` reads the screener cache, so it must run after `fundamentals.py`
has refreshed it. A run with no arguments snapshots today and rebuilds the page;
`--refresh` fetches the screener itself first. Dates are UTC everywhere, so a
local run and the scheduled job land on the same file rather than inventing a
day of rank movement between them.

No API keys anywhere: ARK, Nasdaq Trader, the Nasdaq screener, Yahoo and SEC
EDGAR are all open endpoints.

## Other managers

`thirteenf.py <manager>` writes `data/<manager>/positions_<period>.csv` in the
same schema the ARK ingest produces, so `diff.py --source <manager>` runs over
it unchanged. Two things do not carry over from ARK:

**Flow correction is off for a 13F.** Dividing out the day's median ratio is
what isolates an ETF manager's decision from creations and redemptions. A 13F
filer has no such mechanism, so that ratio *is* a decision — Duquesne cut ~10%
across the book in Q2 2025, and correcting for it reported untouched positions
as 10% buys and dropped the real trims entirely. `diff.CREATES_UNITS` names the
sources the correction applies to.

**A filing names holdings by CUSIP, not ticker.** `issuers.py` closes that gap:
OpenFIGI first, then a scored name match against every US listing, then a
hand-checked override table. It accepts only above a bar calibrated to sit
above the observed error band and prints everything below it for review, so
adding a manager is: run the ingest, run `python3 issuers.py <manager>`, check
the proposals, paste the confirmed ones into `OVERRIDES`.

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

**Dual-class lines on the leaderboard.** The screener reports Alphabet's whole
market cap against both GOOG and GOOGL, and Berkshire's against both classes.
Summing them invents a company and shifts every rank below it, while looking
entirely plausible. `leaders.py` collapses the known pairs by hand and
`check_unhandled()` fails the build when a new one appears rather than counting
it twice. Fox and News Corp are the other kind — each class carries its own cap
— and are deliberately left alone.

**Securities that are not companies.** `CCZ` is Comcast Holdings' zero-coupon
exchangeable notes, and the screener prices it at $234B against Comcast's own
common at $85B — a debt instrument outranking the company it converts into.
Excluded by name. The near-misses are the reason the rule is narrow: `BNS` reads
"Bank Nova Scotia Halifax Pfd 3 Ordinary Shares" but is the common, and Digital
Realty **Trust** and Warner Bros. Discovery **Series A** are ordinary companies.

**Market cap on an ADR.** Nasdaq and Xueqiu quote the same last sale, so when
they disagree on market cap they disagree on share count — and an ADR ratio is
where share counts go wrong. Nasdaq has Ferrari 33% high and Toyota 21% high;
Xueqiu multiplies Coca-Cola FEMSA's whole share count by the price of an ADR
worth ten of them and reports $182B for a company worth about $23B. Petrobras
differs for a third reason, a real one: Nasdaq counts the preferred class and
Xueqiu does not. `python3 xueqiu.py` prints every disagreement above 10% and
corrects nothing — there is no source here entitled to overrule the other.

**A second source that never forgets a ticker.** Xueqiu's ranking still lists
RDS.A, ANTM, BK, STO, MMC and MTU beside SHEL, ELV, BNY, EQNR, MRSH and MUFG —
the renamed lines that replaced them — so six companies appear twice in its top
300 and twelve real ones are pushed out of it. Its ratios are joined by symbol
and used; its membership is not. Nasdaq Trader's directory decides what is
listed, which is the same rule `listings.py` applies to the ARK book.

**Security-type words matched too widely.** The screener's name field is a
company name followed by a security type followed, sometimes, by a sentence
describing what the security represents — and that sentence is full of the same
words. `depositary shares` was excluded to catch preferred lines and silently
dropped every ADR with it, which is how most large foreign issuers trade here:
Alibaba, Shell, Sony, BHP, PDD, GSK and SK hynix, twelve companies above the
threshold at the time. Matching `units` or `rights` anywhere does the same to "each
representing one unit" and "the right to receive ten Class A Ordinary Shares".

`is_company()` therefore splits the test in two. Words that can only belong to
another instrument — `preferred`, `warrant`, `notes`, a percentage — disqualify
a row wherever they appear. Words that are only a security type when they *are*
the security type — `units`, `rights` — are tested against the name up to the
descriptive clause. A missing company is invisible in a ranking, so the failure
mode here is silence: check the tail of the list after changing these rules.

## The site

| Page | What it answers |
|------|-----------------|
| `index.html` | What ARK did in the last session, and whether every feed is current |
| `holdings.html` | The tradeable book on the newest date |
| `activity.html` | Every move over the last 30 sessions |
| `leaders.html` | The 300 largest companies on the US market, and what moved |
| `archive.html` | One report per archived date |

The home page holds no parsing of its own. Each source module answers for its
own data through a `summary()` — `report.summary()`, `activity.summary()`,
`leaders.summary()` — and `home.py` only arranges the answers, so adding a
source is a summary plus a card rather than a second copy of the merge rules.

Freshness is counted in sessions, not clock time, so a Friday file read on
Sunday is current. Market holidays are not modelled: the day after one reads
as a session behind, which errs toward looking.

Shared pieces are inlined into every page at build time by `shell.py` —
`styles.css` and `nav.js` — because each page has to stay a single file with
no external requests. Add a page to `NAV_PAGES` and `i18n.NAV` and it appears
in the nav on all of them.

## Data

`data/raw/<date>/` holds the bytes exactly as ARK served them; everything under
`data/*.csv` is derived and reproducible — with one exception.

`data/leaders_<date>.csv` is an archive, not a derivation. Nasdaq's screener
overwrites in place and keeps no history, exactly as ARK's files do, so nothing
can rebuild a past day's ranking once the endpoint has moved on. Delete one and
the rank movement, the entries and exits, and the record of where the threshold
used to sit go with it. The same holds for `data/leaders_meta.json`, which
stores each day's whole-market total so an archived page is measured against
its own day rather than against today. `data/leaders_quotes_<date>.csv` is the
52-week range for that snapshot and is optional: the page renders without it.

`data/leaders_xueqiu_<date>.csv` is the same kind of archive as the ranking
itself: point-in-time ratios behind an endpoint with no history.

Company descriptions in `data/descriptions*.json` cover 321 symbols — the ARK
book and the leaderboard — and were written by a language model, not taken from
filings. `data/descriptions/` keeps the per-batch inputs and outputs behind them.

SEC company facts are cached under `data/reference/companyfacts/` and excluded
from git — they are large and rebuildable.

## Publishing

`.github/workflows/update.yml` runs the pipeline on weekday mornings, commits
the day's CSVs, and deploys `site/` to GitHub Pages. Reports are not stored in
the repository; they are rebuilt from the committed CSVs on every run, so a
template change reflows the whole archive at once.

The workflow triggers on `schedule` and `workflow_dispatch` only, not on push:
a code change reaches the site when the next run happens, or when you ask for
one with `gh workflow run update.yml`. The cron covers Tuesday to Saturday, so
a Monday leaves a gap in the leaderboard archive and the movement column then
spans two days rather than one.

---

Holdings data, not investment advice.
