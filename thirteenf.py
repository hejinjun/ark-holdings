"""Ingest a manager's 13F filings as position snapshots.

  python3 thirteenf.py duquesne          # uses the registry below
  python3 thirteenf.py --cik 1536411 --name duquesne

Writes data/<manager>/positions_<report-date>.csv in exactly the schema the
ARK pipeline produces, so diff.py, tradeable.py, report.py and the rest work
unchanged. Only the ingest differs -- that is the whole point of the seam.

What a 13F is not: it lists long US equity, ADR, ETF and option positions once
a quarter, 45 days after the fact. Shorts, cash, bonds, futures and foreign
lines are absent. For a macro manager that can be most of the book.

Two details that will silently corrupt a series if ignored:

  value units   the `value` column was reported in THOUSANDS of dollars until
                the 2023-Q1 filings, then in whole dollars. A series spanning
                that change is off by a factor of 1000 across the boundary.
  repeated rows one holding appears once per manager or discretion category,
                so rows must be summed by CUSIP before anything else.
"""

import csv
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import cusips

HERE = Path(__file__).parent
DATA = HERE / "data"
UA = "ark-holdings-research hejinjun 62hfdkv7vm@privaterelay.appleid.com"

MANAGERS = {
    "duquesne": {"cik": 1536411, "label": "Duquesne Family Office"},
    "keysquare": {"cik": 1662970, "label": "Key Square Capital Management"},
    "berkshire": {"cik": 1067983, "label": "Berkshire Hathaway"},
}

# The value column changed from thousands of dollars to whole dollars around
# the 2023 filing season, but filers switched at their own pace -- Duquesne
# reported 2022-12-31 in dollars and 2023-03-31 back in thousands. A date rule
# is therefore wrong; the unit is inferred from the numbers instead.
THOUSANDS_PRICE_CEILING = 1.0


def fetch(url: str, out: Path) -> str:
    subprocess.run(["curl", "-sS", "--retry", "4", "--retry-delay", "2",
                    "--retry-all-errors", "--max-time", "45", "-A", UA,
                    url, "-o", str(out)], check=False)
    return out.read_text(encoding="utf-8", errors="replace")


def filings(cik: int, tmp: Path) -> list[dict]:
    raw = fetch(f"https://data.sec.gov/submissions/CIK{cik:010d}.json", tmp / "sub.json")
    rec = json.loads(raw)["filings"]["recent"]
    return [{"form": rec["form"][i], "period": rec["reportDate"][i],
             "filed": rec["filingDate"][i], "acc": rec["accessionNumber"][i]}
            for i in range(len(rec["form"])) if rec["form"][i] == "13F-HR"]


def info_table(cik: int, acc: str, tmp: Path) -> str | None:
    a = acc.replace("-", "")
    idx = fetch(f"https://www.sec.gov/Archives/edgar/data/{cik}/{a}/index.json",
                tmp / "idx.json")
    try:
        items = json.loads(idx)["directory"]["item"]
    except Exception:
        return None
    names = [f["name"] for f in items
             if f["name"].endswith(".xml") and "primary_doc" not in f["name"]]
    if not names:
        return None
    return fetch(f"https://www.sec.gov/Archives/edgar/data/{cik}/{a}/{names[0]}",
                 tmp / "info.xml")


def field(block: str, tag: str) -> str:
    m = re.search(rf"<(?:\w+:)?{tag}>(.*?)</(?:\w+:)?{tag}>", block, re.S)
    return m.group(1).strip() if m else ""


def infer_scale(rows: list[tuple[float, float]]) -> int:
    """Whole dollars or thousands, decided by implied share price.

    value / shares is a share price. Listed equities do not trade below a
    dollar in any quantity that matters, so a median implied price under $1
    means the value column is in thousands.
    """
    prices = sorted(v / s for v, s in rows if s > 0 and v > 0)
    if not prices:
        return 1
    median = prices[len(prices) // 2]
    return 1000 if median < THOUSANDS_PRICE_CEILING else 1


def parse(xml: str, period: str) -> dict[str, dict]:
    """Sum the rows by CUSIP and normalise value to whole dollars."""
    blocks = re.findall(r"<infoTable>(.*?)</infoTable>", xml, re.S)
    raw = [(float(field(b, "value") or 0), float(field(b, "sshPrnamt") or 0))
           for b in blocks if not field(b, "putCall")]
    scale = infer_scale(raw)

    agg: dict[str, dict] = {}
    for block in blocks:
        cusip = field(block, "cusip").strip().upper()
        # An empty filing carries one placeholder row of zeroes.
        if not cusip or set(cusip) == {"0"}:
            continue
        shares = field(block, "sshPrnamt")
        # Option positions are reported in the same table; they are a different
        # instrument and are excluded rather than summed into the share count.
        if field(block, "putCall"):
            continue
        if field(block, "sshPrnamtType") not in ("", "SH"):
            continue
        a = agg.setdefault(cusip, {"company": field(block, "nameOfIssuer"),
                                   "shares": 0.0, "value": 0.0})
        a["shares"] += float(shares or 0)
        a["value"] += float(field(block, "value") or 0) * scale
    return agg


def write(name: str, label: str, period: str, agg: dict, tickers: dict) -> Path:
    out = DATA / name
    out.mkdir(parents=True, exist_ok=True)
    total = sum(a["value"] for a in agg.values())
    path = out / f"positions_{period}.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=[
            "date", "fund", "cusip", "ticker", "company", "asset_class",
            "shares", "market_value", "weight"])
        w.writeheader()
        for cusip, a in sorted(agg.items(), key=lambda kv: -kv[1]["value"]):
            t = tickers.get(cusip, {})
            w.writerow({
                "date": period, "fund": label, "cusip": cusip,
                "ticker": t.get("ticker", ""), "company": a["company"],
                "asset_class": "equity",
                "shares": f"{a['shares']:.0f}",
                "market_value": f"{a['value']:.2f}",
                "weight": f"{100 * a['value'] / total:.4f}" if total else "0",
            })
    return path


def main(argv: list[str]) -> int:
    args = [a for a in argv[1:] if not a.startswith("--")]
    if "--cik" in argv:
        cik = int(argv[argv.index("--cik") + 1])
        name = argv[argv.index("--name") + 1] if "--name" in argv else f"cik{cik}"
        label = name
    elif args and args[0] in MANAGERS:
        name = args[0]
        cik, label = MANAGERS[name]["cik"], MANAGERS[name]["label"]
    else:
        raise SystemExit(f"usage: thirteenf.py <{'|'.join(MANAGERS)}> | --cik N --name X")

    tmp = DATA / "reference" / "tmp13f"
    tmp.mkdir(parents=True, exist_ok=True)

    all_filings = filings(cik, tmp)
    print(f"{label}  CIK {cik}  {len(all_filings)} filings\n")

    periods: dict[str, dict] = {}
    for f in all_filings:
        # A period can be amended; the latest filing of it wins.
        if f["period"] in periods and periods[f["period"]]["filed"] >= f["filed"]:
            continue
        xml = info_table(cik, f["acc"], tmp)
        time.sleep(0.35)
        if not xml:
            print(f"  {f['period']}  no info table")
            continue
        agg = parse(xml, f["period"])
        periods[f["period"]] = {"filed": f["filed"], "agg": agg}
        total = sum(a["value"] for a in agg.values())
        print(f"  {f['period']}  {len(agg):>3} holdings  ${total:>16,.0f}")

    live = {p: v for p, v in periods.items() if v["agg"]}
    if not live:
        raise SystemExit("every filing was empty -- nothing to write")

    pairs = sorted({(c, a["company"])
                    for v in live.values() for c, a in v["agg"].items()})
    print(f"\nresolving {len(pairs)} CUSIPs to tickers")
    tickers = cusips.resolve(pairs)
    hit = sum(1 for c, _ in pairs if tickers.get(c, {}).get("ticker"))
    print(f"  resolved {hit}/{len(pairs)}")

    for period in sorted(live):
        p = write(name, label, period, live[period]["agg"], tickers)
        print(f"  wrote {p.relative_to(HERE)}")
    print(f"\n{len(live)} period(s) -> data/{name}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
