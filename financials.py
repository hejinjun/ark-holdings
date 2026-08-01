"""Pull six fundamentals per company from SEC EDGAR's XBRL company facts.

  python3 financials.py [YYYY-MM-DD] [--refresh] [--refresh-cik]

Raw company facts are cached under data/reference/companyfacts/; pass
--refresh to re-download them when new filings are expected.

Source is https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json, which
returns every XBRL value a company has ever filed. No key; SEC asks only for a
User-Agent carrying a contact address and roughly 10 requests a second.

Filings are quarterly, so this is not part of the daily pipeline -- run it
weekly, or when a company reports.

The work is not fetching, it is naming. The same line item is tagged differently
by different filers: Tesla's revenue is RevenueFromContractWithCustomer... while
others still use Revenues or SalesRevenueNet, and foreign private issuers file
under the IFRS taxonomy entirely. Every metric therefore has a fallback chain,
and which concept actually matched is recorded so a bad mapping is visible
rather than silently producing a blank.
"""

import csv
import json
import sys
import time
import urllib.request
from pathlib import Path

DATA = Path(__file__).parent / "data"
REF = DATA / "reference"
CIK_CACHE = REF / "company_tickers.json"
FACTS_DIR = REF / "companyfacts"
CIK_URL = "https://www.sec.gov/files/company_tickers.json"
FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{:010d}.json"

# SEC's fair-access policy asks for a real contact address in the User-Agent.
UA = "ark-holdings-research hejinjun 62hfdkv7vm@privaterelay.appleid.com"
DELAY = 0.3          # SEC drops connections when pushed; stay well inside 10/sec
RETRIES = 3

# Ordered fallbacks. First taxonomy/concept that yields usable periods wins.
# "flow" metrics are measured over a period; "stock" metrics at an instant.
METRICS = {
    "revenue": ("flow", [
        ("us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax"),
        ("us-gaap", "RevenueFromContractWithCustomerIncludingAssessedTax"),
        ("us-gaap", "Revenues"),
        ("us-gaap", "SalesRevenueNet"),
        ("us-gaap", "SalesRevenueGoodsNet"),
        ("us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTaxMember"),
        ("ifrs-full", "Revenue"),
        ("ifrs-full", "RevenueFromContractsWithCustomers"),
    ]),
    "gross_profit": ("flow", [
        ("us-gaap", "GrossProfit"),
        ("ifrs-full", "GrossProfit"),
    ]),
    "cost_of_revenue": ("flow", [
        ("us-gaap", "CostOfRevenue"),
        ("us-gaap", "CostOfGoodsAndServicesSold"),
        ("us-gaap", "CostOfServices"),
        ("ifrs-full", "CostOfSales"),
    ]),
    "net_income": ("flow", [
        ("us-gaap", "NetIncomeLoss"),
        ("us-gaap", "ProfitLoss"),
        ("us-gaap", "NetIncomeLossAvailableToCommonStockholdersBasic"),
        ("ifrs-full", "ProfitLoss"),
    ]),
    "operating_cash_flow": ("flow", [
        ("us-gaap", "NetCashProvidedByUsedInOperatingActivities"),
        ("us-gaap", "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"),
        ("ifrs-full", "CashFlowsFromUsedInOperatingActivities"),
    ]),
    "cash": ("stock", [
        ("us-gaap", "CashAndCashEquivalentsAtCarryingValue"),
        ("us-gaap", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"),
        ("ifrs-full", "CashAndCashEquivalents"),
    ]),
    "short_term_investments": ("stock", [
        ("us-gaap", "ShortTermInvestments"),
        ("us-gaap", "MarketableSecuritiesCurrent"),
        ("us-gaap", "AvailableForSaleSecuritiesDebtSecuritiesCurrent"),
    ]),
    # Share count is reported two ways: as an instant on the cover page, or as
    # a weighted average over a period. Both are accepted -- companies like
    # Quantum-Si file only the latter.
    "shares": ("either", [
        ("dei", "EntityCommonStockSharesOutstanding"),
        ("us-gaap", "CommonStockSharesOutstanding"),
        ("ifrs-full", "NumberOfSharesOutstanding"),
        ("us-gaap", "WeightedAverageNumberOfDilutedSharesOutstanding"),
        ("us-gaap", "WeightedAverageNumberOfSharesOutstandingBasic"),
    ]),
}

ANNUAL = (330, 400)     # days; 10-K / 20-F periods
QUARTER = (75, 115)     # days; 10-Q / 6-K periods


def fetch(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    last = None
    for attempt in range(1, RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                return json.load(resp)
        except Exception as exc:
            last = exc
            if attempt == RETRIES:
                raise last
            time.sleep(1.5 * attempt)
    raise AssertionError("unreachable")


def company_facts(cik: int, refresh: bool = False) -> dict:
    """Fetch one company's facts, cached on disk.

    These payloads run to several megabytes and EDGAR starts dropping
    connections if the same ones are pulled repeatedly, so a re-run -- or a
    debugging session -- must not mean re-downloading.
    """
    FACTS_DIR.mkdir(parents=True, exist_ok=True)
    path = FACTS_DIR / f"CIK{cik:010d}.json"
    if path.exists() and not refresh:
        return json.loads(path.read_text(encoding="utf-8"))
    data = fetch(FACTS_URL.format(cik))
    path.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    return data


def cik_map(refresh: bool = False) -> dict[str, int]:
    REF.mkdir(parents=True, exist_ok=True)
    if refresh or not CIK_CACHE.exists():
        CIK_CACHE.write_text(json.dumps(fetch(CIK_URL), separators=(",", ":")),
                             encoding="utf-8")
    raw = json.loads(CIK_CACHE.read_text(encoding="utf-8"))
    return {v["ticker"]: v["cik_str"] for v in raw.values()}


def cik_for(symbol: str, table: dict[str, int]) -> int | None:
    # EDGAR writes class shares as MOG-A; the holdings file uses MOG.A.
    for cand in (symbol, symbol.replace(".", "-"), symbol.replace(".", "")):
        if cand in table:
            return table[cand]
    return None


def days(entry: dict) -> int | None:
    if not entry.get("start"):
        return None
    from datetime import date
    a = date.fromisoformat(entry["start"])
    b = date.fromisoformat(entry["end"])
    return (b - a).days


def pick_periods(facts: dict, chain: list, kind: str) -> tuple[list, str | None, str | None]:
    """Return the periods, the concept they came from, and the unit.

    The chain is not first-match. A concept that stopped being used still holds
    years of history -- GE's RevenueFromContractWithCustomer... carries annual
    figures only through 2018, long after the company moved the line elsewhere.
    Taking the first hit would report an eight-year-old number as current, so
    every concept is scored on how recent its data is and the freshest wins,
    with chain order breaking ties.
    """
    best_rows, best_concept, best_unit, best_key = [], None, None, None

    for rank, (taxonomy, concept) in enumerate(chain):
        block = (facts.get(taxonomy) or {}).get(concept)
        if not block:
            continue
        for unit, rows in block.get("units", {}).items():
            # Any reporting currency is accepted -- Spotify files in EUR -- but
            # per-share units are never a total.
            if "/" in unit:
                continue
            picked: dict[tuple, dict] = {}
            for e in rows:
                if e.get("val") is None:
                    continue
                instant = not e.get("start")
                if kind == "stock" and not instant:
                    continue
                if kind == "flow" and instant:
                    continue
                if instant:
                    key = (e["end"],)
                else:
                    d = days(e)
                    if d is None:
                        continue
                    if ANNUAL[0] <= d <= ANNUAL[1]:
                        key = (e["start"], e["end"], "A")
                    elif QUARTER[0] <= d <= QUARTER[1]:
                        key = (e["start"], e["end"], "Q")
                    else:
                        continue
                prev = picked.get(key)
                if prev is None or e.get("filed", "") > prev.get("filed", ""):
                    picked[key] = e
            if not picked:
                continue
            rows_sorted = sorted(picked.values(), key=lambda x: x["end"])
            # Rank on the newest annual period when there is one, since that is
            # the figure being reported; fall back to the newest period of any
            # length.
            annual_ends = [r["end"] for r in rows_sorted
                           if r.get("start") and ANNUAL[0] <= days(r) <= ANNUAL[1]]
            freshness = (annual_ends[-1] if annual_ends else rows_sorted[-1]["end"])
            key = (freshness, -rank)
            if best_key is None or key > best_key:
                best_rows, best_concept, best_unit, best_key = (
                    rows_sorted, f"{taxonomy}:{concept}", unit, key)

    return best_rows, best_concept, best_unit


def split_ap(rows: list) -> tuple[list, list]:
    annual = [r for r in rows if r.get("start") and ANNUAL[0] <= days(r) <= ANNUAL[1]]
    quarter = [r for r in rows if r.get("start") and QUARTER[0] <= days(r) <= QUARTER[1]]
    return annual, quarter


def extract(facts: dict) -> dict:
    out, matched, units = {}, {}, {}
    for name, (kind, chain) in METRICS.items():
        rows, concept, unit = pick_periods(facts, chain, kind)
        if not rows:
            out[name] = None
            continue
        matched[name] = concept
        units[name] = unit
        instants = [r for r in rows if not r.get("start")]
        annual, quarter = split_ap(rows)

        if kind == "stock" or (kind == "either" and instants):
            src = instants or rows
            latest = src[-1]
            block = {"value": latest["val"], "as_of": latest["end"]}
            prior = prior_year(src, latest["end"])
            if prior:
                block["prior"] = {"value": prior["val"], "as_of": prior["end"]}
            out[name] = block
        elif kind == "either":
            # Only weighted-average share counts on file; treat the newest
            # period's average as the current count.
            src = quarter or annual or rows
            latest = src[-1]
            block = {"value": latest["val"], "as_of": latest["end"], "basis": "weighted average"}
            prior = prior_year(src, latest["end"])
            if prior:
                block["prior"] = {"value": prior["val"], "as_of": prior["end"]}
            out[name] = block
        else:
            out[name] = {
                "annual": [{"end": r["end"], "value": r["val"]} for r in annual[-3:]],
                "quarterly": [{"end": r["end"], "value": r["val"]} for r in quarter[-5:]],
            }
    out["_concepts"] = matched
    out["_units"] = units
    return out


def prior_year(rows: list, latest_end: str) -> dict | None:
    """The observation closest to twelve months before `latest_end`.

    Anchoring on a date window rather than "the previous entry" matters: filings
    cluster, so the entry before the latest is often only weeks earlier, which
    would make share-count growth meaningless.
    """
    from datetime import date
    target = date.fromisoformat(latest_end)
    best, best_gap = None, None
    for r in rows:
        gap = (target - date.fromisoformat(r["end"])).days
        if not 300 <= gap <= 430:
            continue
        score = abs(gap - 365)
        if best_gap is None or score < best_gap:
            best, best_gap = r, score
    return best


def derive(f: dict) -> dict:
    """Turn raw line items into the handful of reads that matter for this book:
    growth, margin, cash runway and dilution."""
    d = {}

    def last(metric, period):
        block = f.get(metric)
        if not block or not block.get(period):
            return None
        return block[period][-1]

    rev_a, rev_q = last("revenue", "annual"), last("revenue", "quarterly")
    if rev_a:
        d["revenue_annual"] = rev_a["value"]
        d["revenue_annual_end"] = rev_a["end"]
        prior = (f["revenue"]["annual"] or [])[-2:-1]
        if prior and prior[0]["value"]:
            d["revenue_yoy_pct"] = round(
                100 * (rev_a["value"] / prior[0]["value"] - 1), 1)

    # Trailing twelve months, when four clean quarters are on file.
    q = (f.get("revenue") or {}).get("quarterly") or []
    if len(q) >= 4:
        d["revenue_ttm"] = sum(x["value"] for x in q[-4:])

    # Margin must be built from the same period on both lines. Each metric
    # picks its own freshest concept independently, so revenue can land on
    # FY2025 while cost of revenue's best concept stops at FY2023 -- pairing
    # those produced a -31.8% gross margin for GE.
    def at_end(metric, period, end):
        for row in ((f.get(metric) or {}).get(period) or []):
            if row["end"] == end:
                return row
        return None

    if rev_a and rev_a["value"]:
        gp = at_end("gross_profit", "annual", rev_a["end"])
        if gp:
            d["gross_margin_pct"] = round(100 * gp["value"] / rev_a["value"], 1)
        else:
            cor = at_end("cost_of_revenue", "annual", rev_a["end"])
            if cor:
                d["gross_margin_pct"] = round(
                    100 * (rev_a["value"] - cor["value"]) / rev_a["value"], 1)

    ni = last("net_income", "annual")
    if ni:
        d["net_income_annual"] = ni["value"]
        d["profitable"] = ni["value"] > 0

    cash = (f.get("cash") or {}).get("value")
    sti = (f.get("short_term_investments") or {}).get("value")
    if cash is not None:
        d["cash"] = cash + (sti or 0)
        d["cash_as_of"] = f["cash"]["as_of"]

    # Runway: how many quarters the current cash pile covers at the latest
    # quarterly operating burn. Only meaningful while operations consume cash.
    ocf_q = last("operating_cash_flow", "quarterly")
    ocf_a = last("operating_cash_flow", "annual")
    burn = None
    if ocf_q and ocf_q["value"] < 0:
        burn = -ocf_q["value"]
    elif ocf_a and ocf_a["value"] < 0:
        burn = -ocf_a["value"] / 4
    if burn:
        d["quarterly_burn"] = round(burn)
        if d.get("cash"):
            d["runway_quarters"] = round(d["cash"] / burn, 1)

    sh = f.get("shares")
    if sh:
        d["shares"] = sh["value"]
        d["shares_as_of"] = sh["as_of"]
        if sh.get("basis"):
            d["shares_basis"] = sh["basis"]
        prior = sh.get("prior")
        if prior and prior["value"]:
            change = round(100 * (sh["value"] / prior["value"] - 1), 1)
            # A year-on-year swing this large is a split, a reverse split or an
            # ADR ratio change, not dilution -- Alibaba's cover-page count moved
            # between ADSs and ordinary shares and read as -89.9%. Report the
            # break instead of a number that means nothing.
            if -60 <= change <= 100:
                d["share_growth_pct"] = change
            else:
                d["share_basis_changed"] = True
    return d


def main(date: str, refresh: bool, refresh_facts: bool) -> int:
    src = DATA / f"tradeable_{date}.csv"
    if not src.exists():
        raise SystemExit(f"missing {src.name} -- run: python3 tradeable.py {date}")
    rows = list(csv.DictReader(src.open(encoding="utf-8")))
    table = cik_map(refresh)

    out, no_cik, no_facts, errors = {}, [], [], []
    for i, r in enumerate(rows, 1):
        sym = r["symbol"]
        cik = cik_for(sym, table)
        if cik is None:
            no_cik.append(sym)
            continue
        try:
            facts = company_facts(cik, refresh_facts)
        except Exception as exc:
            errors.append((sym, str(exc)[:60]))
            print(f"  [{i:>3}/{len(rows)}] {sym:<8} ERROR {str(exc)[:50]}")
            time.sleep(DELAY)
            continue
        time.sleep(DELAY)

        raw = extract(facts.get("facts") or {})
        d = derive(raw)
        if not d:
            no_facts.append(sym)
            print(f"  [{i:>3}/{len(rows)}] {sym:<8} no reported facts yet")
            continue
        d["cik"] = cik
        d["concepts"] = raw["_concepts"]
        cur = raw["_units"].get("revenue") or raw["_units"].get("cash")
        if cur and cur != "USD":
            d["currency"] = cur
        out[sym] = d
        rev = d.get("revenue_annual")
        print(f"  [{i:>3}/{len(rows)}] {sym:<8}"
              f"{('rev ' + format(rev, ',')) if rev else 'no revenue':>22}"
              f"   {('margin ' + str(d['gross_margin_pct']) + '%') if 'gross_margin_pct' in d else '':<18}"
              f"{('runway ' + str(d['runway_quarters']) + 'q') if 'runway_quarters' in d else ''}")

    path = DATA / f"financials_{date}.json"
    path.write_text(json.dumps(out, indent=1, sort_keys=True), encoding="utf-8")
    report(rows, out, no_cik, no_facts, errors, path)
    return 0


def report(rows, out, no_cik, no_facts, errors, path):
    n = len(rows)
    print(f"\nfundamentals for {len(out)} of {n} symbols -> {path.name}")
    have = lambda k: sum(1 for d in out.values() if k in d)
    for key, label in (("revenue_annual", "revenue"), ("gross_margin_pct", "gross margin"),
                       ("net_income_annual", "net income"), ("cash", "cash"),
                       ("runway_quarters", "runway"), ("share_growth_pct", "share growth")):
        print(f"  {label:<14}{have(key):>4}/{len(out)}")
    if no_facts:
        print(f"\nno filings yet ({len(no_facts)}): {', '.join(no_facts)}")
    if no_cik:
        print(f"no CIK ({len(no_cik)}): {', '.join(no_cik)}")
    if errors:
        print(f"errors ({len(errors)}):")
        for s, e in errors:
            print(f"  {s:<8}{e}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dates = sorted(p.name.removeprefix("tradeable_").removesuffix(".csv")
                   for p in DATA.glob("tradeable_*.csv"))
    raise SystemExit(main(args[0] if args else dates[-1],
                          "--refresh-cik" in sys.argv,
                          "--refresh" in sys.argv))
