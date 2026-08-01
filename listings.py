"""US exchange listing directory, used to decide what is actually tradeable.

Source is Nasdaq Trader's official symbol files, which together cover Nasdaq,
NYSE, NYSE American, NYSE Arca, Cboe and IEX. Anything absent from both files
is not listed on a US exchange -- foreign local lines (Tel Aviv, Paris, Tokyo)
and OTC ADRs alike.

CUSIP cannot answer this question: CRISPR Therapeutics carries the CINS
H17182108 of a Swiss issuer and trades on Nasdaq as CRSP, while Bezeq carries a
SEDOL and trades only in Tel Aviv.
"""

import urllib.request
from pathlib import Path

REF = Path(__file__).parent / "data" / "reference"
FILES = {
    "nasdaqlisted.txt": "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt",
    "otherlisted.txt": "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt",
}
EXCHANGE = {"N": "NYSE", "A": "NYSE American", "P": "NYSE Arca", "Z": "Cboe BZX", "V": "IEX"}

# Bloomberg exchange suffixes ARK appends to some tickers ("RKLB UQ"). Only the
# base symbol is looked up; the suffix itself is not trusted as evidence.
SUFFIX_LEN = 2


def refresh() -> None:
    REF.mkdir(parents=True, exist_ok=True)
    for name, url in FILES.items():
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            (REF / name).write_bytes(resp.read())


def load() -> dict[str, tuple[str, str]]:
    """symbol -> (exchange, security name). Test issues are dropped."""
    if not all((REF / n).exists() for n in FILES):
        refresh()

    out: dict[str, tuple[str, str]] = {}
    for line in (REF / "nasdaqlisted.txt").read_text().splitlines():
        p = line.split("|")
        if len(p) < 8 or p[0] == "Symbol" or line.startswith("File Creation"):
            continue
        if p[3] == "Y":  # test issue
            continue
        out[p[0]] = ("NASDAQ", p[1])
    for line in (REF / "otherlisted.txt").read_text().splitlines():
        p = line.split("|")
        if len(p) < 8 or p[0] == "ACT Symbol" or line.startswith("File Creation"):
            continue
        if p[6] == "Y":
            continue
        out.setdefault(p[0], (EXCHANGE.get(p[2], p[2]), p[1]))
    return out


def strip_suffix(ticker: str) -> str:
    parts = ticker.split()
    if len(parts) == 2 and len(parts[1]) == SUFFIX_LEN:
        return parts[0]
    return ticker


# Words that carry no identity, so they must not be what makes two names agree.
BOILERPLATE = {
    "THE", "INC", "CORP", "CORPORATION", "CO", "COMPANY", "LTD", "LIMITED", "PLC",
    "SA", "SE", "AG", "NV", "AB", "ASA", "SPA", "KGAA", "LP", "LLC", "GROUP",
    "HOLDING", "HOLDINGS", "CLASS", "CL", "COMMON", "ORDINARY", "SHARES", "SHS",
    "STOCK", "ADR", "ADS", "SPONS", "SPONSORED", "UNSPONSORED", "REG", "TRUST",
    "ETF", "FUND", "NEW", "DEPOSITARY", "RECEIPT", "PAR", "VALUE", "AND", "OF",
    "A", "B", "C", "I", "II", "REPRESENTING", "INTEREST", "INTERESTS",
}


def _tokens(name: str) -> set[str]:
    cleaned = "".join(ch if ch.isalnum() else " " for ch in name.upper())
    return {t for t in cleaned.split() if t not in BOILERPLATE and len(t) > 1}


def names_agree(ark_name: str, listed_name: str) -> bool:
    """Do these two names plausibly describe the same issuer?

    Ticker equality alone is not evidence: a foreign local code collides with a
    US symbol often enough to matter -- Airbus trades as AIR in Paris while AIR
    on the NYSE is AAR Corp, and Titomic is ASX:TTT while TTT is a Treasury ETF.
    ARK also truncates long names ('ARCTURUS THERAPEUTICS HOLDIN'), so a token
    counts as shared when one side is a prefix of the other.
    """
    a, b = _tokens(ark_name), _tokens(listed_name)
    if not a or not b:
        return False
    if a & b:
        return True
    return any(
        (x.startswith(y) or y.startswith(x)) and min(len(x), len(y)) >= 4
        for x in a for y in b
    )


# Issuers that renamed, where the two names share no token but the match is
# real. Each entry is a deliberate override of the name check, confirmed
# against the quote cross-check in quotes.py -- not a way to silence it.
RENAMED = {
    "GE": "GENERAL ELECTRIC",  # now listed as "GE Aerospace"
}


def lookup(ticker: str, listed: dict[str, tuple[str, str]], company: str = ""):
    """Return (symbol, exchange, name) if US-listed, else None.

    Class shares appear as MOG/A in ARK's file and MOG.A in Nasdaq's, so both
    separators are tried. When `company` is given the issuer names must also
    agree, which is what rejects ticker collisions with foreign listings.
    """
    if not ticker:
        return None
    base = strip_suffix(ticker)
    for cand in (base, base.replace("/", "."), base.replace(".", "/")):
        if cand not in listed:
            continue
        exchange, listed_name = listed[cand]
        if company and not names_agree(company, listed_name):
            # Guard against the empty-string default: "" is a substring of
            # everything, which would wave through every mismatch.
            override = RENAMED.get(cand)
            if not override or override.upper() not in company.upper():
                return None
        return (cand, exchange, listed_name)
    return None
