"""Render a self-contained HTML view of one day's holdings.

  python3 report.py [YYYY-MM-DD] [--full] [--open]

Default is the tradeable universe -- US-listed equities only, the things that
can actually be bought. `--full` renders the unfiltered baseline instead,
including cash, the private placement, the bitcoin holdcos, and foreign lines.

The template holds no copy of its own: headings, tiles, footnotes and the
secondary dimension all arrive in the payload, so one template serves both
views. Output is a single file with no external requests.
"""

import csv
import json
import sys
import webbrowser
from pathlib import Path

import financials
import fundamentals
import i18n
import links
import segments
import shell
from funds import ETFS
from tradeable import EXCLUDED_FUNDS

HERE = Path(__file__).parent
DATA = HERE / "data"
TEMPLATE = HERE / "report_template.html"

# ARK stays at the data root; an ingested filer lives in its own directory.
# Rebinding one module-level name is enough because every read below goes
# through it -- the seam that let a 13F reuse this pipeline at all.
SOURCE = "ark"


def use_source(name: str) -> None:
    global DATA, SOURCE
    SOURCE = name
    DATA = HERE / "data" if name == "ark" else HERE / "data" / name
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

# Revenue, margin, cash and runway in the detail panel. The figures come from
# SEC XBRL and are quarterly, so they are older than the price on the same row.
SHOW_FINANCIALS = True

CLASS_LABEL = {"equity": "equity", "private": "private",
               "bitcoin_holdco": "bitcoin", "cash": "cash"}


def manager_label() -> str:
    """The filer's own name, taken from thirteenf's registry when it knows it."""
    try:
        import thirteenf
        return thirteenf.MANAGERS.get(SOURCE, {}).get("label", SOURCE)
    except Exception:
        return SOURCE


def fund_tally(date: str, skip: set[str]) -> list[dict]:
    # Fund names come from the file, not from the ARK registry: a 13F filer
    # reports under one name of its own and would otherwise KeyError here.
    tally: dict[str, dict] = {}
    with (DATA / f"positions_{date}.csv").open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["fund"] in skip:
                continue
            t = tally.setdefault(r["fund"], {"n": 0, "v": 0.0})
            t["n"] += 1
            t["v"] += float(r["market_value"])
    return sorted(({"f": f, **t} for f, t in tally.items()), key=lambda x: -x["v"])


def venture_date() -> str:
    dates = sorted(p.parent.name for p in (DATA / "raw").glob("*/ARKVX.csv"))
    return dates[-1] if dates else "n/a"


def tradeable_funds(date: str, keep: set[str]) -> list[dict]:
    """Per-fund position count and market value, counting only `keep` CUSIPs.

    Fund totals must describe the filtered universe, not the whole fund, so
    they are recounted from the positions that survived rather than reused.
    """
    mv: dict[str, float] = {}
    n: dict[str, int] = {}
    with (DATA / f"positions_{date}.csv").open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["fund"] in EXCLUDED_FUNDS or r["cusip"] not in keep:
                continue
            n[r["fund"]] = n.get(r["fund"], 0) + 1
            mv[r["fund"]] = mv.get(r["fund"], 0.0) + float(r["market_value"])
    return sorted(({"f": f, "n": n[f], "v": mv[f]} for f in mv), key=lambda x: -x["v"])


def tradeable_dates() -> list[str]:
    return sorted(p.name.removeprefix("tradeable_").removesuffix(".csv")
                  for p in DATA.glob("tradeable_*.csv"))


def _book(date: str) -> tuple[dict[str, float], set[str]]:
    """symbol -> position value, and the CUSIPs behind them, for one day."""
    value, cusips = {}, set()
    with (DATA / f"tradeable_{date}.csv").open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            value[r["symbol"]] = float(r["total_market_value"])
            cusips.add(r["cusip"])
    return value, cusips


def summary(date: str | None = None) -> dict | None:
    """Headline shape of one day's tradeable book, for the home page.

    Change is measured against the previous snapshot on file rather than a
    fixed lag, so a missed fetch shows up as a longer interval instead of a
    silently absent comparison.
    """
    dates = tradeable_dates()
    if not dates:
        return None
    date = date or dates[-1]
    value, cusips = _book(date)
    funds = tradeable_funds(date, cusips)
    total = sum(f["v"] for f in funds)
    out = {"date": date, "total": total, "n": len(value), "funds": funds,
           "top": [{"t": t, "v": v} for t, v in
                   sorted(value.items(), key=lambda kv: -kv[1])[:5]]}

    earlier = [d for d in dates if d < date]
    if earlier:
        prev_value, prev_cusips = _book(earlier[-1])
        out["prev"] = {
            "date": earlier[-1],
            # Totalled the same way as today's, through the fund split, so the
            # two are comparable rather than two different sums of the book.
            "total": sum(f["v"] for f in tradeable_funds(earlier[-1], prev_cusips)),
            "n": len(prev_value),
            "added": sorted(set(value) - set(prev_value)),
            "removed": sorted(set(prev_value) - set(value)),
        }
    return out


def load_full(date: str) -> dict:
    path = DATA / f"baseline_{date}.csv"
    if not path.exists():
        raise SystemExit(f"missing {path.name} -- run: python3 baseline.py {date}")
    securities = [{
        "c": r["cusip"], "t": r["ticker"], "n": r["company"], "k": r["asset_class"],
        "s": float(r["total_shares"]), "v": float(r["total_market_value"]),
        "f": r["funds"].split("|"), "bf": json.loads(r["by_fund_shares"]),
    } for r in csv.DictReader(path.open(encoding="utf-8"))]
    funds = fund_tally(date, skip=set())
    total = sum(f["v"] for f in funds)
    equity = sum(s["v"] for s in securities if s["k"] == "equity")
    multi = sum(1 for s in securities if len(s["f"]) > 1)
    n = len(securities)

    return {
        "asOf": date,
        "langs": [{"v": "en", "label": "EN"}],
        "i18n": {"en": {
            "eyebrow": "Position baseline",
            "title": "ARK ETF holdings, merged and deduplicated",
            "standfirst": (
                "Every position across the eight ARK exchange-traded funds, collapsed to "
                "one row per security. Shares and market value are summed across funds; "
                "the per-fund split is kept on each row. This is the reference snapshot "
                "future daily diffs are measured against."
            ),
            "provenance": (
                f"as of {date}  ·  8 ETFs  ·  {sum(f['n'] for f in funds)} fund-level "
                f"positions  ·  {n} unique securities  ·  ARKVX (monthly) excluded, "
                f"last {venture_date()}"
            ),
            "tiles": [
                ["Total market value", "$" + f"{total:,.0f}", "sum across the eight ETFs"],
                ["Unique securities", str(n),
                 f"merged from {sum(f['n'] for f in funds)} positions"],
                ["Held by 2+ funds", str(multi), f"{100 * multi / n:.0f}% of securities"],
                ["Non-equity", f"{(total - equity) / total * 100:.2f}%",
                 "private, bitcoin holdco, cash"],
            ],
            "nav": i18n.NAV["en"],
            "footnotes": [
                ["Merge key is CUSIP, not ticker.",
                 "Tickers change and are blank on ARK's non-listed rows; CUSIP is present "
                 f"on all {sum(f['n'] for f in funds)} fund-level positions."],
                ["ARKVX is excluded.",
                 "The venture fund publishes weights only — no share counts or market "
                 "values — so there is nothing to sum into these totals."],
                ["Bitcoin holdcos are not merged across funds.",
                 "ARKK, ARKW and ARKF each hold a separate subsidiary with its own CUSIP "
                 "over the same underlying."],
                ["", "Source: ARK's own daily holdings files on assets.ark-funds.com. "
                     "Holdings data, not investment advice."],
            ],
            "ui": i18n.UI["en"],
        }},
        "dimLabel": "Class",
        "dimLabelZh": "类别",
        "dims": [{"v": k, "label": v, "label_zh": v} for k, v in CLASS_LABEL.items()],
        "segFilters": [],
        "securities": securities,
        "funds": funds,
    }


def load_tradeable(date: str) -> dict:
    path = DATA / f"tradeable_{date}.csv"
    if not path.exists():
        raise SystemExit(f"missing {path.name} -- run: python3 tradeable.py {date}")
    # Quotes are optional: the report still renders before quotes.py has run.
    quotes = {}
    qpath = DATA / f"quotes_{date}.csv"
    if qpath.exists():
        for q in csv.DictReader(qpath.open(encoding="utf-8")):
            if q["range_pct"]:
                quotes[q["symbol"]] = {
                    "p": float(q["price"]), "lo": float(q["week52_low"]),
                    "hi": float(q["week52_high"]), "rp": float(q["range_pct"]),
                    "oh": float(q["off_high_pct"]), "ol": float(q["off_low_pct"]),
                }

    securities = []
    for r in csv.DictReader(path.open(encoding="utf-8")):
        bf = {}
        for part in r["by_fund_shares"].split(";"):
            f, _, s = part.partition("=")
            bf[f] = float(s)
        securities.append({
            "c": r["cusip"], "t": r["symbol"], "n": r["company"], "k": r["exchange"],
            "s": float(r["total_shares"]), "v": float(r["total_market_value"]),
            "f": r["funds"].split("|"), "bf": bf,
            **quotes.get(r["symbol"], {}),
        })

    def _load(name):
        p = DATA / name
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    descriptions = _load("descriptions.json")
    descriptions_zh = _load("descriptions_zh.json")
    fin_data = _load(f"financials_{date}.json")

    try:
        ciks = financials.cik_map()
    except Exception:
        ciks = {}                     # links still work without the SEC entry

    facts = fundamentals.load()
    for s in securities:
        s["lk"] = links.for_symbol(s["t"], financials.cik_for(s["t"], ciks))
        if s["t"] in descriptions:
            s["d"] = descriptions[s["t"]]
        if s["t"] in descriptions_zh:
            s["dz"] = descriptions_zh[s["t"]]
        if SHOW_FINANCIALS and s["t"] in fin_data:
            fin = fin_data[s["t"]]
            s["fin"] = {k: fin[k] for k in (
                "revenue_annual", "revenue_annual_end", "revenue_yoy_pct",
                "gross_margin_pct", "net_income_annual", "cash", "runway_quarters",
                "share_growth_pct", "share_basis_changed", "currency",
            ) if k in fin}
        f = fundamentals.lookup(s["t"], facts) or {}
        s["cap"] = f.get("market_cap") or None
        s["sec"] = f.get("sector") or ""
        s["ind"] = f.get("industry") or ""
        # Values the buckets are cut on. Drawdown is the magnitude of off-high
        # so the buckets read as plain percentages rather than negatives.
        vals = {
            "market_cap": s["cap"],
            "position_value": s["v"],
            "price": s.get("p"),
            "drawdown": abs(s["oh"]) if "oh" in s else None,
            "off_low": s.get("ol"),
            "range_pct": s.get("rp"),
            "amplitude": (100 * (s["hi"] / s["lo"] - 1)) if s.get("lo") else None,
            "n_funds": len(s["f"]),
        }
        s["sg"] = {d["key"]: segments.assign(d, vals[d["field"]]) for d in segments.DIMENSIONS}

    seg_filters = []
    for d in segments.DIMENSIONS:
        used = {s["sg"][d["key"]] for s in securities}
        spec = segments.spec(d, used)
        if len(spec["options"]) > 1:
            seg_filters.append(spec)
    sectors = sorted({s["sec"] for s in securities if s["sec"]})
    if sectors:
        seg_filters.append({
            "key": "sec", "label": "Sector", "label_zh": "板块",
            "options": [{"v": x, "label": x, "label_zh": i18n.SECTORS.get(x, x)}
                        for x in sectors],
        })

    funds = tradeable_funds(date, {s["c"] for s in securities})

    total = sum(f["v"] for f in funds)
    n = len(securities)
    multi = sum(1 for s in securities if len(s["f"]) > 1)
    exchanges = sorted({s["k"] for s in securities},
                       key=lambda e: -sum(s["v"] for s in securities if s["k"] == e))
    nasdaq = sum(s["v"] for s in securities if s["k"] == "NASDAQ")

    excl = "/".join(sorted(EXCLUDED_FUNDS))
    quoted = sum(1 for s in securities if "rp" in s)
    near_low = sum(1 for s in securities if s.get("rp", 100) < 25)

    def page(lang: str) -> dict:
        c = i18n.PAGE[lang]
        tiles = [
            [c["tileValue"], "$" + f"{total:,.0f}", c["tileValueNote"]],
            [c["tileSymbols"], str(n), c["tileSymbolsNote"].format(n=len(funds))],
            [c["tileMulti"], str(multi), c["tileMultiNote"].format(p=f"{100 * multi / n:.0f}")],
        ]
        if quoted:
            tiles.append([c["tileNearLow"], str(near_low),
                          c["tileNearLowNote"].format(n=quoted)])
        else:
            tiles.append(["On Nasdaq", f"{nasdaq / total * 100:.1f}%",
                          f"{sum(1 for s in securities if s['k'] == 'NASDAQ')} of {n}"])
        # A 13F filer's book is not a daily ETF book, and the ARK copy would
        # describe it wrongly on every count -- see i18n.FILER_PAGE.
        f = i18n.FILER_PAGE[lang] if SOURCE != "ark" else None
        return {
            "eyebrow": (f or c)["eyebrow"],
            "title": (f["title"].format(manager=manager_label())
                      if f else c["title"]),
            "standfirst": (f or c)["standfirst"],
            "provenance": (f["provenance"].format(date=date, n=n) if f
                           else c["provenance"].format(date=date, funds=len(funds),
                                                       excl=excl, n=n)),
            "tiles": tiles,
            "nav": i18n.NAV[lang],
            "footnotes": i18n.FOOTNOTES[lang],
            "ui": i18n.UI[lang],
        }

    return {
        "asOf": date,
        "langs": [{"v": k, "label": lb} for k, lb in i18n.LANGS],
        "posBadge": i18n.POSITION_BADGE,
        "sites": links.SITES,
        "i18n": {k: page(k) for k, _ in i18n.LANGS},
        "dimLabel": "Exchange",
        "dimLabelZh": "交易所",
        "dims": [{"v": e, "label": e, "label_zh": e} for e in exchanges],
        "segFilters": seg_filters,
        "securities": securities,
        "funds": funds,
    }


def main(argv: list[str]) -> int:
    if "--source" in argv:
        use_source(argv[argv.index("--source") + 1])
    args = positional(argv[1:])
    full = "--full" in argv
    kind = "baseline" if full else "tradeable"
    dates = sorted(p.name.split("_")[1].removesuffix(".csv")
                   for p in DATA.glob(f"{kind}_*.csv"))
    date = args[0] if args else (dates[-1] if dates else None)
    if not date:
        raise SystemExit(f"no {kind} CSVs found -- run fetch.py, baseline.py, tradeable.py")

    payload = load_full(date) if full else load_tradeable(date)
    out = DATA / f"report_{'full' if full else 'tradeable'}_{date}.html"
    out.write_text(shell.render(TEMPLATE, payload), encoding="utf-8")
    print(f"{out}  ({out.stat().st_size:,} bytes, {len(payload['securities'])} rows)")
    if "--open" in argv:
        webbrowser.open(out.resolve().as_uri())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
