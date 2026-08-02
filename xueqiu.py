"""Xueqiu's US screener: the per-company metrics Nasdaq's does not carry.

  python3 xueqiu.py [YYYY-MM-DD]

Year-to-date return, trailing P/E and dividend yield are absent from the Nasdaq
screener, and computing them from primary sources would mean a year of prices,
four quarters of earnings and a dividend history per company. Xueqiu publishes
all three for the whole US market behind an endpoint that needs no account.

It is also a second opinion on market cap, which is the more valuable thing.
Both sources price the same security at the same last sale, so any disagreement
is a disagreement about share count -- and share count is exactly what an ADR
makes hard. Neither source is reliably right about it:

  RACE   Nasdaq 234M shares, Xueqiu 176M. Ferrari has ~176M; Nasdaq is 33% high.
  KOF    The ADR is 1:10. Xueqiu multiplies the whole share count by the ADR
         price and reports $182B against a company worth about $23B; Nasdaq
         reports $5.7B, which is too low. Both are wrong.
  PBR    Nasdaq counts the preferred class too, Xueqiu does not. A difference
         of definition rather than an error.

So this is not a correction feed and must not be used as one. It flags rows
where the two disagree enough to be worth a look, and nothing is overwritten.

What is NOT taken from here is membership. Xueqiu's list still carries tickers
that no longer trade -- RDS.A, ANTM, BK, STO, MMC, MTU, TFCFA, DCM -- alongside
the renamed lines that replaced them, so six companies appear twice in its
ranking and twelve real ones are pushed out of the top 200. Nasdaq Trader's
directory is the authority on what is listed.
"""

import csv
import json
import sys
import time
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path

DATA = Path(__file__).parent / "data"

# The screener rejects a request with no session cookie. Any page under
# xueqiu.com/hq issues one to an anonymous caller; no account is involved.
HOME = "https://xueqiu.com/hq"
LIST = ("https://stock.xueqiu.com/v5/stock/screener/quote/list.json"
        "?page={page}&size={size}&order=desc&order_by=market_capital"
        "&market=US&type=us")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
PAGE_SIZE = 90
DELAY = 0.6

# How far down to read. The ranking only needs its own 300, but a company can
# sit far lower here than in ours -- Ferrari is 182nd for us and 263rd there,
# and Xueqiu's list is padded with a dozen delisted tickers that push everything
# below them down -- so the fetch has to overshoot or the join silently misses
# the tail.
DEPTH = 600

# Disagreement worth printing. Below this the two sources are arguing about
# rounding and float definitions, not about the size of the company.
TOLERANCE = 0.10

COLUMNS = ["symbol", "market_capital", "pe_ttm", "dividend_yield",
           "ytd_pct", "price"]


def _opener():
    jar = CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    op.addheaders = [("User-Agent", UA), ("Accept", "application/json"),
                     ("Referer", "https://xueqiu.com/")]
    op.open(HOME, timeout=25).read()      # for the cookie, not the bytes
    return op


def fetch(depth: int = DEPTH) -> list[dict]:
    op = _opener()
    out, page = [], 1
    while len(out) < depth:
        url = LIST.format(page=page, size=PAGE_SIZE)
        with op.open(url, timeout=30) as resp:
            payload = json.load(resp)
        if payload.get("error_code") not in (0, "0"):
            raise SystemExit(f"xueqiu: {payload.get('error_description')}")
        rows = ((payload.get("data") or {}).get("list")) or []
        if not rows:
            break
        out.extend(rows)
        page += 1
        time.sleep(DELAY)
    return out[:depth]


def _num(v):
    return float(v) if isinstance(v, (int, float)) else None


def _blank(v):
    """The CSV cell for one field: the number, or empty when the feed had none.
    Zero is a number."""
    n = _num(v)
    return "" if n is None else n


def write(date: str, depth: int = DEPTH) -> Path:
    rows = fetch(depth)
    path = DATA / f"leaders_xueqiu_{date}.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        for r in rows:
            sym = (r.get("symbol") or "").strip()
            if not sym:
                continue
            # `or ""` would be wrong here: it turns a real zero into a blank,
            # and zero and absent are different facts. A company flat on the
            # year has a year-to-date of 0.00%, not a missing one. The archive
            # records what the source said; what to show is decided in load().
            w.writerow({
                "symbol": sym,
                "market_capital": _blank(r.get("market_capital")),
                "pe_ttm": _blank(r.get("pe_ttm")),
                "dividend_yield": _blank(r.get("dividend_yield")),
                "ytd_pct": _blank(r.get("current_year_percent")),
                "price": _blank(r.get("current")),
            })
    return path


def load(date: str) -> dict[str, dict]:
    """symbol -> {pe, dy, ytd, cap}. Empty when the day was not fetched."""
    path = DATA / f"leaders_xueqiu_{date}.csv"
    if not path.exists():
        return {}
    out = {}
    for r in csv.DictReader(path.open(encoding="utf-8")):
        e = {}
        # Year-to-date is shown whatever it is: flat on the year is a result.
        if r["ytd_pct"] != "":
            e["ytd"] = float(r["ytd_pct"])
        # P/E and yield are shown only when positive, which is the same as
        # saying a loss and a non-payer are rendered as no figure rather than
        # as a number. In practice the feed blanks both rather than returning a
        # zero or a negative -- checked across 600 symbols, no negative P/E and
        # no zero yield -- so this is the guard for the day that changes, not a
        # description of what arrives today.
        if r["pe_ttm"] != "" and float(r["pe_ttm"]) > 0:
            e["pe"] = float(r["pe_ttm"])
        if r["dividend_yield"] != "" and float(r["dividend_yield"]) > 0:
            e["dy"] = float(r["dividend_yield"])
        if r["market_capital"] != "" and float(r["market_capital"]) > 0:
            e["cap2"] = float(r["market_capital"])
        if e:
            out[r["symbol"]] = e
    return out


def disagreements(date: str, snapshot: list[dict]) -> list[tuple]:
    """Rows where the two sources differ on market cap by more than TOLERANCE,
    worst first. Returned, not applied."""
    other = load(date)
    out = []
    for r in snapshot:
        e = other.get(r["symbol"])
        if not e or "cap2" not in e or not e["cap2"]:
            continue
        drift = r["market_cap"] / e["cap2"] - 1
        if abs(drift) > TOLERANCE:
            out.append((r["symbol"], r["company"], r["market_cap"], e["cap2"], drift))
    return sorted(out, key=lambda x: -abs(x[4]))


def main(argv: list[str]) -> int:
    import leaders
    dates = leaders.snapshots()
    date = ([a for a in argv[1:] if not a.startswith("--")] or [dates[-1]])[0]

    path = write(date)
    n = sum(1 for _ in csv.DictReader(path.open(encoding="utf-8")))
    print(f"{path.name}  ({n} symbols)")

    snapshot = leaders.read_snapshot(date)
    joined = sum(1 for r in snapshot if r["symbol"] in load(date))
    print(f"joined {joined}/{len(snapshot)} of the ranking")

    bad = disagreements(date, snapshot)
    if bad:
        print(f"\nmarket cap disagrees by >{TOLERANCE:.0%} ({len(bad)}) -- "
              f"neither source is authoritative, check the ADR ratio:")
        for sym, name, ours, theirs, drift in bad:
            print(f"  {sym:<7}{name[:30]:<32}Nasdaq ${ours / 1e9:>7,.1f}B   "
                  f"Xueqiu ${theirs / 1e9:>7,.1f}B   {drift:>+7.0%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
