"""ARK fund registry: ticker -> holdings CSV filename on assets.ark-funds.com.

Filenames change when ARK renames a fund (ARKF was ARK_FINTECH_INNOVATION_ETF
before the blockchain rename). The old URL keeps returning HTTP 200 with stale
data frozen at the rename date, so freshness is validated on every fetch rather
than trusted from the status code.
"""

BASE_URL = "https://assets.ark-funds.com/fund-documents/funds-etf-csv"

# ETFs: full holdings with share counts and market value.
ETFS = {
    "ARKK": "ARK_INNOVATION_ETF_ARKK_HOLDINGS.csv",
    "ARKQ": "ARK_AUTONOMOUS_TECH._&_ROBOTICS_ETF_ARKQ_HOLDINGS.csv",
    # Renamed to "ARK Next Generation Technology ETF" effective 2026-09-07;
    # expect this filename to go stale (HTTP 200, frozen data) on that date.
    "ARKW": "ARK_NEXT_GENERATION_INTERNET_ETF_ARKW_HOLDINGS.csv",
    "ARKG": "ARK_GENOMIC_REVOLUTION_ETF_ARKG_HOLDINGS.csv",
    "ARKF": "ARK_BLOCKCHAIN_&_FINTECH_INNOVATION_ETF_ARKF_HOLDINGS.csv",
    # Renamed from ARK_SPACE_EXPLORATION_&_INNOVATION_ETF around 2026-01-02.
    "ARKX": "ARK_SPACE_&_DEFENSE_INNOVATION_ETF_ARKX_HOLDINGS.csv",
    "PRNT": "THE_3D_PRINTING_ETF_PRNT_HOLDINGS.csv",
    "IZRL": "ARK_ISRAEL_INNOVATIVE_TECHNOLOGY_ETF_IZRL_HOLDINGS.csv",
}

# Venture fund: weight only, no share counts, monthly cadence. Kept out of the
# share/market-value aggregation because there is nothing to sum.
VENTURE = {
    "ARKVX": "ARK_VENTURE_FUND_ARKVX_HOLDINGS.csv",
}

ALL_FUNDS = {**ETFS, **VENTURE}


def url_for(fund: str) -> str:
    return f"{BASE_URL}/{ALL_FUNDS[fund]}"
