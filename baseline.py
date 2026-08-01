"""Merge one day's raw ARK ETF holdings into a deduplicated position table.

Produces two files per as-of date:

  positions_<date>.csv  long format, one row per (fund, security) -- the fact
                        table daily diffs are computed against
  baseline_<date>.csv   one row per security, shares and market value summed
                        across every ETF that holds it

CUSIP is the merge key, not ticker: tickers change (Block trades as XYZ, was SQ)
and ARK leaves the column blank on non-listed positions, while CUSIP is present
on every row -- including the synthetic ones ARK mints for cash (X9USDGSFT),
the per-fund bitcoin holdcos (MM*), and private placements (PP*).

The venture fund (ARKVX) is excluded: it reports weights only, with no share
counts or market values, so there is nothing to sum into these totals.
"""

import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from funds import ETFS

DATA = Path(__file__).parent / "data"
DATE_RE = re.compile(r"^\d{2}/\d{2}/\d{4}$")


def classify(cusip: str) -> str:
    """Bucket a position by the shape of its CUSIP."""
    if cusip == "X9USDGSFT":
        return "cash"          # Goldman FS Treasury Obligations money market
    if cusip.startswith("MM"):
        return "bitcoin_holdco"  # Cayman sub holding ARKB, one CUSIP per fund
    if cusip.startswith("PP"):
        return "private"       # private placement (OpenAI Series C)
    return "equity"


def num(s: str) -> float:
    """Parse ARK's formatted numbers: '1,752,619', '$541,296,378.15', '9.42%'."""
    return float(re.sub(r"[$,%\s]", "", s or "0") or 0)


def load_fund(path: Path, fund: str) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            # The file ends with a one-field legal disclaimer that DictReader
            # hands back as a date with every other column None.
            if not DATE_RE.match((r.get("date") or "").strip()):
                continue
            cusip = (r.get("cusip") or "").strip()
            if not cusip:
                raise ValueError(f"{fund}: row without CUSIP: {r.get('company')!r}")
            rows.append({
                "date": r["date"].strip(),
                "fund": fund,
                "cusip": cusip,
                "ticker": (r.get("ticker") or "").strip(),
                "company": (r.get("company") or "").strip(),
                "asset_class": classify(cusip),
                "shares": num(r.get("shares", "")),
                "market_value": num(r.get("market value ($)", "")),
                "weight": num(r.get("weight (%)", "")),
            })
    return rows


def collapse_within_fund(rows: list[dict]) -> tuple[list[dict], list[str]]:
    """One row per (fund, cusip). ARK occasionally splits a position over
    multiple lines; sum them so the fund-level view has a unique key."""
    by_key: dict[tuple[str, str], dict] = {}
    dupes = []
    for r in rows:
        key = (r["fund"], r["cusip"])
        if key in by_key:
            prev = by_key[key]
            dupes.append(f"{r['fund']} {r['cusip']} {r['company']}")
            prev["shares"] += r["shares"]
            prev["market_value"] += r["market_value"]
            prev["weight"] += r["weight"]
        else:
            by_key[key] = dict(r)
    return list(by_key.values()), dupes


def merge_across_funds(positions: list[dict]) -> list[dict]:
    agg: dict[str, dict] = {}
    for p in positions:
        a = agg.setdefault(p["cusip"], {
            "cusip": p["cusip"],
            "ticker": p["ticker"],
            "company": p["company"],
            "asset_class": p["asset_class"],
            "total_shares": 0.0,
            "total_market_value": 0.0,
            "n_funds": 0,
            "funds": [],
            "by_fund_shares": {},
        })
        # Prefer a non-empty ticker if any fund reports one for this CUSIP.
        if not a["ticker"] and p["ticker"]:
            a["ticker"] = p["ticker"]
        a["total_shares"] += p["shares"]
        a["total_market_value"] += p["market_value"]
        a["n_funds"] += 1
        a["funds"].append(p["fund"])
        a["by_fund_shares"][p["fund"]] = p["shares"]
    out = list(agg.values())
    out.sort(key=lambda a: -a["total_market_value"])
    return out


def main(date: str) -> int:
    raw = DATA / "raw" / date
    if not raw.is_dir():
        print(f"no raw data at {raw}", file=sys.stderr)
        return 1

    positions, dupes = [], []
    missing = []
    for fund in ETFS:
        path = raw / f"{fund}.csv"
        if not path.exists():
            missing.append(fund)
            continue
        rows, d = collapse_within_fund(load_fund(path, fund))
        positions.extend(rows)
        dupes.extend(d)

    if missing:
        print(f"missing raw files for: {', '.join(missing)}", file=sys.stderr)
        return 1

    merged = merge_across_funds(positions)

    pos_path = DATA / f"positions_{date}.csv"
    with pos_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=[
            "date", "fund", "cusip", "ticker", "company",
            "asset_class", "shares", "market_value", "weight",
        ])
        w.writeheader()
        w.writerows(sorted(positions, key=lambda p: (p["fund"], -p["market_value"])))

    base_path = DATA / f"baseline_{date}.csv"
    with base_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow([
            "cusip", "ticker", "company", "asset_class",
            "total_shares", "total_market_value", "n_funds", "funds",
            "by_fund_shares",
        ])
        for a in merged:
            w.writerow([
                a["cusip"], a["ticker"], a["company"], a["asset_class"],
                f"{a['total_shares']:.4f}".rstrip("0").rstrip("."),
                f"{a['total_market_value']:.2f}",
                a["n_funds"], "|".join(sorted(a["funds"])),
                json.dumps(a["by_fund_shares"], separators=(",", ":")),
            ])

    report(date, positions, merged, dupes)
    print(f"\nwrote {pos_path.name} and {base_path.name}")
    return 0


def report(date, positions, merged, dupes):
    total_mv = sum(p["market_value"] for p in positions)
    by_class = defaultdict(float)
    for a in merged:
        by_class[a["asset_class"]] += a["total_market_value"]

    print(f"ARK ETF baseline -- as of {date}\n")
    print(f"{'fund':<8}{'positions':>10}{'market value':>18}")
    per_fund = defaultdict(lambda: [0, 0.0])
    for p in positions:
        per_fund[p["fund"]][0] += 1
        per_fund[p["fund"]][1] += p["market_value"]
    for fund in ETFS:
        n, mv = per_fund[fund]
        print(f"{fund:<8}{n:>10}{mv:>18,.0f}")
    print(f"{'TOTAL':<8}{len(positions):>10}{total_mv:>18,.0f}")

    print(f"\nunique securities after merge: {len(merged)}"
          f"  (from {len(positions)} fund-level positions)")
    multi = [a for a in merged if a["n_funds"] > 1]
    print(f"held by more than one fund:    {len(multi)}")

    print("\nby asset class:")
    for k in ("equity", "bitcoin_holdco", "private", "cash"):
        if k in by_class:
            print(f"  {k:<16}{by_class[k]:>18,.0f}{by_class[k]/total_mv:>8.2%}")

    print("\ntop 15 merged positions:")
    print(f"{'ticker':<8}{'company':<32}{'shares':>14}{'market value':>17}{'funds':>7}")
    for a in merged[:15]:
        print(f"{(a['ticker'] or '-'):<8}{a['company'][:31]:<32}"
              f"{a['total_shares']:>14,.0f}{a['total_market_value']:>17,.0f}"
              f"{a['n_funds']:>7}")

    if dupes:
        print(f"\nintra-fund duplicate CUSIPs collapsed: {dupes}")


if __name__ == "__main__":
    # Default to the newest snapshot on disk. A hardcoded date would keep
    # rebuilding the same day forever once this runs unattended.
    if len(sys.argv) > 1:
        raise SystemExit(main(sys.argv[1]))
    snapshots = sorted(p.name for p in (DATA / "raw").iterdir() if p.is_dir())
    if not snapshots:
        raise SystemExit("no snapshots in data/raw -- run fetch.py first")
    raise SystemExit(main(snapshots[-1]))
