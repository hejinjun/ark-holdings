"""Assemble the published site from whatever data is committed.

  python3 build_site.py [--out site]

Reports are not stored in the repository -- they are rebuilt here from the CSVs
on every run. That keeps the archive alive without committing 180KB of HTML per
day, and means a template change reflows every historical date at once.

  site/index.html            the daily brief: what moved, and is the data fresh
  site/holdings.html         the latest date
  site/reports/<date>.html   one page per date on file
  site/activity.html         the trade feed across all dates
  site/leaders.html          the market cap leaderboard, latest snapshot
  site/archive.html          links to all of them
"""

import shutil
import sys
from pathlib import Path

import activity
import home
import i18n
import leaders
import report

HERE = Path(__file__).parent
DATA = HERE / "data"


def dates() -> list[str]:
    return sorted(p.name.removeprefix("tradeable_").removesuffix(".csv")
                  for p in DATA.glob("tradeable_*.csv"))


def archive_page(all_dates: list[str]) -> str:
    """The one page with no data of its own, so it is written here rather than
    given a module. Nav labels come from i18n so it cannot drift from the
    others; the rest is English, being a list of dates."""
    nav = "\n".join(
        f'    <a href="{k}.html"{" aria-current=\'page\'" if k == "archive" else ""}>'
        f'{i18n.NAV["en"][k]}</a>'
        for k in ("index", "holdings", "activity", "leaders", "archive"))
    items = "\n".join(
        f'    <li><a href="reports/{d}.html">{d}</a>'
        f'{" <em>latest</em>" if d == all_dates[-1] else ""}</li>'
        for d in reversed(all_dates))
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ARK holdings — archive</title>
<style>
  :root {{ color-scheme: light dark; --ink-3: #8b959f; --rule: #8883; --accent: #2a78d6; }}
  body {{ font: 15px/1.6 ui-sans-serif, -apple-system, "Segoe UI", Roboto, sans-serif;
         max-width: 40rem; margin: 0 auto; padding: 2.5rem 1.25rem 4rem; }}
  h1 {{ font-family: ui-serif, Georgia, serif; font-size: 1.6rem; margin: 0 0 .3rem; }}
  p {{ color: var(--ink-3); margin: 0 0 2rem; }}
  nav {{ display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 1.75rem; }}
  nav a {{ font-family: ui-monospace, Menlo, monospace; font-size: 12px;
          padding: 5px 11px; border: 1px solid var(--rule); border-radius: 3px;
          text-decoration: none; color: inherit; white-space: nowrap; }}
  nav a[aria-current] {{ border-color: var(--accent); color: var(--accent); font-weight: 600; }}
  ul {{ list-style: none; padding: 0; }}
  li {{ padding: .45rem 0; border-bottom: 1px solid var(--rule); }}
  li a {{ font-family: ui-monospace, Menlo, monospace; text-decoration: none; }}
  li a:hover {{ text-decoration: underline; }}
  em {{ color: var(--ink-3); font-size: .8rem; font-style: normal; }}
</style></head>
<body>
  <nav>
{nav}
  </nav>
  <h1>ARK holdings archive</h1>
  <p>{len(all_dates)} snapshot{"s" if len(all_dates) != 1 else ""}, rebuilt from the
     committed CSVs on every deploy.</p>
  <ul>
{items}
  </ul>
</body></html>
"""


def main(argv: list[str]) -> int:
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else HERE / "site"
    all_dates = dates()
    if not all_dates:
        raise SystemExit("no tradeable_*.csv found -- run the pipeline first")

    if out.exists():
        shutil.rmtree(out)
    (out / "reports").mkdir(parents=True)

    for d in all_dates:
        report.main(["build_site", d])
        src = DATA / f"report_tradeable_{d}.html"
        shutil.copy(src, out / "reports" / f"{d}.html")
        print(f"  {d}  {src.stat().st_size:>9,} bytes")

    # The newest report is the same bytes as its dated copy: one render, served
    # at two paths, which is why the nav resolves its own depth at runtime.
    shutil.copy(out / "reports" / f"{all_dates[-1]}.html", out / "holdings.html")

    # The trade feed spans every date at once, so it is built once, not per day.
    try:
        activity.main(["build_site"])
        shutil.copy(DATA / "activity.html", out / "activity.html")
        print("  activity.html")
    except SystemExit as exc:
        print(f"  activity skipped: {exc}")

    # The leaderboard tracks the market, not ARK, so it follows its own archive
    # of snapshots rather than the holdings dates.
    board = leaders.snapshots()
    if board:
        leaders.main(["build_site", board[-1]])
        shutil.copy(DATA / f"leaders_{board[-1]}.html", out / "leaders.html")
        print(f"  leaders.html  ({board[-1]})")
    else:
        print("  leaders skipped: no leaders_*.csv snapshot yet")

    (out / "archive.html").write_text(archive_page(all_dates), encoding="utf-8")

    # Last, because it reports on everything above it.
    home.main(["build_site"])
    shutil.copy(DATA / "home.html", out / "index.html")
    print("  index.html  (daily brief)")

    # Pages would otherwise run the output through Jekyll, which drops
    # directories beginning with an underscore and rewrites nothing we want.
    (out / ".nojekyll").write_text("", encoding="utf-8")

    print(f"\n{len(all_dates)} report(s) -> {out}  (latest {all_dates[-1]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
