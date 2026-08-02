"""Render the home page: what moved, and whether the data behind it is fresh.

  python3 home.py [--open]

The page is a brief, not a portal. Four links would not need a page of their
own -- what does need one is the pair of questions asked before any analysis:
what ARK did in the last session, and whether every feed actually updated.
Every source overwrites in place at origin, so a stale archive and a quiet
market look identical until something checks. This checks.

Nothing here parses a CSV. Each source module owns a `summary()` that answers
for its own data, and this file only arranges the answers -- so a new source
is a new summary plus a card, and the merging rules stay in one place instead
of drifting into a second implementation here.
"""

import json
import sys
import webbrowser
from datetime import date as _date
from pathlib import Path

import activity
import i18n
import leaders
import report

HERE = Path(__file__).parent
DATA = HERE / "data"
TEMPLATE = HERE / "home_template.html"

# Freshness thresholds, in sessions for the daily feeds and in calendar days
# for the ones that report on their own schedule. `late` is the first value
# that stops reading as current; `stale` is where it stops being usable.
SOURCES = [
    {"key": "holdings", "glob": "tradeable_*.csv", "unit": "sessions", "late": 2, "stale": 4},
    # Trades are derived from a pair of snapshots, so the newest trade date is
    # always one session behind the newest holdings file. That is the shape of
    # the data, not a delay, hence the extra session of tolerance.
    {"key": "trades", "glob": "trades_*.csv", "unit": "sessions", "late": 3, "stale": 5},
    {"key": "quotes", "glob": "quotes_*.csv", "unit": "sessions", "late": 2, "stale": 4},
    {"key": "leaders", "glob": "leaders_*.csv", "unit": "sessions", "late": 2, "stale": 4},
    # Filings arrive quarterly; anything inside a quarter plus the filing
    # window is simply the newest that exists.
    {"key": "financials", "glob": "financials_*.json", "unit": "days", "late": 100, "stale": 200},
    # ARKVX publishes monthly and holds no share counts, so it is archived for
    # completeness rather than consumed.
    {"key": "venture", "glob": "raw/*/ARKVX.csv", "unit": "days", "late": 45, "stale": 90},
]


def _stamp(path: Path) -> str:
    """The date a data file is about, taken from its name.

    Raw fund files carry the date on the directory instead, which is the only
    place the two layouts differ.
    """
    if path.suffix == ".csv" and path.parent.parent.name == "raw":
        return path.parent.name
    return path.stem.split("_")[-1]


def sessions_between(then: str, now: str) -> int:
    """Weekdays after `then`, up to and including `now`.

    Counted in sessions rather than clock time so a Friday file read on Sunday
    is current rather than two days late. Market holidays are not modelled --
    the day after one reads as a session behind, which errs toward looking.
    """
    a, b = _date.fromisoformat(then), _date.fromisoformat(now)
    return sum(1 for i in range(1, (b - a).days + 1)
               if (a.toordinal() + i - 1) % 7 < 5)


def freshness(now: str) -> list[dict]:
    out = []
    for src in SOURCES:
        paths = sorted(DATA.glob(src["glob"]), key=_stamp)
        if not paths:
            out.append({"k": src["key"], "status": "missing"})
            continue
        stamp = _stamp(paths[-1])
        behind = (sessions_between(stamp, now) if src["unit"] == "sessions"
                  else (_date.fromisoformat(now) - _date.fromisoformat(stamp)).days)
        status = ("ok" if behind < src["late"] else
                  "late" if behind < src["stale"] else "stale")
        out.append({"k": src["key"], "date": stamp, "unit": src["unit"],
                    "behind": behind, "status": status, "n": len(paths)})
    return out


def page(lang: str, sources: list[dict], sessions: int) -> dict:
    c = i18n.HOME_PAGE[lang]
    on_file = {s["k"]: s.get("date", "—") for s in sources}
    return {
        "eyebrow": c["eyebrow"],
        "title": c["title"],
        "standfirst": c["standfirst"],
        "provenance": c["provenance"].format(
            holdings=on_file["holdings"], leaders=on_file["leaders"], n=sessions),
        "sources": i18n.SOURCES[lang],
        "next": i18n.HOME_NEXT[lang],
        "footnotes": i18n.HOME_FOOTNOTES[lang],
        "nav": i18n.NAV[lang],
        # The action words are the feed's, borrowed rather than re-translated:
        # the same move must not be "opened" on one page and "started" on the
        # other.
        "ui": {**i18n.HOME[lang],
               **{k: i18n.ACTIVITY[lang][k] for k in ("new", "buy", "sell", "exit")}},
    }


def build() -> dict:
    now = leaders.today()
    sources = freshness(now)
    book = report.summary()
    if not book:
        raise SystemExit("no tradeable_*.csv found -- run the pipeline first")

    return {
        "asOf": book["date"],
        "today": now,
        "langs": [{"v": k, "label": lb} for k, lb in i18n.LANGS],
        "sources": sources,
        "book": book,
        "moves": activity.summary(),
        "leaders": leaders.summary(),
        "i18n": {k: page(k, sources, len(report.tradeable_dates()))
                 for k, _ in i18n.LANGS},
    }


def main(argv: list[str]) -> int:
    payload = build()
    html = TEMPLATE.read_text(encoding="utf-8")
    html = html.replace("/*__STYLES__*/", (HERE / "styles.css").read_text(encoding="utf-8"))
    html = html.replace("/*__DATA__*/", json.dumps(payload, separators=(",", ":")))
    out = DATA / "home.html"
    out.write_text(html, encoding="utf-8")
    late = [s["k"] for s in payload["sources"] if s["status"] != "ok"]
    print(f"{out}  ({out.stat().st_size:,} bytes)  "
          + (f"stale: {', '.join(late)}" if late else "all sources current"))
    if "--open" in argv:
        webbrowser.open(out.resolve().as_uri())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
