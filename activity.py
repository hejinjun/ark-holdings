"""Render the trade feed: what ARK did, newest first.

  python3 activity.py [--days 30] [--open]

Rows are merged across funds. One fund adding to a name is a position change;
four funds adding to it on the same day is the firm agreeing with itself, and
that is the signal worth surfacing — so the number of funds acting together is
what the page sorts and highlights on, not the raw share count.

Reads data/trades_*.csv, which diff.py has already corrected for creations and
redemptions and stamped with the true trade date.
"""

import csv
import json
import sys
import webbrowser
from collections import defaultdict
from pathlib import Path

import i18n
import links
import report

HERE = Path(__file__).parent
DATA = HERE / "data"
TEMPLATE = HERE / "activity_template.html"

DEFAULT_DAYS = 30
# Sweeping the money-market position is cash management, not a view on a
# company, and it is large enough to sit at the top of every day if left in.
SKIP_CLASSES = {"cash"}
# Three or more funds moving the same way on the same day is the threshold the
# page treats as conviction rather than housekeeping.
CONVICTION = 3


def load_trades(days: int) -> list[dict]:
    paths = sorted(DATA.glob("trades_*.csv"))[-days:]
    rows = []
    for p in paths:
        with p.open(encoding="utf-8") as fh:
            rows.extend(r for r in csv.DictReader(fh)
                        if r.get("asset_class") not in SKIP_CLASSES)
    return rows


def merge(rows: list[dict]) -> list[dict]:
    """One entry per (date, security, direction), with the funds that acted."""
    groups: dict[tuple, dict] = {}
    for r in rows:
        side = "buy" if r["action"] in ("buy", "new") else "sell"
        key = (r["trade_date"], r["cusip"], side)
        shares = float(r["active_shares"])
        held = float(r["shares"]) or float(r["prev_shares"])
        # Approximate the trade's value at the day's own implied price.
        price = 0.0
        g = groups.setdefault(key, {
            "date": r["trade_date"], "cusip": r["cusip"], "ticker": r["ticker"],
            "company": r["company"], "side": side, "shares": 0.0,
            "funds": [], "actions": set(),
        })
        g["shares"] += shares
        g["funds"].append(r["fund"])
        g["actions"].add(r["action"])
        _ = held, price
    out = []
    for g in groups.values():
        g["funds"] = sorted(set(g["funds"]))
        # "new" and "exit" describe the position, not the direction, and take
        # precedence in the label: opening a position says more than adding.
        if "new" in g["actions"]:
            g["kind"] = "new"
        elif "exit" in g["actions"]:
            g["kind"] = "exit"
        else:
            g["kind"] = g["side"]
        del g["actions"]
        out.append(g)
    out.sort(key=lambda g: (g["date"], len(g["funds"]), abs(g["shares"])), reverse=True)
    return out


def price_map() -> dict[str, dict[str, float]]:
    """Implied price per snapshot date, keyed by CUSIP."""
    prices = {}
    for p in sorted(DATA.glob("positions_*.csv")):
        d = p.name.removeprefix("positions_").removesuffix(".csv")
        day = {}
        with p.open(encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                sh = float(r["shares"])
                if sh:
                    day[r["cusip"]] = float(r["market_value"]) / sh
        prices[d] = day
    return prices


def price_for(prices: dict, cusip: str, trade_date: str) -> float:
    """A newly opened position is absent from the snapshot named by its own
    trade date -- it first appears in the next one -- so fall forward."""
    days = sorted(prices)
    for d in days:
        if d >= trade_date and prices[d].get(cusip):
            return prices[d][cusip]
    for d in reversed(days):
        if prices[d].get(cusip):
            return prices[d][cusip]
    return 0.0


def build(days: int) -> dict:
    rows = load_trades(days)
    if not rows:
        raise SystemExit("no trades_*.csv found -- run diff.py --all first")
    merged = merge(rows)

    dates = sorted({g["date"] for g in merged})
    prices = price_map()
    for g in merged:
        g["value"] = abs(g["shares"]) * price_for(prices, g["cusip"], g["date"])

    descriptions = json.loads((DATA / "descriptions.json").read_text(encoding="utf-8")) \
        if (DATA / "descriptions.json").exists() else {}
    descriptions_zh = json.loads((DATA / "descriptions_zh.json").read_text(encoding="utf-8")) \
        if (DATA / "descriptions_zh.json").exists() else {}
    try:
        import financials
        ciks = financials.cik_map()
        cik_of = lambda t: financials.cik_for(t, ciks)
    except Exception:
        cik_of = lambda t: None

    events = []
    for g in merged:
        t = g["ticker"]
        events.append({
            "d": g["date"], "t": t, "n": g["company"], "k": g["kind"],
            "s": g["shares"], "v": g["value"], "f": g["funds"],
            "c": g["cusip"],
            **({"ds": descriptions[t]} if t in descriptions else {}),
            **({"dz": descriptions_zh[t]} if t in descriptions_zh else {}),
            **({"lk": links.for_symbol(t, cik_of(t))} if t else {}),
        })

    by_day = defaultdict(lambda: {"buy": 0, "sell": 0, "new": 0, "exit": 0})
    for e in events:
        by_day[e["d"]][e["k"]] += 1

    conviction = sum(1 for e in events if len(e["f"]) >= CONVICTION)
    funds = sorted({f for e in events for f in e["f"]})

    return {
        "asOf": dates[-1],
        "days": len(dates),
        "conviction": CONVICTION,
        "langs": [{"v": k, "label": lb} for k, lb in i18n.LANGS],
        "i18n": {k: page(k, dates, events, conviction) for k, _ in i18n.LANGS},
        "kinds": [{"v": k, "label": i18n.ACTIVITY[ "en"][k], "label_zh": i18n.ACTIVITY["zh"][k]}
                  for k in ("new", "buy", "sell", "exit")],
        "funds": [{"v": f, "label": f, "label_zh": f} for f in funds],
        "sites": links.SITES,
        "events": events,
        "byDay": [{"d": d, **by_day[d]} for d in sorted(by_day, reverse=True)],
    }


def page(lang: str, dates: list[str], events: list[dict], conviction: int) -> dict:
    c = i18n.ACTIVITY_PAGE[lang]
    return {
        "eyebrow": c["eyebrow"],
        "title": c["title"],
        "standfirst": c["standfirst"],
        "provenance": c["provenance"].format(
            first=dates[0], last=dates[-1], days=len(dates), n=len(events)),
        "tiles": [
            [c["tileSessions"], str(len(dates)), c["tileSessionsNote"].format(first=dates[0])],
            [c["tileMoves"], str(len(events)), c["tileMovesNote"]],
            [c["tileConviction"], str(conviction),
             c["tileConvictionNote"].format(n=CONVICTION)],
            [c["tileOpened"],
             f'{sum(1 for e in events if e["k"] == "new")} / '
             f'{sum(1 for e in events if e["k"] == "exit")}',
             c["tileOpenedNote"]],
        ],
        "footnotes": i18n.ACTIVITY_FOOTNOTES[lang],
        "ui": i18n.ACTIVITY[lang],
    }


def main(argv: list[str]) -> int:
    days = int(argv[argv.index("--days") + 1]) if "--days" in argv else DEFAULT_DAYS
    payload = build(days)
    html = TEMPLATE.read_text(encoding="utf-8")
    html = html.replace("/*__STYLES__*/", (HERE / "styles.css").read_text(encoding="utf-8"))
    html = html.replace("/*__DATA__*/", json.dumps(payload, separators=(",", ":")))
    out = DATA / "activity.html"
    out.write_text(html, encoding="utf-8")
    print(f"{out}  ({out.stat().st_size:,} bytes, {len(payload['events'])} moves "
          f"over {payload['days']} sessions)")
    if "--open" in argv:
        webbrowser.open(out.resolve().as_uri())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
