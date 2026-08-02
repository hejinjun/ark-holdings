"""Regression check for the issuer matcher.

  python3 test_issuers.py

The thresholds in issuers.py were set by hand-checking six hundred filing
names against the Nasdaq directory. That check is worth exactly nothing if it
only ever ran once: the matcher fails silently and plausibly -- Luckin Coffee
becomes Coffee Holding, Kite Pharma becomes Kite Realty -- so a loosened
threshold looks like more coverage rather than more errors.

The labels below are that verification, frozen. RESOLVES is what the matcher
must still get right; REFUSES is what it must still refuse, each with the wrong
answer it produced before the rule that stopped it. Both were confirmed against
the filing's own issuer name and the listing directory, not against the
matcher's output.

The directory is live, so a company delisting can legitimately break a case
here. That is a prompt to re-check the row and move it, not to relax a bound.
"""

import sys

import issuers

# Filed name -> the ticker it must resolve to. Foreign-issuer CINSs OpenFIGI
# does not carry, which is the whole reason the name layer exists.
RESOLVES = {
    "Seagate Technology Hldngs Pl": "STX",
    "Bbb Foods Inc": "TBBB",
    "Newamsterdam Pharma Company": "NAMS",
    "Wave Life Sciences Ltd": "WVE",
    "Linde Plc": "LIN",
    "MEDTRONIC PLC": "MDT",
    "Chubb Limited": "CB",
    "Herbalife Ltd.": "HLF",
    "Flutter Entmt Plc": "FLUT",
    "Elastic N V": "ESTC",
    "Stellantis N.V": "STLA",
    "Elbit Sys Ltd": "ESLT",
    "Xp Inc": "XP",
    "Nu Hldgs Ltd": "NU",
    "Jbs N.V.": "JBS",
    "Ac Immune Sa": "ACIU",
    "Tower Semiconductor Ltd": "TSEM",
    "NXP Semiconductors NV": "NXPI",
    "Spotify Technology S A": "SPOT",
    "Global E Online Ltd": "GLBE",
    "Ascendis Pharma A/S": "ASND",
    "NABORS INDUSTRIES LTD": "NBR",
    "Nvent Electric Plc": "NVT",
    "Joby Aviation Inc": "JOBY",
    "Arista Networks Inc": "ANET",
    "Astrazeneca PLC": "AZN",
    "Carnival Corp": "CCL",
    "Draftkings Inc": "DKNG",
    "Lam Research Corp": "LRCX",
    "T-Mobile Us Inc": "TMUS",
    "Royal Carib&apos;n Cruises Ltd": "RCL",     # entity-encoded, as EDGAR serves it
    "Charter Comm&apos;s Inc": "CHTR",
    "Nektar Therapeutics": "NKTR",
    "Nextcure Inc": "NXTC",
    "Atlassian Corp Plc": "TEAM",
    "SBA Comms Corp": "SBAC",
    "Lyondellbasell Industries N": "LYB",
    "Ihs Holding Limited": "IHS",
}

# Filed name -> the wrong ticker the matcher used to return. Every one is a
# delisted or acquired issuer whose name half-matches a living company, which
# is the failure mode the coverage rule exists to stop.
REFUSES = {
    "Luckin Coffee Inc": "JVA",                  # Coffee Holding Co.
    "Kite Pharma Inc": "KRG",                    # Kite Realty Group
    "Mead Johnson Nut&apos;n Co": "JNJ",         # Johnson & Johnson
    "Noble Energy Inc": "NE",                    # Noble Corporation, a driller
    "Coupa Software Inc": "CPNG",                # Coupang
    "Arco Platform Ltd Com": "ACA",              # Arcosa
    "Rice Energy Inc": "KRSP",                   # Rice Acquisition Corp
    "STAMPS COM INC": "IDAI",                    # T Stamp Inc
    "Sunrise Communications Ag Ads": "SUNS",     # Sunrise Realty Trust
    "Decarbonization Plus Acqu Ii": "ZIG",       # The Acquirers Fund
    "Intelsat S A": "INTC",                      # Intel
    "Ihs Markit Ltd": "IHS",                     # IHS Holding, a different firm
    "Hess Corp": "HESM",                         # Hess Midstream
    "Expeditors Int&apos;l of Wash Inc.": "EXPE",  # Expedia
    "Allegheny Tech Inc.": "ALLE",               # Allegion
    "Vertex Pharms Inc": "VERX",                 # Vertex, Inc.
}

# CUSIPs whose obvious match is the wrong side of a corporate action. Name
# scoring cannot see these: after a rename the two names agree perfectly.
REFUSES_BY_CUSIP = {
    "013817101": "Alcoa Inc, renamed Arconic; AA is the spun-off half",
    "G47791101": "Ingersoll-Rand plc, became Trane Technologies; IR went elsewhere",
}


def main() -> int:
    index = issuers.Index()
    failures = []

    for name, want in RESOLVES.items():
        hit = issuers.by_name(name, index)
        got = hit["ticker"] if hit else None
        if got != want:
            failures.append(f"{name!r} resolved to {got}, expected {want}")

    for name, never in REFUSES.items():
        hit = issuers.by_name(name, index)
        got = hit["ticker"] if hit else None
        if got == never:
            failures.append(f"{name!r} resolved to {never} again")

    for cusip, why in REFUSES_BY_CUSIP.items():
        entry = issuers.OVERRIDES.get(cusip)
        if not entry or entry[0] is not None:
            failures.append(f"{cusip} must be refused by OVERRIDES: {why}")

    checked = len(RESOLVES) + len(REFUSES) + len(REFUSES_BY_CUSIP)
    if failures:
        print(f"FAIL  {len(failures)} of {checked} checks\n")
        for f in failures:
            print(f"  {f}")
        print(f"\nThresholds in issuers.py: MIN_SCORE={issuers.MIN_SCORE}, "
              f"UNCOVERED_MAX={issuers.UNCOVERED_MAX}, MARGIN={issuers.MARGIN}")
        return 1

    print(f"ok  {checked} checks  "
          f"({len(RESOLVES)} must resolve, {len(REFUSES) + len(REFUSES_BY_CUSIP)} must not)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
