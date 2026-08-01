"""Download today's ARK holdings CSVs into data/raw/<as-of-date>/.

Archives the bytes exactly as served so the parsing rules can change later and
be replayed over history. The as-of date comes from the CSV's own `date` column,
not from the wall clock: ARK overwrites one file per fund in place and does not
update it on weekends or holidays.

Staleness is a hard failure. When ARK renames a fund the old filename keeps
serving HTTP 200 with data frozen at the rename date, so a fund lagging the rest
of the complex means the URL in funds.py needs updating -- not that the fund had
a quiet day.
"""

import csv
import io
import sys
import time
import urllib.request
from collections import Counter
from pathlib import Path

from funds import ALL_FUNDS, ETFS, VENTURE, url_for

RAW_DIR = Path(__file__).parent / "data" / "raw"
UA = "Mozilla/5.0 (compatible; ark-baseline/1.0)"
RETRIES = 3


def download(fund: str) -> str:
    req = urllib.request.Request(url_for(fund), headers={"User-Agent": UA})
    for attempt in range(1, RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode("utf-8-sig")
        except Exception:
            if attempt == RETRIES:
                raise
            time.sleep(2 * attempt)
    raise AssertionError("unreachable")


def as_of(text: str) -> str:
    """Most common date in the file, as MM/DD/YYYY."""
    rows = list(csv.DictReader(io.StringIO(text)))
    dates = Counter(r["date"] for r in rows if r.get("date"))
    if not dates:
        raise ValueError("no date column values")
    return dates.most_common(1)[0][0]


def to_iso(mdy: str) -> str:
    m, d, y = mdy.split("/")
    return f"{y}-{m}-{d}"


def main() -> int:
    saved, failed = {}, []
    for fund in ALL_FUNDS:
        try:
            text = download(fund)
            iso = to_iso(as_of(text))
        except Exception as exc:
            failed.append((fund, exc))
            print(f"  {fund:6} FAILED  {exc}")
            continue
        out = RAW_DIR / iso / f"{fund}.csv"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        saved[fund] = iso
        print(f"  {fund:6} {iso}  {len(text):>7,} bytes")

    # ETFs are daily and must all agree; the venture fund is monthly and is
    # expected to lag, so it is reported but never gates the run.
    etf_dates = {f: d for f, d in saved.items() if f in ETFS}
    stale = []
    if etf_dates:
        latest = max(etf_dates.values())
        stale = sorted(f for f, d in etf_dates.items() if d != latest)
        print(f"\nlatest ETF as-of: {latest}")
    for fund in VENTURE:
        if fund in saved:
            print(f"{fund} (monthly): {saved[fund]}")

    if stale:
        print(
            f"\nSTALE: {', '.join(stale)} lag the rest of the complex -- "
            "check for a fund rename and update funds.py",
            file=sys.stderr,
        )
    if failed:
        print(f"{len(failed)} fund(s) failed to download", file=sys.stderr)
    return 1 if (failed or stale) else 0


if __name__ == "__main__":
    raise SystemExit(main())
