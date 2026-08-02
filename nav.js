/* The shared site nav, inlined into every page by shell.py.

   Labels come from page().nav so they follow the language switch, and each
   template declares its own `HERE` so the current page can be marked rather
   than dropped -- a missing entry reads as a broken link, not as "you are
   here".

   The newest report is served both as holdings.html and as its dated copy
   under reports/, from the same bytes, so the depth cannot be baked into the
   href; it is read off the path instead. */

const NAV_BASE = location.pathname.includes('/reports/') ? '../' : '';
const NAV_PAGES = ['index', 'holdings', 'activity', 'leaders', 'archive'];

function paintNav() {
  const el = document.getElementById('sitenav');
  if (!el) return;
  const labels = page().nav || {};
  el.innerHTML = NAV_PAGES.map(k =>
    `<a href="${NAV_BASE}${k}.html"${k === HERE ? ' aria-current="page"' : ''}>` +
    `${labels[k] || k}</a>`).join('');
}
