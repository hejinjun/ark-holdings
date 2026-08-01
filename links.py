"""Outbound links for a holding: filings, financials, quote.

Symbol punctuation is not consistent across these sites, and getting it wrong
produces a dead link rather than an error. Moog's class A shares are `mog.a` on
StockAnalysis but `mog-a` on Nasdaq and Yahoo, so each URL is built from the
form that site actually uses rather than from one normalised symbol.

SEC is keyed on CIK, not ticker, which is the only identifier that survives a
rename or a ticker change.
"""

SITES = [
    # StockAnalysis first: it is the fastest way to actually read the three
    # statements, which is what the link is for.
    {"key": "fin", "label": "Financials", "label_zh": "财报数据"},
    {"key": "sec", "label": "SEC filings", "label_zh": "SEC 申报"},
    {"key": "nasdaq", "label": "Nasdaq", "label_zh": "Nasdaq"},
    {"key": "quote", "label": "Quote", "label_zh": "行情"},
]


def for_symbol(symbol: str, cik: int | None = None) -> list[dict]:
    dotted = symbol.lower()                    # StockAnalysis keeps the dot
    dashed = symbol.replace(".", "-")          # Nasdaq and Yahoo use a dash
    out = [
        {"k": "fin", "u": f"https://stockanalysis.com/stocks/{dotted}/financials/"},
        {"k": "nasdaq",
         "u": f"https://www.nasdaq.com/market-activity/stocks/{dashed.lower()}/financials"},
        {"k": "quote", "u": f"https://finance.yahoo.com/quote/{dashed}"},
    ]
    if cik:
        out.insert(1, {"k": "sec",
                       "u": f"https://www.sec.gov/edgar/browse/?CIK={cik}&owner=exclude"})
    return out
