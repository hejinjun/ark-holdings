"""Reduce a day's positions to the tradeable universe: US-listed equities only.

  python3 tradeable.py [YYYY-MM-DD]

Three things get dropped, and each is reported rather than silently discarded:

  excluded fund   IZRL is a Tel Aviv universe -- see EXCLUDED_FUNDS
  not an equity   cash, the bitcoin holdcos, and the OpenAI private placement
  not US-listed   foreign local lines, and OTC ADRs, which trade in the US but
                  are on no US exchange -- surfaced as their own bucket so the
                  call to keep or drop them stays visible
  excluded venue  NYSE Arca, which lists funds rather than operating companies

Re-aggregation happens after the fund filter, so a security's totals reflect
only the funds still in scope.
"""

import csv
import sys
from pathlib import Path

import listings

DATA = Path(__file__).parent / "data"

# IZRL holds Israeli companies listed in Tel Aviv, which are not accessible
# from a US brokerage account.
EXCLUDED_FUNDS = {"IZRL"}

KEEP_CLASSES = {"equity"}

# NYSE Arca lists chiefly ETFs and funds rather than operating companies.
EXCLUDED_EXCHANGES = {"NYSE Arca"}


def is_adr(company: str) -> bool:
    return "ADR" in company.upper()


def main(date: str) -> int:
    src = DATA / f"positions_{date}.csv"
    if not src.exists():
        raise SystemExit(f"missing {src.name} -- run: python3 baseline.py {date}")

    listed = listings.load()
    rows = list(csv.DictReader(src.open(encoding="utf-8")))

    kept, dropped = [], {"fund": [], "class": [], "adr": [], "unlisted": [], "exchange": []}
    for r in rows:
        if r["fund"] in EXCLUDED_FUNDS:
            dropped["fund"].append(r)
            continue
        if r["asset_class"] not in KEEP_CLASSES:
            dropped["class"].append(r)
            continue
        hit = listings.lookup(r["ticker"], listed, r["company"])
        if not hit:
            dropped["adr" if is_adr(r["company"]) else "unlisted"].append(r)
            continue
        symbol, exchange, name = hit
        if exchange in EXCLUDED_EXCHANGES:
            dropped["exchange"].append(r)
            continue
        kept.append({**r, "symbol": symbol, "exchange": exchange, "listed_name": name})

    # Merge across the funds that survived the filter.
    agg: dict[str, dict] = {}
    for p in kept:
        a = agg.setdefault(p["symbol"], {
            "symbol": p["symbol"], "exchange": p["exchange"], "cusip": p["cusip"],
            "company": p["company"], "total_shares": 0.0, "total_market_value": 0.0,
            "funds": [], "by_fund_shares": {},
        })
        a["total_shares"] += float(p["shares"])
        a["total_market_value"] += float(p["market_value"])
        a["funds"].append(p["fund"])
        a["by_fund_shares"][p["fund"]] = float(p["shares"])
    merged = sorted(agg.values(), key=lambda a: -a["total_market_value"])

    out = DATA / f"tradeable_{date}.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["symbol", "exchange", "cusip", "company", "total_shares",
                    "total_market_value", "n_funds", "funds", "by_fund_shares"])
        for a in merged:
            w.writerow([
                a["symbol"], a["exchange"], a["cusip"], a["company"],
                f"{a['total_shares']:.0f}", f"{a['total_market_value']:.2f}",
                len(a["funds"]), "|".join(sorted(a["funds"])),
                ";".join(f"{f}={a['by_fund_shares'][f]:.0f}" for f in sorted(a["by_fund_shares"])),
            ])

    report(date, rows, kept, dropped, merged)
    print(f"\nwrote {out.name}")
    return 0


def mv(rs) -> float:
    return sum(float(r["market_value"]) for r in rs)


def report(date, rows, kept, dropped, merged):
    total = mv(rows)
    print(f"Tradeable universe -- {date}\n")
    print(f"{'':2}{'bucket':<34}{'positions':>10}{'market value':>17}{'share':>8}")
    buckets = [
        ("kept: US-listed equities", kept),
        (f"dropped: excluded fund ({'/'.join(sorted(EXCLUDED_FUNDS))})", dropped["fund"]),
        ("dropped: not an equity", dropped["class"]),
        ("dropped: OTC ADR (no US exchange)", dropped["adr"]),
        ("dropped: not US-listed", dropped["unlisted"]),
        (f"dropped: {'/'.join(sorted(EXCLUDED_EXCHANGES))}", dropped["exchange"]),
    ]
    for label, rs in buckets:
        print(f"{'':2}{label:<34}{len(rs):>10}{mv(rs):>17,.0f}{mv(rs)/total:>8.2%}")
    print(f"{'':2}{'TOTAL':<34}{len(rows):>10}{total:>17,.0f}{1:>8.2%}")

    print(f"\nunique tradeable symbols: {len(merged)}")
    print(f"tradeable market value  : {sum(a['total_market_value'] for a in merged):,.0f}")

    for key, label in (("adr", "OTC ADRs"), ("unlisted", "not US-listed"),
                       ("class", "not an equity")):
        rs = dropped[key]
        if not rs:
            continue
        seen, uniq = set(), []
        for r in sorted(rs, key=lambda r: -float(r["market_value"])):
            if r["cusip"] in seen:
                continue
            seen.add(r["cusip"])
            uniq.append(r)
        print(f"\n{label} ({len(uniq)} securities):")
        for r in uniq[:12]:
            print(f"  {(r['ticker'] or '—'):<9}{r['company'][:38]:<40}"
                  f"{float(r['market_value']):>14,.0f}")
        if len(uniq) > 12:
            print(f"  ... and {len(uniq) - 12} more")


if __name__ == "__main__":
    dates = sorted(p.name.removeprefix("positions_").removesuffix(".csv")
                   for p in DATA.glob("positions_*.csv"))
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else dates[-1]))
