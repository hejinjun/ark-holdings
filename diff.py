"""Derive ARK's trades by differencing consecutive holdings snapshots.

  python3 diff.py                        # ARK, newest pair of dates
  python3 diff.py --all                  # every consecutive pair
  python3 diff.py --source duquesne --all

ARK publishes what it holds, never what it traded, so the trades have to be
inferred. The naive difference is wrong, and wrong in a way that looks
plausible: when money flows into or out of an ETF the authorised participant
creates or redeems units, and every position moves proportionally. On a day of
heavy redemption a naive diff reports the fund "sold" all forty holdings, which
is noise dressed as conviction.

So each fund's share counts are first divided by the day's flow factor -- the
median ratio across positions held on both days, which is exactly 1.0 when no
units were created. What survives that division is the active decision.

Diffing is done on shares, never on market value: market value moves with price
every single day whether or not anyone traded.

Dating: ARK's file for day D states the portfolio at the *beginning* of D, so
the change between file D-1 and file D is the trading that happened during
D-1. Output is therefore stamped with the earlier snapshot's date. Checked
against an independent reconstruction over 29 sessions: 82% of tickers in
common and 204 of 205 directions agreeing, which only lines up under this
convention.
"""

import csv
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).parent / "data"
DATA = ROOT   # rebound by --source; ARK lives at the root for historical reasons
SOURCE = "ark"

# Which sources create and redeem units. This is the question the flow
# correction below answers, and it has to be asked of the source rather than
# computed, because the arithmetic cannot tell the two cases apart.
#
# An ETF's authorised participant moves every position proportionally, so the
# median ratio is mechanical and dividing it out is what isolates the manager's
# decision. A 13F filer has no such mechanism: there the median ratio IS a
# decision -- the manager scaling the whole book -- and dividing it out inverts
# the reading. Duquesne cut ~10% across the board in Q2 2025; with the
# correction applied, positions left untouched were reported as 10% buys and
# the genuine trims disappeared entirely.
CREATES_UNITS = {"ark"}

# Residual noise after dividing out the flow: rounding in ARK's own numbers
# leaves ratios a hair off 1.0, so a position must move more than this fraction
# of itself to count as traded.
ACTIVE_THRESHOLD = 0.005
# A position smaller than this many shares produces meaningless percentages.
MIN_SHARES = 1


def snapshots() -> list[str]:
    return sorted(p.name.removeprefix("positions_").removesuffix(".csv")
                  for p in DATA.glob("positions_*.csv"))


def load(date: str) -> dict[tuple[str, str], dict]:
    path = DATA / f"positions_{date}.csv"
    out = {}
    with path.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            out[(r["fund"], r["cusip"])] = {
                "fund": r["fund"], "cusip": r["cusip"], "ticker": r["ticker"],
                "company": r["company"], "asset_class": r["asset_class"],
                "shares": float(r["shares"]), "weight": float(r["weight"]),
                "market_value": float(r["market_value"]),
            }
    return out


def flow_factor(prev: dict, curr: dict, fund: str) -> tuple[float, int]:
    """How much the whole fund was scaled by creations or redemptions.

    The median is the right estimator here, not the mean: on any given day a
    handful of positions were genuinely traded, and those are the outliers the
    median is designed to ignore.

    Pinned to 1.0 for a source that cannot create or redeem -- see
    CREATES_UNITS. The basis count is still returned, so the report shows how
    many positions the number would have rested on.
    """
    ratios = []
    for key, before in prev.items():
        if key[0] != fund or key not in curr:
            continue
        if before["shares"] < MIN_SHARES:
            continue
        ratios.append(curr[key]["shares"] / before["shares"])
    if SOURCE not in CREATES_UNITS or len(ratios) < 5:
        return 1.0, len(ratios)
    return statistics.median(ratios), len(ratios)


def compare(prev_date: str, curr_date: str) -> tuple[list[dict], dict]:
    prev, curr = load(prev_date), load(curr_date)
    funds = sorted({k[0] for k in prev} | {k[0] for k in curr})
    factors = {f: flow_factor(prev, curr, f) for f in funds}

    trades = []
    for key in set(prev) | set(curr):
        fund, cusip = key
        k = factors[fund][0]
        before, after = prev.get(key), curr.get(key)

        if before is None:
            trades.append({**after, "action": "new", "prev_shares": 0.0,
                           "expected_shares": 0.0, "active_shares": after["shares"],
                           "active_pct": None, "flow_factor": k})
            continue
        if after is None:
            trades.append({**before, "action": "exit", "prev_shares": before["shares"],
                           "shares": 0.0, "expected_shares": before["shares"] * k,
                           "active_shares": -before["shares"], "active_pct": -100.0,
                           "flow_factor": k})
            continue

        expected = before["shares"] * k
        active = after["shares"] - expected
        if expected < MIN_SHARES:
            continue
        pct = 100 * active / expected
        if abs(active) / expected <= ACTIVE_THRESHOLD:
            continue
        trades.append({**after, "action": "buy" if active > 0 else "sell",
                       "prev_shares": before["shares"], "expected_shares": expected,
                       "active_shares": active, "active_pct": pct, "flow_factor": k})

    order = {"new": 0, "buy": 1, "sell": 2, "exit": 3}
    trades.sort(key=lambda t: (order[t["action"]], -move_value(t), t["fund"], t["cusip"]))
    return trades, factors


def move_value(t: dict) -> float:
    """Rough dollar size of the move, for ordering only.

    Priced off whichever share count is non-zero: an exit reports zero shares
    held, so pricing off `shares` gives every exit a weight of zero, they all
    tie, and their order falls to set iteration -- which differs between runs
    and rewrites the file on every rebuild. Fund and CUSIP break the remaining
    ties so the output is reproducible.
    """
    base = t["shares"] or t["prev_shares"]
    return abs(t["active_shares"] * (t["market_value"] / base if base else 0.0))


def write(trade_date: str, from_date: str, to_date: str, trades: list[dict]) -> Path:
    path = DATA / f"trades_{trade_date}.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["trade_date", "from_snapshot", "to_snapshot", "fund", "action",
                    "ticker", "company", "cusip", "asset_class", "prev_shares",
                    "shares", "expected_shares", "active_shares", "active_pct",
                    "flow_factor"])
        for t in trades:
            w.writerow([
                trade_date, from_date, to_date,
                t["fund"], t["action"], t["ticker"], t["company"], t["cusip"],
                t["asset_class"], f"{t['prev_shares']:.0f}", f"{t['shares']:.0f}",
                f"{t['expected_shares']:.0f}", f"{t['active_shares']:.0f}",
                "" if t["active_pct"] is None else f"{t['active_pct']:.2f}",
                f"{t['flow_factor']:.6f}",
            ])
    return path


def report(prev_date, curr_date, trades, factors):
    print(f"trades of {prev_date}   (snapshots {prev_date} -> {curr_date})\n")
    print(f"{'fund':<7}{'flow':>10}{'basis':>7}   {'new':>4}{'buy':>5}{'sell':>6}{'exit':>6}")
    for fund in sorted(factors):
        k, n = factors[fund]
        ft = [t for t in trades if t["fund"] == fund]
        c = {a: sum(1 for t in ft if t["action"] == a) for a in ("new", "buy", "sell", "exit")}
        flow = f"{(k - 1) * 100:+.2f}%" if SOURCE in CREATES_UNITS else "n/a"
        print(f"{fund:<7}{flow:>10}{n:>7}   {c['new']:>4}{c['buy']:>5}{c['sell']:>6}{c['exit']:>6}")
    if SOURCE not in CREATES_UNITS:
        print(f"  flow n/a: {SOURCE} does not create or redeem units, so every "
              f"share change is a decision")

    if not trades:
        print("\nno active trades")
        return
    print(f"\n{len(trades)} active trade(s):")
    print(f"  {'fund':<6}{'action':<7}{'ticker':<8}{'company':<28}"
          f"{'shares':>12}{'of position':>13}")
    for t in trades[:25]:
        pct = "" if t["active_pct"] is None else f"{t['active_pct']:+.1f}%"
        print(f"  {t['fund']:<6}{t['action']:<7}{(t['ticker'] or '—'):<8}"
              f"{t['company'][:27]:<28}{t['active_shares']:>12,.0f}{pct:>13}")
    if len(trades) > 25:
        print(f"  ... and {len(trades) - 25} more")


def main(argv: list[str]) -> int:
    global DATA, SOURCE
    if "--source" in argv:
        SOURCE = argv[argv.index("--source") + 1]
        DATA = ROOT if SOURCE == "ark" else ROOT / SOURCE
        if not DATA.is_dir():
            raise SystemExit(f"no such source: {DATA}")
    dates = snapshots()
    if len(dates) < 2:
        raise SystemExit(f"need two snapshots to diff; have {len(dates)}")
    pairs = list(zip(dates, dates[1:])) if "--all" in argv else [(dates[-2], dates[-1])]
    for prev_date, curr_date in pairs:
        trades, factors = compare(prev_date, curr_date)
        path = write(prev_date, prev_date, curr_date, trades)
        if len(pairs) == 1:
            report(prev_date, curr_date, trades, factors)
            print(f"\nwrote {path.name}")
        else:
            print(f"{prev_date}: {len(trades):>3} trades -> {path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
