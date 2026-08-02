"""Identify the issuer behind a filing line: (CUSIP, filed name) -> US ticker.

  python3 issuers.py duquesne        # what is still unidentified, and why
  python3 issuers.py --audit         # every name-matched result, worst first

A 13F names a holding by CUSIP and a shorthand issuer name. Everything
downstream is keyed on ticker, so something has to close that gap, and no free
CUSIP->ticker mapping is complete. Three strategies, tried in order, each
recording how it decided so a wrong answer is visible rather than plausible:

  figi      OpenFIGI's CUSIP mapping. Authoritative where it answers, but it
            does not carry every foreign-issuer CINS -- Seagate's G7997R103
            and BBB Foods' G0896C103 are both absent.
  name      Score the filed name against every US listing. This is the layer
            that earns its keep: a US-listed issuer is always in Nasdaq's
            directory under a name the filing echoes, however abbreviated.
  override  Hand-checked, one line of evidence each. There is always a tail,
            and a short honest table beats a matcher tuned until it guesses.

Why scoring rather than listings.names_agree: that function answers "could
these two names be the same issuer" about ONE proposed pair, and it is
deliberately loose -- one shared token is enough. Used as a search over twelve
thousand listings it returns 242 candidates for "Seagate Technology Hldngs Pl",
every company with "TECHNOLOGY" in its name, and an ambiguous answer is thrown
away. Identity does not live in the shared word, it lives in the rare one, so
tokens are weighted by how many listings use them and a winner has to beat the
runner-up by a margin.
"""

import html
import json
import math
import sys
from pathlib import Path

import cusips
import listings

REF = Path(__file__).parent / "data" / "reference"
DATA = Path(__file__).parent / "data"
CACHE = REF / "issuer_tickers.json"
SEC_NAMES = REF / "company_tickers.json"

# Thresholds in IDF units. A token used by one listing in twelve thousand
# scores ~9.4; "TECHNOLOGY", used by 242 of them, scores ~3.9.
#
# Calibrated on two populations, because they behave differently. Run at a
# floor of 6.0 against the 446 CUSIPs OpenFIGI does resolve, scoring picked
# FIGI's own ticker 315 times and a different one twice. Against the 155 it
# does not resolve, precision collapsed to 77%: FIGI misses an issuer largely
# when the issuer is delisted, and a dead company's name reliably half-matches
# a living one. Luckin Coffee scored onto Coffee Holding, Kite Pharma onto
# Kite Realty, Mead Johnson onto Johnson & Johnson.
#
# Raw score turned out to be the wrong knob. A correct single-word match --
# "Linde Plc" against Linde plc -- scores the same 5 to 9 as a wrong one, so
# any bar high enough to exclude Luckin Coffee also excluded CRH, Linde and
# Transocean. What separates them is UNCOVERED_MAX below: every one of the ten
# known-wrong matches leaves a distinctive filed word unexplained, and every
# correct one explains the whole name. So the score floor is low and does the
# coarse work, coverage does the deciding, and the band between PROPOSE and
# MIN_SCORE is printed for a human -- which is what OVERRIDES is for.
MIN_SCORE = 7.5
PROPOSE = 6.0
# How much of the filed name may go unexplained by the listing, in IDF units.
# Zero would be too strict -- a filing says "Ihs Holding Limited" where the
# listing says "IHS Holding Ltd" and stray words do occur -- but a whole
# distinctive word left over means the two names describe different companies.
UNCOVERED_MAX = 3.0
# The winner must be this much better than the next candidate. Two issuers
# sharing their only distinctive token is exactly the case to refuse.
MARGIN = 1.6
# Below this length a prefix match is coincidence, not an abbreviation.
#
# Containment, not shared prefix. Scoring a common prefix of five characters
# instead was tried and is worse: it pairs Expeditors with Expedia, Allegheny
# with Allegion and Billiton with Bollinger, and cost more right answers than
# the abbreviations it caught. Words that are abbreviated internally --
# "Vertex Pharms" for "Vertex Pharmaceuticals" -- are left to the name check
# failing safe and the row being reported as unidentified.
MIN_PREFIX = 4
# Listings that are not the thing a 13F share line can be. The filing reports
# a share count of type SH, so the warrant, unit and preferred lines of the
# same issuer are the wrong instrument -- and they are the runner-up that was
# blocking the right answer, because their names are nearly identical.
# NewAmsterdam scored 14.5 against its own warrant line at 12.6 and was
# refused as ambiguous.
NOT_A_SHARE = ("WARRANT", "RIGHT", "UNIT", "PREFERRED", "DEBENTURE", "NOTE",
               "DEPOSITARY", "SUBSCRIPTION")
INSTRUMENT_PENALTY = 4.0

# What a candidate is charged for each distinctive word the filing never used.
# Half weight, not full: filings really do drop words, so an unused token is
# evidence against, not proof against.
UNMATCHED = 0.5

# CUSIPs no strategy identifies, resolved by hand. Each line states the
# evidence, because an unexplained entry here is indistinguishable from a
# guess and will outlive whoever added it.
# A ticker of None means "identified as unidentifiable": the filing names a
# company that no longer maps to any listing, and the obvious match is a
# different one. Corporate actions are the blind spot no name scoring can
# cover -- after a rename the names still agree perfectly, and after a spinoff
# the surviving ticker belongs to the other half of the company.
OVERRIDES: dict[str, tuple[str | None, str]] = {
    # Both are one-word issuer names, which is the case scoring is worst at:
    # there is only the one token, so a correct match scores no higher than a
    # coincidental one and both sit under the floor. Checked by hand against
    # the filing's own share counts and the Nasdaq directory.
    "G25508105": ("CRH", "CRH plc, Irish CINS, NYSE: CRH"),
    "H8817H100": ("RIG", "Transocean Ltd, Swiss CINS, NYSE: RIG"),

    # Foreign CINSs whose filed name carries a suffix no listing uses, so the
    # coverage rule read the leftover word as an unexplained one. Each was
    # checked against the Nasdaq directory by hand.
    "G68707101": ("PAGS", "PagSeguro Digital Ltd, Cayman CINS, NYSE: PAGS. "
                          "Held back by the filing's 'COM' for Common."),
    "N7902X106": ("ST", "Sensata Technologies, Dutch CINS filed as NV where "
                        "the listing reads plc, NYSE: ST."),
    "Y2573F102": ("FLEX", "Flex Ltd, Singapore CINS, Nasdaq: FLEX. A one-word "
                          "issuer name, which scores low however right it is."),
    "G85158106": ("STNE", "StoneCo Ltd, Cayman CINS, Nasdaq: STNE. Same."),

    # Refusals. Every one is a delisted issuer whose name half-matches a
    # living company, and the listing the matcher proposed says so itself --
    # no acquisition history needed to see it. Recorded rather than left
    # unanswered so the same question is not asked on every run.
    "013817101": (None, "Alcoa Inc renamed to Arconic in 2016. The Alcoa "
                        "Corporation now trading as AA is the spun-off half "
                        "and carries CUSIP 013872106, not this one."),
    "G47791101": (None, "Ingersoll-Rand plc became Trane Technologies in "
                        "2020. The IR ticker went to Gardner Denver, which "
                        "took the Ingersoll Rand name -- a different issuer."),
    "L5140P101": (None, "Intelsat S.A. The match was Intel Corporation."),
    "22266L106": (None, "Coupa Software. The match was Coupang."),
    "49803L109": (None, "Kite Pharma. The match was Kite Realty Group Trust."),
    "582839106": (None, "Mead Johnson Nutrition. The match was Johnson & Johnson."),
    "655044105": (None, "Noble Energy. The match was Noble Corporation, a driller."),
    "485170302": (None, "Kansas City Southern. The match was City Holding Company."),
    "254709108": (None, "Discover Financial Services. The match was an iShares "
                        "financial-services ETF."),
    "03940R107": (None, "Arch Resources, a coal miner. The match was Arch "
                        "Capital Group, an insurer."),
    "723787107": (None, "Pioneer Natural Resources. The match was Pioneer "
                        "Acquisition I Corp, a blank-cheque company."),
    "762760106": (None, "Rice Energy. The match was Rice Acquisition Corp 3."),
    "90341W108": (None, "US Airways Group. The match was AiRWA Inc."),
    "966244105": (None, "WhiteWave Foods. The match was B&G Foods."),
    "G04553106": (None, "Arco Platform. The match was Arcosa."),
    "867975104": (None, "Sunrise Communications AG. The match was Sunrise "
                        "Realty Trust."),
    "24279D105": (None, "Decarbonization Plus Acquisition II. The match was "
                        "The Acquirers Fund, an ETF."),
    "G47567105": (None, "IHS Markit Ltd. The match was IHS Holding Limited, "
                        "the tower operator, which is a different company and "
                        "is itself correctly resolved under G4701H109."),

    # The judgement calls, decided the same way as Alcoa: a CUSIP identifies a
    # security, and a corporate action gives the survivor a new one. Mapping
    # the old CUSIP to the new ticker asserts a continuity the identifier
    # itself denies, and the position would then be priced and linked as a
    # company the filer never reported holding.
    "260543103": (None, "Dow Chemical Co, which merged into DowDuPont and was "
                        "split out again as Dow Inc under a new CUSIP. This "
                        "one is the pre-merger security."),
    "78781P105": (None, "SailPoint Technologies Holdings, taken private in "
                        "2022. The SailPoint listed again in 2025 is a "
                        "different security under a different CUSIP."),
    "90130A101": (None, "Twenty-First Century Fox, most of which went to "
                        "Disney. The remainder became Fox Corporation, whose "
                        "A and B lines scored identically here -- the tie is "
                        "the evidence that this cannot be settled by name."),
    "G61188101": (None, "Liberty Global. Two CUSIPs in this book both propose "
                        "LBTYA, so at least one is a different share class or "
                        "the pre-redomicile line. Per-class evidence is needed; "
                        "one ticker for both would be wrong for one of them."),
    "G61188127": (None, "Liberty Global, the second of the two. See above."),
}


# Filing shorthand, expanded before tokenising. Without this a filed name
# carries words no listing ever uses -- "Seagate Technology HLDNGS PL" -- and
# the coverage rule below cannot tell shorthand apart from a word the listing
# genuinely lacks. Only unambiguous contractions belong here.
SHORTHAND = {
    "HLDNGS": "HOLDINGS", "HLDGS": "HOLDINGS", "HLDG": "HOLDING",
    "HOLDINGS": "HOLDINGS", "PL": "PLC", "TECHNLGIES": "TECHNOLOGIES",
    "TECHNOLGIES": "TECHNOLOGIES", "TECHS": "TECHNOLOGIES",
    "PHARMS": "PHARMACEUTICALS", "PHARM": "PHARMACEUTICALS",
    "SVCS": "SERVICES", "SVC": "SERVICE", "GRP": "GROUP", "INDS": "INDUSTRIES",
    "INTL": "INTERNATIONAL", "INTERNATL": "INTERNATIONAL", "NATL": "NATIONAL",
    "COMMS": "COMMUNICATIONS", "COMM": "COMMUNICATIONS", "SYS": "SYSTEMS",
    "MGMT": "MANAGEMENT", "FINL": "FINANCIAL", "RES": "RESOURCES",
    "PPTYS": "PROPERTIES", "NUTN": "NUTRITION", "ENTMT": "ENTERTAINMENT",
    "BK": "BANK", "CTL": "CONTROL", "STL": "STEEL", "CENTY": "CENTURY",
}


def _tokens(name: str) -> set[str]:
    # EDGAR serves the issuer name with XML entities intact ("Am Int&apos;l
    # Grp"), which tokenise into APOS and AMP and then match nothing real.
    # Expanded first, then filtered again: "HLDNGS" is not in listings'
    # boilerplate list but "HOLDINGS" is, and a shorthand that expands into a
    # word every listing drops must be dropped too -- otherwise the filed name
    # carries a token the candidate side has already thrown away, and coverage
    # scores it as unexplained.
    expanded = {SHORTHAND.get(t, t) for t in listings._tokens(html.unescape(name))}
    return {t for t in expanded if t not in listings.BOILERPLATE}


def sec_titles() -> dict[str, list[str]]:
    """ticker -> SEC's own registered company titles.

    A second name for each issuer, and the one likelier to match: both the
    13F and this file are SEC-side names, while Nasdaq's directory names the
    security ("Seagate Technology Holdings plc Ordinary Shares").
    """
    if not SEC_NAMES.exists():
        return {}
    raw = json.loads(SEC_NAMES.read_text(encoding="utf-8"))
    rows = raw.values() if isinstance(raw, dict) else raw
    out: dict[str, list[str]] = {}
    for r in rows:
        t = (r.get("ticker") or "").strip().upper()
        title = (r.get("title") or "").strip()
        if t and title:
            out.setdefault(t, []).append(title)
    return out


class Index:
    """Every US listing, its names, and how distinctive each token is."""

    def __init__(self, listed: dict[str, tuple[str, str]] | None = None):
        self.listed = listed if listed is not None else listings.load()
        titles = sec_titles()
        self.names: dict[str, list[str]] = {}
        for symbol, (_exchange, name) in self.listed.items():
            self.names[symbol] = [name] + titles.get(symbol, [])

        # Document frequency over listings, not over occurrences: a token used
        # by one company a hundred times is still one company.
        self.df: dict[str, int] = {}
        for symbol, names in self.names.items():
            for tok in {t for n in names for t in _tokens(n)}:
                self.df[tok] = self.df.get(tok, 0) + 1
        self.n = max(len(self.names), 1)

        # Postings, so a lookup touches the listings sharing a token rather
        # than all twelve thousand.
        self.postings: dict[str, list[str]] = {}
        for symbol, names in self.names.items():
            for tok in {t for n in names for t in _tokens(n)}:
                self.postings.setdefault(tok, []).append(symbol)

    def idf(self, token: str) -> float:
        return math.log(self.n / (1 + self.df.get(token, 0)))

    def score(self, filed: set[str], symbol: str) -> float:
        """Weight of what the filed name and this listing share, less what
        only the listing has.

        A filed token counts once, at its best match: filings abbreviate
        ("PHARMACEUTICALS" -> "PHARMS") and truncate, so a prefix in either
        direction counts, but only the strongest match for that token, or a
        long name would score by repetition.

        The subtraction is what stops a delisted issuer being handed to a
        living namesake. Hess Corp was acquired and is no longer listed;
        matching on the shared HESS alone gives Hess Midstream, which is a
        different company. Charging the candidate for MIDSTREAM -- a word the
        filing never used -- drops it below the floor and the answer becomes
        "unidentified", which is the truth.
        """
        cand = {t for n in self.names.get(symbol, []) for t in _tokens(n)}
        total = 0.0
        matched: set[str] = set()
        for tok in filed:
            best, hit = 0.0, None
            for other in cand:
                if tok == other:
                    if self.idf(tok) > best:
                        best, hit = self.idf(tok), other
                elif ((tok.startswith(other) or other.startswith(tok))
                      and min(len(tok), len(other)) >= MIN_PREFIX):
                    # An abbreviation is weaker evidence than the whole word.
                    weak = 0.75 * min(self.idf(tok), self.idf(other))
                    if weak > best:
                        best, hit = weak, other
            total += best
            if hit:
                matched.add(hit)
        total -= UNMATCHED * sum(self.idf(t) for t in cand - matched)
        listed_name = self.listed.get(symbol, ("", ""))[1].upper()
        if any(w in listed_name for w in NOT_A_SHARE):
            total -= INSTRUMENT_PENALTY
        return total

    def uncovered(self, filed: set[str], symbol: str) -> float:
        """Weight of the filed name this listing does not account for.

        The sharpest signal there is. Every one of the ten known-wrong matches
        left a distinctive filed word unexplained -- LUCKIN against Coffee
        Holding, PHARMA against Kite Realty, ENERGY against Noble Corporation
        -- while a correct match at the same raw score explains the whole
        name. Linde Plc against Linde plc leaves nothing over.
        """
        cand = {t for n in self.names.get(symbol, []) for t in _tokens(n)}
        loose = 0.0
        for tok in filed:
            if tok in cand:
                continue
            if any((tok.startswith(o) or o.startswith(tok))
                   and min(len(tok), len(o)) >= MIN_PREFIX for o in cand):
                continue
            loose += self.idf(tok)
        return loose

    def best(self, company: str) -> tuple[str | None, float, float]:
        """(symbol, score, runner-up score) for the filed name."""
        filed = _tokens(company)
        if not filed:
            return None, 0.0, 0.0
        seen: set[str] = set()
        for tok in filed:
            for other in self.postings:
                if tok == other or (
                        (tok.startswith(other) or other.startswith(tok))
                        and min(len(tok), len(other)) >= MIN_PREFIX):
                    seen.update(self.postings[other])
        if not seen:
            return None, 0.0, 0.0
        # Sorted on score descending, symbol ascending: a tie must not be
        # settled by whichever ticker happens to sort last.
        ranked = sorted(((-self.score(filed, s), s) for s in seen))
        top, symbol = -ranked[0][0], ranked[0][1]
        second = -ranked[1][0] if len(ranked) > 1 else 0.0
        return symbol, top, second


def by_name(company: str, index: Index) -> dict | None:
    symbol, score, second = index.best(company)
    if not symbol or score < MIN_SCORE:
        return None
    if second and score < MARGIN * second:
        return None
    if index.uncovered(_tokens(company), symbol) > UNCOVERED_MAX:
        return None
    exchange, name = index.listed[symbol]
    return {"ticker": symbol, "name": name, "type": exchange, "via": "name",
            "score": round(score, 2), "runner_up": round(second, 2)}


def load_cache() -> dict:
    return json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}


def resolve(items: list[tuple[str, str]], refresh: bool = False) -> dict[str, dict]:
    """items: (cusip, filed issuer name). Returns cusip -> {ticker, name, via, ...}.

    Same signature as cusips.resolve, which this supersedes for filing-derived
    sources; the FIGI layer is still cusips' own.
    """
    cache = {} if refresh else load_cache()
    wanted = {c: n for c, n in items}
    missing = [(c, n) for c, n in items if not cache.get(c, {}).get("ticker")]

    if missing:
        # FIGI only answers off a US exchange row now, so its answer is taken
        # as given. Testing it against today's directory instead was tried and
        # is wrong: it discards every issuer since acquired or delisted, and a
        # 2015 holding of Alexion should still read ALXN.
        figi = cusips.resolve(missing, refresh=refresh)
        for c, _ in missing:
            hit = figi.get(c) or {}
            # FIGI answers only, even though its cache may hold older entries
            # from the name fallback that used to live there. Those were made
            # under a rule this module has replaced -- it is how Intelsat S.A.
            # came to be identified as Intel -- and a decision must not
            # outlive the rule that made it.
            if hit.get("via") == "figi" and hit.get("ticker"):
                cache[c] = hit

    still = [(c, n) for c, n in items if not cache.get(c, {}).get("ticker")]
    if still:
        index = Index()
        found = 0
        for c, name in still:
            hit = by_name(name, index)
            if hit:
                cache[c] = hit
                found += 1
        print(f"  name match recovered {found}/{len(still)}")

    # Last, so a hand-checked answer always wins over a machine-made one.
    applicable = {c: v for c, v in OVERRIDES.items() if c in wanted}
    if applicable:
        listed = listings.load()
        for c, (ticker, why) in applicable.items():
            if ticker is None:
                cache[c] = {"via": "override", "why": why}
                continue
            exchange, name = listed.get(ticker, ("", ""))
            cache[c] = {"ticker": ticker, "name": name, "type": exchange,
                        "via": "override", "why": why}

    REF.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, indent=1, sort_keys=True), encoding="utf-8")
    return cache


# ---- inspection ----

def manager_rows(manager: str) -> list[tuple[str, str]]:
    """Every (cusip, name) a manager has ever reported."""
    src = DATA / manager
    if not src.is_dir():
        raise SystemExit(f"no such source: data/{manager}")
    import csv
    seen = {}
    for path in sorted(src.glob("positions_*.csv")):
        with path.open(encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                seen[r["cusip"]] = r["company"]
    return sorted(seen.items())


def main(argv: list[str]) -> int:
    args = [a for a in argv[1:] if not a.startswith("--")]
    cache = load_cache()

    if "--audit" in argv:
        rows = [(v.get("score", 0), c, v) for c, v in cache.items()
                if v.get("via") == "name"]
        rows.sort()
        print(f"{len(rows)} name-matched issuer(s), least confident first\n")
        print(f"  {'cusip':<11}{'ticker':<8}{'score':>7}{'next':>7}  listing")
        for score, c, v in rows:
            print(f"  {c:<11}{v['ticker']:<8}{score:>7.1f}"
                  f"{v.get('runner_up', 0):>7.1f}  {v['name'][:44]}")
        return 0

    if not args:
        raise SystemExit("usage: issuers.py <manager> | --audit")

    pairs = manager_rows(args[0])
    resolved = resolve(pairs)
    unknown = [(c, n) for c, n in pairs if not resolved.get(c, {}).get("ticker")]
    via: dict[str, int] = {}
    for c, _ in pairs:
        via[resolved.get(c, {}).get("via", "none")] = \
            via.get(resolved.get(c, {}).get("via", "none"), 0) + 1

    print(f"\n{args[0]}: {len(pairs) - len(unknown)}/{len(pairs)} identified")
    for k in sorted(via):
        print(f"  {k:<9} {via[k]}")
    if unknown:
        index = Index()
        proposals, blank = [], []
        for c, n in unknown:
            if c in OVERRIDES:
                # Already decided, and decided as "no ticker". Re-proposing it
                # every run would ask the same question after it was answered.
                continue
            symbol, score, second = index.best(n)
            (proposals if symbol and score >= PROPOSE else blank).append(
                (score, c, n, symbol, second))
        proposals.sort(reverse=True)

        if proposals:
            print(f"\n{len(proposals)} proposal(s) below the accept bar. Check each, "
                  f"then paste into OVERRIDES:")
            for score, c, n, symbol, second in proposals:
                listing = index.listed[symbol][1]
                print(f'  "{c}": ("{symbol}", ""),'.ljust(34)
                      + f'# {n[:30]:<32}-> {listing[:36]}  {score:.1f}/{second:.1f}')
        if blank:
            print(f"\n{len(blank)} with no candidate at all "
                  f"(delisted, or a name nothing echoes):")
            for _s, c, n, _sym, _sec in blank[:15]:
                print(f"  {c:<11}{n[:44]}")
            if len(blank) > 15:
                print(f"  ... and {len(blank) - 15} more")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
