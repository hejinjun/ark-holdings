"""Render one manager's 13F book, with the history behind each position.

  python3 manager.py [duquesne] [--open]

The other pages in this project read a day. This one reads thirteen years,
because that is the only thing a 13F archive can say that a daily holdings
feed cannot: not what is held, but when it was opened, how it was sized, and
how long the conviction lasted.

So the axis is inverted from report.py. There the shape is one date across
many funds; here it is one filer across fifty-two quarters, and every row
carries its own history rather than a single snapshot value.

What a 13F is not, restated because the page would otherwise imply it: long US
equity, ETF and ADR positions only, reported as of a quarter end and filed up
to 45 days later. Shorts, cash, bonds, futures and foreign listings never
appear. For a macro manager that can be most of the book.

Two things on the page are prose rather than filing data, and both are here
because the table alone is unreadable without them: who the filer is
(i18n.MANAGER_ABOUT, keyed by filer) and what each holding's business actually
is (data/descriptions*.json, shared with the ARK pages and keyed by ticker).
A footnote says so, and a holding with no description simply shows none.
"""

import csv
import json
import sys
import webbrowser
from pathlib import Path

import financials
import i18n
import links
import shell
import thirteenf

HERE = Path(__file__).parent
DATA = HERE / "data"
TEMPLATE = HERE / "manager_template.html"

# How far back to look for positions that have been closed. Older exits are
# in the history of the position itself, not news about the book.
EXIT_WINDOW = 8


def load(manager: str, period: str) -> dict[str, dict]:
    with (DATA / manager / f"positions_{period}.csv").open(encoding="utf-8") as fh:
        return {r["cusip"]: r for r in csv.DictReader(fh)}


def _descriptions(name: str) -> dict[str, str]:
    """Ticker -> business description, shared with the ARK pages.

    Written for this site rather than lifted from a filing, and keyed by
    ticker, so a holding whose CUSIP never resolved has none by construction.
    """
    path = DATA / name
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def runs(present: list[bool]) -> int:
    """Where the current unbroken run of quarters held began."""
    i = len(present) - 1
    while i > 0 and present[i - 1]:
        i -= 1
    return i


def build(manager: str) -> dict:
    quarters = thirteenf.periods(manager)
    if not quarters:
        raise SystemExit(f"no positions on file for {manager}")
    books = {q: load(manager, q) for q in quarters}
    now = books[quarters[-1]]

    try:
        ciks = financials.cik_map()
        cik_of = lambda t: financials.cik_for(t, ciks)
    except Exception:
        cik_of = lambda t: None

    desc = _descriptions("descriptions.json")
    desc_zh = _descriptions("descriptions_zh.json")

    total = sum(float(r["market_value"]) for r in now.values())

    holdings = []
    for cusip, r in sorted(now.items(), key=lambda kv: -float(kv[1]["market_value"])):
        # Index into `quarters` rather than repeating the date on every point:
        # fifty-two quarters times sixty-five positions is where this payload
        # would otherwise spend its size.
        history = [[i, round(float(books[q][cusip]["weight"]), 4),
                    float(books[q][cusip]["market_value"]),
                    float(books[q][cusip]["shares"])]
                   for i, q in enumerate(quarters) if cusip in books[q]]
        present = [cusip in books[q] for q in quarters]
        ticker = r["ticker"]
        holdings.append({
            "c": cusip, "t": ticker, "n": r["company"],
            "v": float(r["market_value"]), "w": float(r["weight"]),
            "s": float(r["shares"]),
            "first": quarters[history[0][0]],
            "since": quarters[runs(present)],
            "held": len(history),
            "h": history,
            **({"d": desc[ticker]} if ticker in desc else {}),
            **({"dz": desc_zh[ticker]} if ticker in desc_zh else {}),
            **({"lk": links.for_symbol(ticker, cik_of(ticker))} if ticker else {}),
        })

    # Closed recently: held at some point in the window, gone now. Reported
    # with the size it had when it was last seen, which is what makes an exit
    # worth noticing or not.
    recent = quarters[-EXIT_WINDOW - 1:-1]
    closed = {}
    for q in recent:
        for cusip, r in books[q].items():
            if cusip in now:
                continue
            closed[cusip] = {"t": r["ticker"], "n": r["company"], "last": q,
                             "v": float(r["market_value"]),
                             "w": float(r["weight"])}
    exits = sorted(closed.values(), key=lambda x: (x["last"], x["v"]), reverse=True)

    top10 = sum(h["v"] for h in holdings[:10])
    opened = sum(1 for h in holdings if h["since"] == quarters[-1])
    lasting = [h for h in holdings if h["held"] >= 8]

    # Who filed this, in the reader's language. Unknown filers -- anything
    # ingested with --cik -- simply have no profile, and the section is dropped
    # rather than filled with the directory name.
    profile = i18n.MANAGER_ABOUT.get(manager, {})
    cik = thirteenf.MANAGERS.get(manager, {}).get("cik")

    def about(lang: str) -> dict | None:
        if lang not in profile:
            return None
        p = profile[lang]
        return {**p, "facts": p["facts"] + ([["CIK", str(cik)]] if cik else [])}

    def page(lang: str) -> dict:
        c = i18n.MANAGER_PAGE[lang]
        return {
            "eyebrow": c["eyebrow"],
            "title": c["title"].format(label=now and next(iter(now.values()))["fund"]),
            "standfirst": c["standfirst"],
            "provenance": c["provenance"].format(
                period=quarters[-1], n=len(holdings), q=len(quarters),
                first=quarters[0]),
            "tiles": [
                [c["tileValue"], "$" + f"{total / 1e9:,.2f}B", c["tileValueNote"]],
                [c["tilePositions"], str(len(holdings)),
                 c["tilePositionsNote"].format(n=opened)],
                [c["tileTop10"], f"{top10 / total * 100:.0f}%", c["tileTop10Note"]],
                [c["tileLasting"], str(len(lasting)), c["tileLastingNote"]],
            ],
            "about": about(lang),
            "footnotes": i18n.MANAGER_FOOTNOTES[lang],
            "nav": i18n.NAV[lang],
            "ui": i18n.MANAGER[lang],
        }

    return {
        "asOf": quarters[-1],
        "manager": manager,
        "label": next(iter(now.values()))["fund"],
        "managers": thirteenf.managers(),
        "quarters": quarters,
        "total": total,
        "langs": [{"v": k, "label": lb} for k, lb in i18n.LANGS],
        "sites": links.SITES,
        "i18n": {k: page(k) for k, _ in i18n.LANGS},
        "holdings": holdings,
        "exits": exits[:24],
    }


def main(argv: list[str]) -> int:
    args = [a for a in argv[1:] if not a.startswith("--")]
    have = thirteenf.managers()
    if not have:
        raise SystemExit("no manager ingested -- run: python3 thirteenf.py <name>")
    manager = args[0] if args else have[0]
    payload = build(manager)

    out = DATA / f"manager_{manager}.html"
    out.write_text(shell.render(TEMPLATE, payload), encoding="utf-8")
    print(f"{out}  ({out.stat().st_size:,} bytes, {len(payload['holdings'])} positions "
          f"over {len(payload['quarters'])} quarters)")
    if "--open" in argv:
        webbrowser.open(out.resolve().as_uri())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
