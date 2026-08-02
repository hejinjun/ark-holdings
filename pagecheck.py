"""Run each built page's script and fail if it throws.

  python3 pagecheck.py [site]

Every page here renders itself from a payload inlined at build time, which
means a page can be byte-perfect, parse as valid JSON, serve HTTP 200 and still
show nothing at all: one undefined function and the whole script dies before
the first row is written.

That is not hypothetical. `report_template.html` gained a call to `paintNav()`
when the nav moved into `nav.js`, but `report.py` was still substituting only
`__STYLES__` and `__DATA__`, so `__NAV__` stayed a comment. Holdings and the
trade feed shipped blank through four deploys. Checking the payload could never
have caught it -- the payload was fine. Only running the script catches it.

So the check executes the page's <script> against a DOM stub small enough to be
obviously correct, and asserts two things: nothing was thrown, and something
was written into the page. The stub is deliberately not a browser. It cannot
tell you a column is too narrow or a colour is unreadable; it tells you the
page runs, which is the failure that costs the most and shows the least.

Needs node, which is on the GitHub runners and is not a runtime dependency of
anything else here.
"""

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent

# Enough DOM for a page that paints innerHTML and attaches listeners. Every
# method is a no-op or a plain value; the moment a page needs more than this,
# the check should grow rather than the page be excused from it.
SHIM = r"""
const fs = require('fs');
const html = fs.readFileSync(process.argv[2], 'utf8');
const m = html.match(/<script>([\s\S]*?)<\/script>/);
if (!m) { console.log(JSON.stringify({ok: false, err: 'no <script> in page'})); process.exit(0); }

const ids = [...new Set([...html.matchAll(/id="([\w-]+)"/g)].map(x => x[1]))];
function el(id) {
  return {
    id, _html: '', textContent: '', hidden: false, value: '', placeholder: '',
    dataset: {}, style: {},
    childNodes: [{}],
    classList: {add(){}, remove(){}, toggle(){}, contains(){return false;}},
    set innerHTML(v) { this._html = String(v); },
    get innerHTML() { return this._html; },
    addEventListener(){}, setAttribute(){}, removeAttribute(){},
    getAttribute(){ return null; },
    querySelector(){ return el('?'); }, querySelectorAll(){ return []; },
    closest(){ return el('?'); }, appendChild(){}, insertBefore(){}, remove(){},
  };
}
const store = {};
ids.forEach(i => store[i] = el(i));

global.document = {
  getElementById: id => store[id] || (store[id] = el(id)),
  querySelector: () => el('?'),
  querySelectorAll: () => [],
  createElement: () => el('?'),
  documentElement: {}, body: el('body'),
  addEventListener(){},
};
global.localStorage = {getItem(){ return null; }, setItem(){}};
global.location = {pathname: '/' + process.argv[2].split('/').pop()};
global.CSS = {escape: s => s};
global.requestAnimationFrame = f => f();
global.window = global;

try {
  new Function(m[1])();
  const painted = Object.entries(store)
    .filter(([, e]) => e._html && e._html.length)
    .map(([k, e]) => [k, e._html.length]);
  const total = painted.reduce((a, [, n]) => a + n, 0);
  console.log(JSON.stringify({ok: true, total, painted: painted.sort((a, b) => b[1] - a[1]).slice(0, 5)}));
} catch (e) {
  console.log(JSON.stringify({ok: false, err: `${e.constructor.name}: ${e.message}`}));
}
"""

# A page that runs but paints nothing has failed just as completely as one that
# threw. The bar is low on purpose -- it is a smoke test, not a snapshot.
MIN_PAINTED = 500


def check(paths: list[Path]) -> list[tuple[Path, dict]]:
    node = shutil.which("node")
    if not node:
        raise SystemExit(
            "pagecheck needs node to run the pages. Install it, or build with "
            "--no-page-check and accept that a page that throws will ship blank.")
    out = []
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as fh:
        fh.write(SHIM)
        shim = fh.name
    try:
        for p in paths:
            r = subprocess.run([node, shim, str(p)], capture_output=True, text=True, timeout=120)
            try:
                res = json.loads(r.stdout.strip().splitlines()[-1])
            except (ValueError, IndexError):
                res = {"ok": False, "err": (r.stderr or r.stdout).strip()[:200] or "no output"}
            if res.get("ok") and res.get("total", 0) < MIN_PAINTED:
                res = {"ok": False,
                       "err": f"ran but painted only {res.get('total', 0)} characters"}
            out.append((p, res))
    finally:
        Path(shim).unlink(missing_ok=True)
    return out


def report(results: list[tuple[Path, dict]], root: Path) -> int:
    # Named by path, not by filename: a manager's page is also activity.html,
    # one directory down, and two lines reading "activity.html ok" would say
    # nothing about which one.
    bad = 0
    width = max((len(str(p.relative_to(root))) for p, _ in results), default=18)
    for path, res in results:
        name = str(path.relative_to(root))
        if res["ok"]:
            top = "  ".join(f"{k}:{n:,}" for k, n in res["painted"][:3])
            print(f"  {name:<{width}}  ok    {res['total']:>8,} chars   {top}")
        else:
            bad += 1
            print(f"  {name:<{width}}  FAIL  {res['err']}")
    return bad


# archive.html is plain server-rendered HTML with no script to run. The dated
# copies under reports/ are the same bytes as holdings.html, one per archived
# day, so checking all of them would be 33 runs of one render path -- the copy
# served as holdings.html stands for them.
SKIP = {"archive.html"}
SKIP_DIRS = {"reports"}


def pages_in(root: Path) -> list[Path]:
    """Every page with a script, at any depth. Per-manager pages live in their
    own subdirectory, and a check that only looked at the top level would have
    said nothing about them."""
    return sorted(p for p in root.rglob("*.html")
                  if p.name not in SKIP
                  and not (set(p.relative_to(root).parts[:-1]) & SKIP_DIRS))


def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else HERE / "site"
    pages = pages_in(root)
    if not pages:
        raise SystemExit(f"no pages in {root} -- run build_site.py first")
    bad = report(check(pages), root)
    if bad:
        print(f"\n{bad} page(s) do not render. They will serve HTTP 200 and show nothing.")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
