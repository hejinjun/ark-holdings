"""Assemble the published site from whatever data is committed.

  python3 build_site.py [--out site]

Reports are not stored in the repository -- they are rebuilt here from the CSVs
on every run. That keeps the archive alive without committing 180KB of HTML per
day, and means a template change reflows every historical date at once.

  site/index.html            the latest date
  site/reports/<date>.html   one page per date on file
  site/activity.html         the trade feed across all dates
  site/archive.html          links to all of them
"""

import html
import shutil
import sys
from pathlib import Path

import activity
import report

HERE = Path(__file__).parent
DATA = HERE / "data"


def dates() -> list[str]:
    return sorted(p.name.removeprefix("tradeable_").removesuffix(".csv")
                  for p in DATA.glob("tradeable_*.csv"))


def archive_page(all_dates: list[str]) -> str:
    items = "\n".join(
        f'    <li><a href="reports/{d}.html">{d}</a>'
        f'{" <em>latest</em>" if d == all_dates[-1] else ""}</li>'
        for d in reversed(all_dates))
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ARK holdings — archive</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ font: 15px/1.6 ui-sans-serif, -apple-system, "Segoe UI", Roboto, sans-serif;
         max-width: 40rem; margin: 3rem auto; padding: 0 1.5rem; }}
  h1 {{ font-family: ui-serif, Georgia, serif; font-size: 1.6rem; margin: 0 0 .3rem; }}
  p {{ color: #6b757f; margin: 0 0 2rem; }}
  ul {{ list-style: none; padding: 0; }}
  li {{ padding: .45rem 0; border-bottom: 1px solid #8883; }}
  a {{ font-family: ui-monospace, Menlo, monospace; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  em {{ color: #6b757f; font-size: .8rem; font-style: normal; }}
</style></head>
<body>
  <h1>ARK holdings archive</h1>
  <p>{len(all_dates)} snapshot{"s" if len(all_dates) != 1 else ""} ·
     <a href="index.html">latest</a></p>
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

    shutil.copy(out / "reports" / f"{all_dates[-1]}.html", out / "index.html")

    # The trade feed spans every date at once, so it is built once, not per day.
    try:
        activity.main(["build_site"])
        shutil.copy(DATA / "activity.html", out / "activity.html")
        print("  activity.html")
    except SystemExit as exc:
        print(f"  activity skipped: {exc}")
    (out / "archive.html").write_text(archive_page(all_dates), encoding="utf-8")

    # Pages would otherwise run the output through Jekyll, which drops
    # directories beginning with an underscore and rewrites nothing we want.
    (out / ".nojekyll").write_text("", encoding="utf-8")

    print(f"\n{len(all_dates)} report(s) -> {out}  (latest {all_dates[-1]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
