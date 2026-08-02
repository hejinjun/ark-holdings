"""Map a CUSIP to a ticker through OpenFIGI.

One strategy, not a decision: OpenFIGI is authoritative where it answers, but
it does not carry every foreign-issuer CINS (BBB Foods, G0896C103, NYSE: TBBB
is absent) and it falls back to a foreign line when the CUSIP has no US row,
answering ANETEUR for Arista. Judging those answers, and identifying what is
left over, belongs to issuers.py -- which is what callers should use.

A name fallback used to live here. It reused listings.names_agree, which is a
verifier for one proposed pair rather than a search, and over twelve thousand
listings it returned an ambiguous answer for almost everything: on the last
full run it recovered 0 of 74. issuers.py replaced it with scoring.

Results are cached, including the misses, so a rerun costs nothing.
"""

import json
import re
import time
import urllib.request
from pathlib import Path

REF = Path(__file__).parent / "data" / "reference"
CACHE = REF / "cusip_tickers.json"
FIGI = "https://api.openfigi.com/v3/mapping"
UA = "ark-holdings/1.0"
# Unauthenticated OpenFIGI caps a request at 10 jobs -- 25 returns 413 and the
# whole batch is lost -- and about 25 requests a minute.
BATCH = 10
DELAY = 3.0
TICKER = re.compile(r"^[A-Z]{1,5}(?:[./][A-Z])?$")
US_EXCHANGES = {"US", "UN", "UQ", "UA", "UP", "UW", "UR", "UV", "UF"}
# Funds and notes are reportable on a 13F but are not operating companies; the
# securityType is kept so a caller can filter them out.
KEEP_TYPES = None  # None = keep everything, decided downstream


def load_cache() -> dict:
    if CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))
    return {}


def save_cache(cache: dict) -> None:
    REF.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, indent=1, sort_keys=True), encoding="utf-8")


def _figi(batch: list[str]) -> dict[str, dict]:
    body = [{"idType": "ID_CUSIP", "idValue": c} for c in batch]
    req = urllib.request.Request(
        FIGI, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "User-Agent": UA})
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(req, timeout=40) as resp:
                results = json.load(resp)
            break
        except Exception as exc:
            if attempt == 3:
                # Surfaced rather than swallowed: a silent {} here looks
                # identical to "no match" and cost a whole run once.
                print(f"    openfigi failed: {type(exc).__name__} {exc}")
                return {}
            time.sleep(5 * attempt)
    else:
        return {}

    out = {}
    for cusip, r in zip(batch, results):
        rows = r.get("data") or []
        us = [x for x in rows if x.get("exchCode") in US_EXCHANGES]
        # No US row means no answer. Falling back to the first row of any
        # exchange returned ANETEUR for Arista and ACLXGBX for Arcellx --
        # real identifiers for the European lines, and useless here, since
        # nothing downstream can price or link them. A delisted US ticker is
        # a different case and still wanted: Alexion really was ALXN, and a
        # 2015 position should say so.
        pick = (us or [None])[0]
        # A US row can still carry a placeholder rather than a ticker: FIGI
        # returns 9990302D for Apache and MS$F for McDermott, both Bloomberg
        # codes for issuers that stopped trading. A real US ticker is letters,
        # optionally with a class suffix.
        if pick and not TICKER.match(pick.get("ticker") or ""):
            pick = None
        if pick and pick.get("ticker"):
            out[cusip] = {"ticker": pick["ticker"], "name": pick.get("name") or "",
                          "type": pick.get("securityType") or "", "via": "figi"}
    return out


def resolve(items: list[tuple[str, str]], refresh: bool = False) -> dict[str, dict]:
    """items: (cusip, issuer name). Returns cusip -> {ticker, name, type, via}."""
    cache = {} if refresh else load_cache()
    todo = [c for c, _ in items if c not in cache]
    todo = sorted(set(todo))

    for i in range(0, len(todo), BATCH):
        batch = todo[i:i + BATCH]
        found = _figi(batch)
        for c in batch:
            cache[c] = found.get(c) or {}
        print(f"  openfigi {i + len(batch):>4}/{len(todo)}  matched {len(found)}/{len(batch)}")
        if i + BATCH < len(todo):
            time.sleep(DELAY)

    save_cache(cache)
    return cache


if __name__ == "__main__":
    import sys
    pairs = [(a, "") for a in sys.argv[1:]]
    for c, v in resolve(pairs).items():
        if c in dict(pairs):
            print(c, v)
