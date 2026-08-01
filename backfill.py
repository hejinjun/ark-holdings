"""Backfill historical holdings into data/raw/, in ARK's own CSV format.

  python3 backfill.py 2026-07-01 2026-07-30

ARK overwrites its files in place, so history can only come from someone who
archived it. arkfunds.io did. Its rows were checked against ARK's own file for
2026-07-31 -- same 48 positions, same CUSIPs, same share counts, no drift -- so
it is trustworthy as a source for dates that predate this project.

Output is written in ARK's exact column layout so the rest of the pipeline
cannot tell the difference, with a SOURCE file in each backfilled directory
recording where the day came from. Days this project fetched itself are left
untouched.
"""

import csv
import json
import sys
import time
import urllib.request
from pathlib import Path

from funds import ETFS

DATA = Path(__file__).parent / "data"
RAW = DATA / "raw"
API = "https://arkfunds.io/api/v2/etf/holdings"
UA = "Mozilla/5.0 (compatible; ark-holdings/1.0)"
COLUMNS = ["date", "fund", "company", "ticker", "cusip",
           "shares", "market value ($)", "weight (%)"]
DELAY = 0.4


def fetch(fund: str, start: str, end: str) -> list[dict]:
    url = f"{API}?symbol={fund}&date_from={start}&date_to={end}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(req, timeout=40) as resp:
                return json.load(resp).get("holdings") or []
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2 * attempt)
    return []


def as_ark_row(h: dict) -> dict:
    """Render one API row the way ARK writes it, so parsers stay identical."""
    y, m, d = h["date"].split("-")
    return {
        "date": f"{m}/{d}/{y}",
        "fund": h["fund"],
        "company": h.get("company") or "",
        "ticker": h.get("ticker") or "",
        "cusip": h.get("cusip") or "",
        "shares": f"{h['shares']:,.0f}" if h.get("shares") is not None else "",
        "market value ($)": (f"${h['market_value']:,.2f}"
                             if h.get("market_value") is not None else ""),
        "weight (%)": f"{h['weight']:.2f}%" if h.get("weight") is not None else "",
    }


def main(start: str, end: str) -> int:
    by_date: dict[str, dict[str, list]] = {}
    for fund in ETFS:
        try:
            rows = fetch(fund, start, end)
        except Exception as exc:
            print(f"  {fund:6} FAILED  {str(exc)[:60]}")
            continue
        for h in rows:
            by_date.setdefault(h["date"], {}).setdefault(fund, []).append(h)
        dates = sorted({h["date"] for h in rows})
        print(f"  {fund:6} {len(rows):>6} rows over {len(dates)} day(s)")
        time.sleep(DELAY)

    written, skipped = 0, 0
    for date in sorted(by_date):
        out = RAW / date
        # Never overwrite a day this project fetched from ARK directly. The
        # test is whether ETF originals are present, not whether the directory
        # exists: a day may hold only the monthly venture fund.
        if any((out / f"{f}.csv").exists() for f in ETFS) and not (out / "SOURCE").exists():
            skipped += 1
            continue
        missing = [f for f in ETFS if f not in by_date[date]]
        if missing:
            print(f"  {date}: incomplete, missing {missing} -- skipped")
            continue
        out.mkdir(parents=True, exist_ok=True)
        for fund, rows in by_date[date].items():
            with (out / f"{fund}.csv").open("w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=COLUMNS)
                w.writeheader()
                w.writerows(as_ark_row(h) for h in
                            sorted(rows, key=lambda x: -(x.get("market_value") or 0)))
        (out / "SOURCE").write_text(
            f"arkfunds.io/api/v2/etf/holdings backfill, retrieved {time.strftime('%Y-%m-%d')}\n",
            encoding="utf-8")
        written += 1

    print(f"\nbackfilled {written} day(s); {skipped} already held ARK originals")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit("usage: python3 backfill.py <start YYYY-MM-DD> <end YYYY-MM-DD>")
    raise SystemExit(main(sys.argv[1], sys.argv[2]))
