"""Ingest a manager's 13F filings as position snapshots.

  python3 thirteenf.py duquesne          # only what is not already on disk
  python3 thirteenf.py duquesne --refetch  # every period again
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

import issuers

HERE = Path(__file__).parent
DATA = HERE / "data"
UA = "ark-holdings-research hejinjun 62hfdkv7vm@privaterelay.appleid.com"

MANAGERS = {
    "duquesne": {"cik": 1536411, "label": "Duquesne Family Office", "short": "Duquesne"},
    "keysquare": {"cik": 1662970, "label": "Key Square Capital Management", "short": "Key Square"},
    "berkshire": {"cik": 1067983, "label": "Berkshire Hathaway", "short": "Berkshire"},
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


def managers() -> list[str]:
    """Directories holding an ingested filer, newest period first inside each."""
    return sorted(p.name for p in DATA.iterdir()
                  if p.is_dir() and any(p.glob("positions_*.csv")))


def periods(manager: str) -> list[str]:
    return sorted(p.name.removeprefix("positions_").removesuffix(".csv")
                  for p in (DATA / manager).glob("positions_*.csv"))


def summary(manager: str | None = None, limit: int = 5) -> dict | None:
    """The newest filed book for one manager, for the home page.

    Reported as of a quarter end and filed up to 45 days after it, so this is
    the one card on that page describing something that already happened
    rather than something that just did. The lag is stated with it.
    """
    have = managers()
    if not have:
        return None
    manager = manager or have[0]
    quarters = periods(manager)
    if not quarters:
        return None

    def book(period: str) -> list[dict]:
        with (DATA / manager / f"positions_{period}.csv").open(encoding="utf-8") as fh:
            return list(csv.DictReader(fh))

    rows = book(quarters[-1])
    total = sum(float(r["market_value"]) for r in rows)
    out = {
        "manager": manager,
        "label": rows[0]["fund"] if rows else manager,
        "period": quarters[-1],
        "quarters": len(quarters),
        "n": len(rows),
        "total": total,
        "unidentified": sum(1 for r in rows if not r["ticker"]),
        "top": [{"t": r["ticker"], "n": r["company"], "v": float(r["market_value"]),
                 "w": float(r["weight"])} for r in rows[:limit]],
    }
    if len(quarters) > 1:
        prev = {r["cusip"] for r in book(quarters[-2])}
        now = {r["cusip"] for r in rows}
        out["prevPeriod"] = quarters[-2]
        out["opened"] = len(now - prev)
        out["closed"] = len(prev - now)
    return out


def weights(manager: str, period: str | None = None) -> dict[str, dict]:
    """ticker -> weight, value and company across one manager's whole book.

    summary()'s `top` is capped at `limit`, five by default; a page that wants
    to answer "does ARK also hold this" for every row, not just the largest
    five, needs the full book instead.
    """
    quarters = periods(manager)
    if not quarters:
        return {}
    period = period or quarters[-1]
    path = DATA / manager / f"positions_{period}.csv"
    with path.open(encoding="utf-8") as fh:
        return {r["ticker"]: {"v": float(r["market_value"]), "w": float(r["weight"]),
                              "n": r["company"]}
                for r in csv.DictReader(fh) if r["ticker"]}


def ledger(name: str, known: list[dict]) -> dict[str, str]:
    """period -> filing date already ingested, so an amendment is detectable.

    On the first run there is no ledger but there may be data, written before
    this bookkeeping existed. Seeding it from the filing dates EDGAR reports
    for the periods already on disk costs no downloads and treats them as
    current -- an empty stamp would instead compare as older than every filing
    and refetch all fifty-two.
    """
    path = DATA / name / "filings.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    latest: dict[str, str] = {}
    for f in known:
        if f["filed"] > latest.get(f["period"], ""):
            latest[f["period"]] = f["filed"]
    return {p: latest.get(p, "") for p in periods_on_disk(name)}


def periods_on_disk(name: str) -> list[str]:
    d = DATA / name
    if not d.is_dir():
        return []
    return sorted(p.name.removeprefix("positions_").removesuffix(".csv")
                  for p in d.glob("positions_*.csv"))


def save_ledger(name: str, stamps: dict[str, str]) -> None:
    (DATA / name / "filings.json").write_text(
        json.dumps(stamps, indent=1, sort_keys=True), encoding="utf-8")


def main(argv: list[str]) -> int:
    refetch = "--refetch" in argv
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

    # Only fetch what is missing. A period already written stays written unless
    # the filer amended it, which shows up as a later filing date for the same
    # period. Without this the ingest pulls fifty-two info tables on every run,
    # which is fine once by hand and not fine on a schedule.
    stamps = ledger(name, all_filings)
    fresh = [f for f in all_filings
             if refetch or stamps.get(f["period"], "") < f["filed"]]
    print(f"{label}  CIK {cik}  {len(all_filings)} filings, "
          f"{len(fresh)} to fetch\n")
    if not fresh:
        print("nothing new")
        return 0

    periods: dict[str, dict] = {}
    for f in fresh:
        # A period can be amended; the latest filing of it wins.
        if f["period"] in periods and periods[f["period"]]["filed"] >= f["filed"]:
            continue
        xml = info_table(cik, f["acc"], tmp)
        time.sleep(0.35)
        if not xml:
            # Filings before roughly 2013 predate the XML information table.
            # Stamping the attempt keeps the ingest from retrying them on
            # every run for as long as the filer exists.
            stamps[f["period"]] = f["filed"]
            print(f"  {f['period']}  no info table (pre-XML filing)")
            continue
        agg = parse(xml, f["period"])
        periods[f["period"]] = {"filed": f["filed"], "agg": agg}
        total = sum(a["value"] for a in agg.values())
        print(f"  {f['period']}  {len(agg):>3} holdings  ${total:>16,.0f}")

    live = {p: v for p, v in periods.items() if v["agg"]}
    if not live:
        # Empty filings and pre-XML ones are both legitimate outcomes; record
        # what was attempted so the next run does not repeat it.
        save_ledger(name, stamps)
        print("\nnothing new to write")
        return 0

    pairs = sorted({(c, a["company"])
                    for v in live.values() for c, a in v["agg"].items()})
    print(f"\nresolving {len(pairs)} CUSIPs to tickers")
    tickers = issuers.resolve(pairs)
    hit = sum(1 for c, _ in pairs if tickers.get(c, {}).get("ticker"))
    print(f"  resolved {hit}/{len(pairs)}")

    for period in sorted(live):
        p = write(name, label, period, live[period]["agg"], tickers)
        stamps[period] = live[period]["filed"]
        print(f"  wrote {p.relative_to(HERE)}")
    save_ledger(name, stamps)
    print(f"\n{len(live)} period(s) -> data/{name}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
