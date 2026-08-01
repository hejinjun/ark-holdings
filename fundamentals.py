"""Company-level facts for the tradeable universe: market cap, sector, industry.

ARK's holdings files carry none of this, and Yahoo's chart endpoint does not
either. Nasdaq's screener returns the whole US listed universe in one request,
which is both cheaper and steadier than 137 per-symbol calls.

The response is cached to data/reference/. Market cap moves with the price, so
refresh it on the same cadence as quotes rather than treating it as static.
"""

import json
import sys
import urllib.request
from pathlib import Path

REF = Path(__file__).parent / "data" / "reference"
CACHE = REF / "nasdaq_screener.json"
# `download=true` returns the full universe regardless of `limit`; passing
# limit=0 instead makes the endpoint hang rather than returning everything.
URL = ("https://api.nasdaq.com/api/screener/stocks"
       "?tableonly=true&limit=25&offset=0&download=true")


def refresh() -> int:
    REF.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(URL, headers={
        "User-Agent": "Mozilla/5.0", "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=45) as resp:
        payload = json.load(resp)
    rows = (payload.get("data") or {}).get("rows") or []
    if not rows:
        raise SystemExit("screener returned no rows -- endpoint may have changed")
    CACHE.write_text(json.dumps(rows, separators=(",", ":")), encoding="utf-8")
    return len(rows)


def load() -> dict[str, dict]:
    """symbol -> {market_cap, sector, industry, ipo_year, country}."""
    if not CACHE.exists():
        refresh()
    out = {}
    for r in json.loads(CACHE.read_text(encoding="utf-8")):
        sym = (r.get("symbol") or "").strip()
        if not sym:
            continue
        try:
            cap = float(r.get("marketCap") or 0)
        except ValueError:
            cap = 0.0
        out[sym] = {
            "market_cap": cap,
            "sector": (r.get("sector") or "").strip(),
            "industry": (r.get("industry") or "").strip(),
            "ipo_year": (r.get("ipoyear") or "").strip(),
            "country": (r.get("country") or "").strip(),
        }
    return out


def lookup(symbol: str, facts: dict[str, dict]) -> dict | None:
    """Nasdaq's directory writes class shares as MOG.A here but MOG/A in the
    screener feed, so both separators are tried -- the same split that bit the
    listing match."""
    for cand in (symbol, symbol.replace(".", "/"), symbol.replace("/", ".")):
        if cand in facts:
            return facts[cand]
    return None


if __name__ == "__main__":
    n = refresh()
    print(f"cached {n:,} symbols -> {CACHE.relative_to(Path(__file__).parent)}")
    if "--check" in sys.argv:
        import csv
        facts = load()
        DATA = Path(__file__).parent / "data"
        latest = sorted(DATA.glob("tradeable_*.csv"))[-1]
        rows = list(csv.DictReader(latest.open(encoding="utf-8")))
        missing = [r["symbol"] for r in rows if not lookup(r["symbol"], facts)]
        print(f"coverage: {len(rows) - len(missing)}/{len(rows)}"
              + (f"  missing: {missing}" if missing else ""))
