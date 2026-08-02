"""The 200 largest companies on the US market by market cap, archived daily.

Nasdaq's screener overwrites in place and keeps no history, exactly like ARK's
holdings files. Snapshotting the ranking each day is therefore the whole point:
without `data/leaders_<date>.csv` there is no way to say who climbed, who fell
out, or what the entry threshold used to be -- the endpoint only ever knows
today.

Scope is the US market as an investor meets it: every operating company whose
shares trade on a US exchange, wherever it is incorporated. TSMC, ASML, Novo
Nordisk and Toyota are all buyable from a US brokerage account and all belong
in a ranking of what the market actually holds. Where a company is registered
is kept as a filter, not as a gate.
"""

import csv
import json
import re
import sys
import time
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

import fundamentals
import i18n
import links
import segments
import shell

HERE = Path(__file__).parent
DATA = HERE / "data"
TEMPLATE = HERE / "leaders_template.html"

SIZE = 200

# The screener's spelling of the domestic country, used to split the ranking
# into domestic and foreign rather than to exclude anything.
US = "United States"

# Everything the screener returns that is not a share in an operating company.
# Closed-end funds are matched on the word `fund`, which also catches the
# handful of listed trusts that are portfolios rather than businesses.
# `ZONES` are zero-coupon notes exchangeable for stock. Comcast Holdings' line
# is the one that matters: the screener prices it at $234B against Comcast's
# own common at $85B, so leaving it in ranks a debt instrument above the
# company it converts into. It is matched by name because nothing else in the
# row says it is not equity.
#
# Deliberately NOT matched: "Pfd", which appears inside Bank of Nova Scotia's
# name ("Bank Nova Scotia Halifax Pfd 3 Ordinary Shares") where the security is
# in fact the common. Nor "Trust" or "Series A", which Digital Realty Trust and
# Warner Bros. Discovery carry legitimately.
# ZONES is scoped case-sensitive with (?-i:...) so it matches the security type
# in caps and not a company that happens to have "zones" in its name.
NOT_A_COMPANY = re.compile(
    r"warrant|\bunits?\b|\bright[s]?\b|preferred|depositary shares|%\s|"
    r"\bnotes?\b|debenture|\bbond|\bfund\b|(?-i:\bZONES\b)", re.I)

# Where a company has two listed classes, Nasdaq sometimes reports the whole
# company's market cap against BOTH lines -- Alphabet's C shares and A shares
# each carry ~$4.36T. Summing them would count Alphabet twice and put a
# phantom company in the top ten. These are the only two such pairs inside the
# top 200; the mapping is dropped-symbol -> the line that survives. Fox and
# News Corp are the other kind, where each class carries its own cap, so they
# are correctly left alone (both sit well outside the ranking anyway).
#
# `check_unhandled` fails the build if a new pair appears, rather than letting
# the double count through quietly.
DUAL_CLASS = {"GOOGL": "GOOG", "BRK.A": "BRK.B"}

# Two lines whose issuer names agree and whose caps are within this of each
# other are reporting one company twice, not two companies of similar size.
SAME_CAP = 0.01

BOILERPLATE = set(
    "the inc corp corporation co company ltd limited plc sa se ag nv ab asa spa lp "
    "llc group holding holdings class cl common ordinary share shares shs stock "
    "capital adr ads american depositary receipt receipts representing new "
    "sponsored par value series a b c d k of and".split())

# The screener names a security, not a company: "NVIDIA Corporation Common
# Stock". On a leaderboard the security type is noise on all 200 rows, and the
# class designation is actively wrong on the rows where two classes were
# collapsed into one.
# Nasdaq appends a qualifier after the security type on some rows -- "(DE)",
# "(new)", "REIT" -- so that is stripped first and the type second.
SECURITY_SUFFIX = re.compile(
    r"\s*(?:class\s+[a-z]\s+)?"
    r"(?:common|capital|ordinary)?\s*"
    r"(?:stock|shares?)"
    r"(?:\s*\([^)]*\)|\s+REIT)?\s*$", re.I)


def _root(name: str) -> str:
    """The issuer name with the words that do not identify it removed."""
    words = re.sub(r"[^a-z0-9 ]", " ", name.lower()).split()
    return " ".join(w for w in words if w not in BOILERPLATE)


# Nasdaq files a leading article at the end -- "Coca-Cola Company (The)" --
# and tacks a structural note onto some others. Neither belongs on a ranking.
TRAILING_THE = re.compile(r"\s*\(the\)\s*$", re.I)
TRAILING_NOTE = re.compile(r"\s*\((?:new|reit|holding company)\)\s*$", re.I)


def _clean(name: str) -> str:
    trimmed = SECURITY_SUFFIX.sub("", name).strip()
    trimmed = TRAILING_NOTE.sub("", trimmed).strip()
    if TRAILING_THE.search(trimmed):
        trimmed = "The " + TRAILING_THE.sub("", trimmed).strip()
    return trimmed or name.strip()


def _symbol(sym: str) -> str:
    """The screener writes class shares as BRK/B; everything else in this
    project -- the Nasdaq directory, the ARK files, every outbound link --
    writes BRK.B. Normalise once, here, so the cross-reference and the links
    both work."""
    return sym.replace("/", ".")


def _money(text: str) -> float:
    try:
        return float(str(text).replace("$", "").replace(",", "").strip() or 0)
    except ValueError:
        return 0.0


def universe() -> list[dict]:
    """Every operating company trading on a US exchange with a reported market
    cap, largest first, one row per company.

    Country of registration is carried on each row but is not filtered on: a
    ranking of the US market is a ranking of what trades here, and TSMC and
    ASML trade here.
    """
    raw = json.loads(
        (DATA / "reference" / "nasdaq_screener.json").read_text(encoding="utf-8"))
    rows = []
    for r in raw:
        sym = (r.get("symbol") or "").strip()
        name = (r.get("name") or "").strip()
        cap = _money(r.get("marketCap"))
        if not sym or NOT_A_COMPANY.search(name) or cap <= 0:
            continue
        rows.append({
            "symbol": _symbol(sym),
            "company": _clean(name),
            "market_cap": cap,
            "sector": (r.get("sector") or "").strip(),
            "industry": (r.get("industry") or "").strip(),
            "country": (r.get("country") or "").strip(),
            "ipo_year": (r.get("ipoyear") or "").strip(),
            "price": _money(r.get("lastsale")),
            "pct_change": _money(str(r.get("pctchange") or "").replace("%", "")),
        })
    rows.sort(key=lambda r: -r["market_cap"])

    alt = {}
    for r in rows:
        if r["symbol"] in DUAL_CLASS:
            alt.setdefault(DUAL_CLASS[r["symbol"]], []).append(r["symbol"])
    kept = [r for r in rows if r["symbol"] not in DUAL_CLASS]
    for r in kept:
        r["alt_symbols"] = " ".join(alt.get(r["symbol"], ()))
    check_unhandled(kept)
    return kept


def check_unhandled(rows: list[dict]) -> None:
    """Fail loudly if a second share class slipped into the ranking.

    A silent double count is the one error this page cannot survive: it would
    invent a company, shift every rank below it by one, and inflate the totals,
    all while looking perfectly plausible. Better to stop and add the pair to
    DUAL_CLASS after checking which kind it is.
    """
    seen: dict[str, dict] = {}
    for r in rows[:SIZE + 50]:          # a buffer, so a pair is caught before it lands
        key = _root(r["company"])
        prev = seen.get(key)
        if prev and abs(prev["market_cap"] - r["market_cap"]) <= SAME_CAP * prev["market_cap"]:
            raise SystemExit(
                f"unhandled dual-class pair: {prev['symbol']} and {r['symbol']} both "
                f"report ${r['market_cap']:,.0f} for '{key}'. Add the secondary line "
                f"to DUAL_CLASS in leaders.py once you have checked which class is "
                f"which -- leaving it in would count the company twice.")
        seen[key] = r


# ---- daily snapshot ----

COLUMNS = ["rank", "symbol", "company", "market_cap", "sector", "industry",
           "country", "ipo_year", "price", "pct_change", "alt_symbols"]

# The 200 are stated as a share of the whole US universe, which is a fact about
# the day they were captured. Recomputing it at render time would silently
# measure an archived ranking against today's market, so it is written down
# with the snapshot instead.
META = DATA / "leaders_meta.json"


def write_snapshot(date: str, rows: list[dict]) -> Path:
    path = DATA / f"leaders_{date}.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        for i, r in enumerate(rows[:SIZE], 1):
            w.writerow({"rank": i, **{k: r.get(k, "") for k in COLUMNS[1:]}})

    meta = json.loads(META.read_text(encoding="utf-8")) if META.exists() else {}
    meta[date] = {"companies": len(rows),
                  "market_cap": sum(r["market_cap"] for r in rows)}
    META.write_text(json.dumps(meta, indent=1, sort_keys=True), encoding="utf-8")
    return path


# ---- 52-week range ----

# The ranking's equivalent of the ARK mark cross-check in quotes.py: Yahoo's
# price and Nasdaq's last sale describe the same security, so a wide gap means
# the symbol resolved to the wrong company, not that the stock moved.
QUOTE_TOLERANCE = 0.25

QUOTE_COLUMNS = ["symbol", "price", "week52_low", "week52_high", "range_pct",
                 "off_high_pct", "off_low_pct", "screener_price", "drift_pct", "status"]


def write_quotes(date: str) -> Path:
    """Fetch the 52-week range for the ranking and archive it beside it.

    Kept in its own file, exactly like quotes.py is kept apart from
    tradeable.py: the ranking must still be captured on a day Yahoo is down,
    and the page renders without this.
    """
    import quotes

    rows = read_snapshot(date)
    out_rows, failed, suspect = [], [], []
    for i, r in enumerate(rows, 1):
        sym = r["symbol"]
        q = quotes.fetch(sym)
        time.sleep(quotes.DELAY)
        if q["status"] in ("net_error", "not_found", "incomplete"):
            failed.append((sym, q["status"], q.get("detail", "")))
            print(f"  [{i:>3}/{len(rows)}] {sym:<8} {q['status']}")
            continue

        ref = r["price"]
        drift = abs(q["price"] - ref) / ref if ref else 0.0
        if drift > QUOTE_TOLERANCE:
            suspect.append((sym, r["company"], ref, q["price"], drift))

        span = q["high"] - q["low"]
        out_rows.append({
            "symbol": sym,
            "price": f"{q['price']:.4f}",
            "week52_low": f"{q['low']:.4f}",
            "week52_high": f"{q['high']:.4f}",
            "range_pct": f"{100 * (q['price'] - q['low']) / span:.2f}" if span else "",
            "off_high_pct": f"{100 * (q['price'] / q['high'] - 1):.2f}" if q["high"] else "",
            "off_low_pct": f"{100 * (q['price'] / q['low'] - 1):.2f}" if q["low"] else "",
            "screener_price": f"{ref:.4f}",
            "drift_pct": f"{100 * (q['price'] / ref - 1):.2f}" if ref else "",
            "status": q["status"],
        })
        print(f"  [{i:>3}/{len(rows)}] {sym:<8} {q['price']:>10,.2f}  "
              f"52w {q['low']:>9,.2f} – {q['high']:>9,.2f}")

    path = DATA / f"leaders_quotes_{date}.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=QUOTE_COLUMNS)
        w.writeheader()
        w.writerows(out_rows)

    print(f"\nquoted {len(out_rows)} of {len(rows)} -> {path.name}")
    if failed:
        print(f"failed ({len(failed)}): " + ", ".join(s for s, _, _ in failed))
    if suspect:
        print(f"\nYahoo disagrees with the screener by >{QUOTE_TOLERANCE:.0%} "
              f"-- check the symbol mapping ({len(suspect)}):")
        for s, name, ref, px, dr in sorted(suspect, key=lambda x: -x[4]):
            print(f"  {s:<8}{name[:30]:<32}Nasdaq {ref:>9,.2f}   Yahoo {px:>9,.2f}"
                  f"   {dr:>7.0%}")
    return path


def read_quotes(date: str) -> dict[str, dict]:
    """symbol -> 52-week figures, or empty when the day was not quoted."""
    path = DATA / f"leaders_quotes_{date}.csv"
    if not path.exists():
        return {}
    out = {}
    for r in csv.DictReader(path.open(encoding="utf-8")):
        if not r["range_pct"]:
            continue
        out[r["symbol"]] = {
            "p": float(r["price"]), "lo": float(r["week52_low"]),
            "hi": float(r["week52_high"]), "rp": float(r["range_pct"]),
            "oh": float(r["off_high_pct"]), "ol": float(r["off_low_pct"]),
        }
    return out


def read_meta(date: str) -> dict:
    meta = json.loads(META.read_text(encoding="utf-8")) if META.exists() else {}
    if date in meta:
        return meta[date]
    # A snapshot taken before the meta file existed: fall back to today's
    # universe and accept that the share is approximate for that one date.
    rows = universe()
    return {"companies": len(rows), "market_cap": sum(r["market_cap"] for r in rows)}


def today() -> str:
    """The date a snapshot taken now belongs to.

    Every date in this project names a UTC day, so a run from any timezone
    files against the same snapshot as the scheduled job.
    """
    return datetime.now(timezone.utc).date().isoformat()


# Only a date-stamped file is a snapshot. `leaders_quotes_<date>.csv` sits in
# the same directory under the same prefix, and a plain glob would offer it as
# a ranking to read.
SNAPSHOT = re.compile(r"^leaders_(\d{4}-\d{2}-\d{2})\.csv$")


def snapshots() -> list[str]:
    return sorted(m.group(1) for p in DATA.glob("leaders_*.csv")
                  if (m := SNAPSHOT.match(p.name)))


def read_snapshot(date: str) -> list[dict]:
    path = DATA / f"leaders_{date}.csv"
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    for r in rows:
        r["rank"] = int(r["rank"])
        r["market_cap"] = float(r["market_cap"])
        r["price"] = float(r["price"] or 0)
        r["pct_change"] = float(r["pct_change"] or 0)
    return rows


# ---- ARK cross-reference ----

def ark_positions(date: str) -> dict[str, float]:
    """symbol -> ARK's position value, from the newest tradeable file at or
    before `date`. The two feeds are on separate cadences, so the holdings are
    matched to the closest snapshot rather than required to be same-day."""
    dates = sorted(p.name.removeprefix("tradeable_").removesuffix(".csv")
                   for p in DATA.glob("tradeable_*.csv"))
    usable = [d for d in dates if d <= date] or dates
    if not usable:
        return {}
    path = DATA / f"tradeable_{usable[-1]}.csv"
    out = {}
    for r in csv.DictReader(path.open(encoding="utf-8")):
        out[r["symbol"]] = float(r["total_market_value"])
    return out


# ---- payload ----

MOVE = {"up": "up", "down": "down", "flat": "flat", "in": "in"}


def summary(limit: int = 5) -> dict | None:
    """What changed at the top of the market since the previous snapshot.

    With one snapshot on file there is no movement to report -- the ranking
    itself is returned and the caller says so, rather than reporting 200
    companies as new entries.
    """
    have = snapshots()
    if not have:
        return None
    date = have[-1]
    rows = read_snapshot(date)
    prev_date = have[-2] if len(have) > 1 else None
    prev = {r["symbol"]: r["rank"] for r in read_snapshot(prev_date)} if prev_date else {}
    ark = ark_positions(date)

    def entry(r, **extra):
        return {"t": r["symbol"], "n": r["company"], "r": r["rank"],
                "cap": r["market_cap"], "ch": r["pct_change"],
                **({"ark": ark[r["symbol"]]} if r["symbol"] in ark else {}), **extra}

    moved = [entry(r, d=prev[r["symbol"]] - r["rank"])
             for r in rows if r["symbol"] in prev and prev[r["symbol"]] != r["rank"]]
    moved.sort(key=lambda x: -abs(x["d"]))
    now = {r["symbol"] for r in rows}

    return {
        "date": date,
        "prevDate": prev_date,
        "size": SIZE,
        "cutoff": rows[-1]["market_cap"],
        "top": [entry(r) for r in rows[:limit]],
        "moved": moved[:limit],
        "in": [entry(r) for r in rows if prev and r["symbol"] not in prev],
        "out": [{"t": p["symbol"], "n": p["company"], "r": p["rank"]}
                for p in (read_snapshot(prev_date) if prev_date else [])
                if p["symbol"] not in now],
        "held": sum(1 for r in rows if r["symbol"] in ark),
    }


def build(date: str, prev_date: str | None) -> dict:
    rows = read_snapshot(date)
    prev = {r["symbol"]: r["rank"] for r in read_snapshot(prev_date)} if prev_date else {}
    ark = ark_positions(date)
    # Optional, like quotes are on the holdings page: the ranking renders on a
    # day Yahoo refused, just without the 52-week columns.
    quoted = read_quotes(date)

    def _load(name):
        p = DATA / name
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    descriptions, descriptions_zh = _load("descriptions.json"), _load("descriptions_zh.json")
    try:
        import financials
        ciks = financials.cik_map()
        cik_of = lambda s: financials.cik_for(s, ciks)
    except Exception:
        cik_of = lambda s: None

    total = sum(r["market_cap"] for r in rows)
    companies = []
    for r in rows:
        sym = r["symbol"]
        was = prev.get(sym)
        # No previous file at all is "unknown", not "new to the list" -- the
        # first day of the archive must not report 200 new entries.
        move = "flat" if not prev else ("in" if was is None else
                                        "up" if was > r["rank"] else
                                        "down" if was < r["rank"] else "flat")
        c = {
            "r": r["rank"], "t": sym, "n": r["company"], "cap": r["market_cap"],
            "w": r["market_cap"] / total * 100,
            "sec": r["sector"], "ind": r["industry"],
            "p": r["price"], "ch": r["pct_change"],
            "iy": r["ipo_year"], "mv": move, "cty": r["country"],
            "lk": links.for_symbol(sym, cik_of(sym)),
            # Yahoo's price wins where it exists: it is newer than the
            # screener's last sale and is what the 52-week range is measured
            # against, so taking one from each would put the marker in the
            # wrong place on the bar.
            **quoted.get(sym, {}),
        }
        if was is not None:
            c["pr"] = was
        if r["alt_symbols"]:
            c["alt"] = r["alt_symbols"]
        if sym in ark:
            c["ark"] = ark[sym]
        if sym in descriptions:
            c["d"] = descriptions[sym]
        if sym in descriptions_zh:
            c["dz"] = descriptions_zh[sym]
        # Drawdown is the magnitude of off-high, so the buckets read as plain
        # percentages rather than negatives -- same convention as report.py.
        vals = {"rank": r["rank"], "market_cap": r["market_cap"],
                "ipo_decade": float(r["ipo_year"]) if r["ipo_year"] else None,
                "drawdown": abs(c["oh"]) if "oh" in c else None,
                "range_pct": c.get("rp")}
        c["sg"] = {d["key"]: segments.assign(d, vals[d["field"]])
                   for d in segments.LEADER_DIMENSIONS}
        companies.append(c)

    seg_filters = []
    for d in segments.LEADER_DIMENSIONS:
        used = {c["sg"][d["key"]] for c in companies}
        spec = segments.spec(d, used)
        if len(spec["options"]) > 1:
            seg_filters.append(spec)
    sectors = sorted({c["sec"] for c in companies if c["sec"]},
                     key=lambda s: -sum(c["cap"] for c in companies if c["sec"] == s))
    seg_filters.append({
        "key": "sec", "label": "Sector", "label_zh": "板块",
        "options": [{"v": s, "label": s, "label_zh": i18n.SECTORS.get(s, s)} for s in sectors],
    })
    # Registration is a dimension, not a gate. Two chips rather than one per
    # country: with 44 foreign issuers spread over a dozen countries, a chip
    # each would be a row of ones. The country itself is on the row.
    if any(c["cty"] and c["cty"] != US for c in companies):
        seg_filters.append({
            "key": "cty", "label": "Domicile", "label_zh": "注册地",
            "options": [{"v": "us", "label": "US", "label_zh": "美国"},
                        {"v": "intl", "label": "Foreign", "label_zh": "外国"}],
        })
    seg_filters.append({
        "key": "ark", "label": "ARK", "label_zh": "ARK",
        "options": [{"v": "y", "label": "Held by ARK", "label_zh": "ARK 持有"},
                    {"v": "n", "label": "Not held", "label_zh": "未持有"}],
    })
    if prev:
        seg_filters.append({
            "key": "mv", "label": "Rank move", "label_zh": "排名变化",
            "options": [{"v": "up", "label": "Climbed", "label_zh": "上升"},
                        {"v": "down", "label": "Slipped", "label_zh": "下降"},
                        {"v": "flat", "label": "Unchanged", "label_zh": "持平"},
                        {"v": "in", "label": "New entry", "label_zh": "新进榜"}],
        })

    # Market share is stated against the whole listed universe, not against the
    # 200 -- "the top 200 are 100% of the top 200" says nothing.
    meta = read_meta(date)
    market, n_universe = meta["market_cap"], meta["companies"]

    gone = []
    if prev_date:
        now = {r["symbol"] for r in rows}
        gone = [{"t": p["symbol"], "n": p["company"], "r": p["rank"]}
                for p in read_snapshot(prev_date) if p["symbol"] not in now]

    return {
        "asOf": date,
        "prevDate": prev_date,
        "size": SIZE,
        "langs": [{"v": k, "label": lb} for k, lb in i18n.LANGS],
        "sites": links.SITES,
        "i18n": {k: page(k, date, prev_date, companies, total, market,
                         n_universe, ark, gone) for k, _ in i18n.LANGS},
        "segFilters": seg_filters,
        "companies": companies,
        "dropped": gone,
        "total": total,
        "market": market,
    }


def page(lang, date, prev_date, companies, total, market, n_universe, ark, gone) -> dict:
    c = i18n.LEADERS_PAGE[lang]
    held = sum(1 for x in companies if "ark" in x)
    cutoff = companies[-1]["cap"]
    top10 = sum(x["cap"] for x in companies[:10])
    entered = sum(1 for x in companies if x["mv"] == "in")
    tiles = [
        [c["tileCap"], f"${total / 1e12:,.1f}T",
         c["tileCapNote"].format(p=f"{total / market * 100:.0f}", n=f"{n_universe:,}")],
        [c["tileCutoff"], f"${cutoff / 1e9:,.0f}B",
         c["tileCutoffNote"].format(t=companies[-1]["t"])],
        [c["tileTop10"], f"{top10 / total * 100:.0f}%", c["tileTop10Note"]],
    ]
    if prev_date:
        tiles.append([c["tileTurnover"], f"{entered} / {len(gone)}",
                      c["tileTurnoverNote"].format(d=prev_date)])
    else:
        tiles.append([c["tileArk"], str(held), c["tileArkNote"]])
    return {
        "eyebrow": c["eyebrow"],
        "title": c["title"],
        "standfirst": c["standfirst"],
        "provenance": c["provenance"].format(date=date, n=len(companies),
                                             u=f"{n_universe:,}", held=held),
        "tiles": tiles,
        "nav": i18n.NAV[lang],
        "footnotes": i18n.LEADERS_FOOTNOTES[lang],
        "ui": i18n.LEADERS[lang],
    }


def main(argv: list[str]) -> int:
    args = [a for a in argv[1:] if not a.startswith("--")]

    if "--refresh" in argv:
        fundamentals.refresh()

    date = args[0] if args else None
    if date is None:
        # A run with no arguments snapshots today from the cached screener.
        # UTC, not local time: the scheduled job runs on a UTC runner and a
        # local run must land on the same filename, or the two would write
        # neighbouring snapshots and invent a day of rank movement between them.
        date = today()
        rows = universe()
        path = write_snapshot(date, rows)
        print(f"{path.name}  ({len(rows[:SIZE])} companies, "
              f"cutoff ${rows[SIZE - 1]['market_cap'] / 1e9:,.0f}B)")

    have = snapshots()
    if date not in have:
        raise SystemExit(f"no leaders_{date}.csv -- run: python3 leaders.py --refresh")
    earlier = [d for d in have if d < date]
    payload = build(date, earlier[-1] if earlier else None)

    out = DATA / f"leaders_{date}.html"
    out.write_text(shell.render(TEMPLATE, payload), encoding="utf-8")
    print(f"{out}  ({out.stat().st_size:,} bytes, {len(payload['companies'])} rows"
          + (f", vs {payload['prevDate']}" if payload["prevDate"] else ", no prior snapshot")
          + ")")
    if "--open" in argv:
        webbrowser.open(out.resolve().as_uri())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
