"""Resolve a CUSIP to a US ticker.

13F filings identify holdings by CUSIP and issuer name only. Everything
downstream of the position table -- quotes, links, company facts, the segment
filters -- is keyed on ticker, so this is the one piece of plumbing a 13F
source needs that an ARK source does not.

Two steps, because neither alone is enough:

  OpenFIGI   authoritative and free, no key, but it does not carry every
             foreign-issuer CINS. BBB Foods (G0896C103, NYSE: TBBB) is absent.
  name match reuses listings.names_agree against Nasdaq's own directory, which
             covers exactly the cases OpenFIGI misses -- a US-listed issuer
             always appears there under a name the filing echoes.

Results are cached, including the misses, so a rerun costs nothing.
"""

import json
import re
import time
import urllib.request
from pathlib import Path

import listings

REF = Path(__file__).parent / "data" / "reference"
CACHE = REF / "cusip_tickers.json"
FIGI = "https://api.openfigi.com/v3/mapping"
UA = "ark-holdings/1.0"
# Unauthenticated OpenFIGI caps a request at 10 jobs -- 25 returns 413 and the
# whole batch is lost -- and about 25 requests a minute.
BATCH = 10
DELAY = 3.0
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
        pick = (us or rows or [None])[0]
        if pick and pick.get("ticker"):
            out[cusip] = {"ticker": pick["ticker"], "name": pick.get("name") or "",
                          "type": pick.get("securityType") or "", "via": "figi"}
    return out


def _by_name(company: str, listed: dict) -> dict | None:
    """Last resort: find the US listing whose issuer name agrees with the
    filing's. Only accepted when exactly one candidate matches, so a common
    word can never pull in the wrong company."""
    tokens = listings._tokens(company)
    if not tokens:
        return None
    hits = []
    for symbol, (exchange, name) in listed.items():
        if listings.names_agree(company, name):
            hits.append((symbol, exchange, name))
    if len(hits) != 1:
        return None
    symbol, exchange, name = hits[0]
    return {"ticker": symbol, "name": name, "type": exchange, "via": "name"}


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

    unresolved = [(c, n) for c, n in items if not cache.get(c, {}).get("ticker")]
    if unresolved:
        listed = listings.load()
        fixed = 0
        for c, name in unresolved:
            hit = _by_name(name, listed)
            if hit:
                cache[c] = hit
                fixed += 1
        print(f"  name fallback recovered {fixed}/{len(unresolved)}")

    save_cache(cache)
    return cache


if __name__ == "__main__":
    import sys
    pairs = [(a, "") for a in sys.argv[1:]]
    for c, v in resolve(pairs).items():
        if c in dict(pairs):
            print(c, v)
