"""Assemble a page: its template, the shared stylesheet, the shared nav, its data.

Every page in this project is one self-contained file with no external
requests, which means anything shared between pages has to be inlined into
each of them at build time. Doing that in one place is the difference between
adding a page to the nav and remembering to add it four times.

Markers a template may carry:

  /*__STYLES__*/   the stylesheet, required
  /*__NAV__*/      the nav painter; the template supplies `HERE` and a #sitenav
  /*__DATA__*/     the payload, required
"""

import json
from pathlib import Path

HERE = Path(__file__).parent
SHARED = {"/*__STYLES__*/": HERE / "styles.css", "/*__NAV__*/": HERE / "nav.js"}
DATA_MARKER = "/*__DATA__*/"


def render(template: Path, payload: dict) -> str:
    html = template.read_text(encoding="utf-8")
    if DATA_MARKER not in html:
        raise SystemExit(f"{template.name} has no {DATA_MARKER} marker")
    for marker, path in SHARED.items():
        if marker in html:
            html = html.replace(marker, path.read_text(encoding="utf-8"))
    # Data last: it is the one substitution whose text may itself contain a
    # marker-shaped string, and it must not be scanned for one.
    return html.replace(DATA_MARKER, json.dumps(payload, separators=(",", ":")))
