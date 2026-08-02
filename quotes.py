"""Fetch last price and 52-week range for the tradeable universe.

  python3 quotes.py [YYYY-MM-DD]

Source is Yahoo Finance's chart endpoint, whose `meta` block carries the last
price and the 52-week high/low directly. It needs no key, but it is an
undocumented endpoint: it rate-limits, resets connections under load, and can
change shape without notice. Every response is therefore checked rather than
trusted, and the raw JSON is not relied on beyond the handful of fields below.

Each quote is cross-checked against ARK's own mark for the same security
(market value / shares). A large gap means the symbol mapping is wrong -- a
ticker that resolved to a different company -- not that the stock moved.
"""

import csv
import json
import sys
import time
import urllib.request
from pathlib import Path

DATA = Path(__file__).parent / "data"


SOURCE = "ark"


def use_source(name: str) -> None:
    """ARK stays at the data root; an ingested filer lives in its own
    directory. Every read goes through DATA, so rebinding it is the whole
    change."""
    global DATA, SOURCE
    SOURCE = name
    DATA = Path(__file__).parent / "data"
    if name != "ark":
        DATA = DATA / name
    if not DATA.is_dir():
        raise SystemExit(f"no data for source {name!r} at {DATA}")


def positional(argv: list[str]) -> list[str]:
    """Arguments that are not flags, and not a flag's value.

    A bare `--source duquesne` otherwise leaves "duquesne" looking like a
    positional date, which is exactly how it was first read."""
    takes_value = {"--source", "--days", "--out"}
    out, skip = [], False
    for a in argv:
        if skip:
            skip = False
            continue
        if a in takes_value:
            skip = True
            continue
        if a.startswith("--"):
            continue
        out.append(a)
    return out
ENDPOINT = "https://query1.finance.yahoo.com/v8/finance/chart/{}?range=1d&interval=1d"
UA = "Mozilla/5.0 (compatible; ark-baseline/1.0)"
RETRIES = 4
DELAY = 0.25          # between symbols, to stay under the rate limit
MARK_TOLERANCE = 0.25  # flag when the quote is >25% from ARK's own mark


def to_yahoo(symbol: str) -> str:
    """Nasdaq writes class shares as MOG.A; Yahoo wants MOG-A."""
    return symbol.replace(".", "-")


def fetch(symbol: str) -> dict:
    url = ENDPOINT.format(to_yahoo(symbol))
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    last = ""
    for attempt in range(1, RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                payload = json.load(resp)
            break
        except Exception as exc:
            last = str(exc)
            if attempt == RETRIES:
                return {"status": "net_error", "detail": last}
            time.sleep(1.5 * attempt)
    else:
        return {"status": "net_error", "detail": last}

    result = (payload.get("chart") or {}).get("result")
    if not result:
        err = (payload.get("chart") or {}).get("error") or {}
        return {"status": "not_found", "detail": err.get("description", "no result")}

    m = result[0].get("meta") or {}
    price, lo, hi = (m.get("regularMarketPrice"), m.get("fiftyTwoWeekLow"),
                     m.get("fiftyTwoWeekHigh"))
    if price is None or lo is None or hi is None:
        return {"status": "incomplete", "detail": "missing price or 52w range"}
    if not (lo <= price <= hi):
        # Yahoo occasionally serves a stale range; keep the row but say so.
        return {"status": "range_stale", "price": price, "low": lo, "high": hi,
                "currency": m.get("currency"), "exchange": m.get("fullExchangeName")}
    return {"status": "ok", "price": price, "low": lo, "high": hi,
            "currency": m.get("currency"), "exchange": m.get("fullExchangeName")}


def main(date: str) -> int:
    src = DATA / f"tradeable_{date}.csv"
    if not src.exists():
        raise SystemExit(f"missing {src.name} -- run: python3 tradeable.py {date}")
    rows = list(csv.DictReader(src.open(encoding="utf-8")))

    out_rows, failed, suspect = [], [], []
    for i, r in enumerate(rows, 1):
        q = fetch(r["symbol"])
        time.sleep(DELAY)
        if q["status"] in ("net_error", "not_found", "incomplete"):
            failed.append((r["symbol"], q["status"], q.get("detail", "")))
            print(f"  [{i:>3}/{len(rows)}] {r['symbol']:<8} {q['status']}")
            continue

        shares = float(r["total_shares"])
        ark_mark = float(r["total_market_value"]) / shares if shares else 0.0
        drift = abs(q["price"] - ark_mark) / ark_mark if ark_mark else 0.0
        if drift > MARK_TOLERANCE:
            suspect.append((r["symbol"], r["company"], ark_mark, q["price"], drift))

        span = q["high"] - q["low"]
        out_rows.append({
            "symbol": r["symbol"],
            "company": r["company"],
            "exchange": r["exchange"],
            "price": f"{q['price']:.4f}",
            "week52_low": f"{q['low']:.4f}",
            "week52_high": f"{q['high']:.4f}",
            # 0% = at the 52-week low, 100% = at the high.
            "range_pct": f"{100 * (q['price'] - q['low']) / span:.2f}" if span else "",
            "off_high_pct": f"{100 * (q['price'] / q['high'] - 1):.2f}" if q["high"] else "",
            # Gain off the 52-week low, measured against the low itself. This is
            # not range_pct: that normalises by the high-low span, so a wide
            # range flatters a small bounce and a narrow one exaggerates it.
            "off_low_pct": f"{100 * (q['price'] / q['low'] - 1):.2f}" if q["low"] else "",
            "ark_mark": f"{ark_mark:.4f}",
            "mark_drift_pct": f"{100 * (q['price'] / ark_mark - 1):.2f}" if ark_mark else "",
            "total_market_value": r["total_market_value"],
            "funds": r["funds"],
            "status": q["status"],
        })
        print(f"  [{i:>3}/{len(rows)}] {r['symbol']:<8} {q['price']:>10,.2f}  "
              f"52w {q['low']:>9,.2f} – {q['high']:>9,.2f}")

    out = DATA / f"quotes_{date}.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        w.writerows(out_rows)

    print(f"\nquoted {len(out_rows)} of {len(rows)} symbols -> {out.name}")
    if failed:
        print(f"\nfailed ({len(failed)}):")
        for s, st, d in failed:
            print(f"  {s:<8}{st:<14}{d[:60]}")
    if suspect:
        print(f"\nquote disagrees with ARK's mark by >{MARK_TOLERANCE:.0%} "
              f"-- check the symbol mapping ({len(suspect)}):")
        for s, name, mark, px, dr in sorted(suspect, key=lambda x: -x[4]):
            print(f"  {s:<8}{name[:30]:<32}ARK {mark:>10,.2f}   Yahoo {px:>10,.2f}"
                  f"   {dr:>7.0%}")
    return 1 if failed else 0


if __name__ == "__main__":
    if "--source" in sys.argv:
        use_source(sys.argv[sys.argv.index("--source") + 1])
    args = positional(sys.argv[1:])
    dates = sorted(p.name.removeprefix("tradeable_").removesuffix(".csv")
                   for p in DATA.glob("tradeable_*.csv"))
    raise SystemExit(main(args[0] if args else dates[-1]))
