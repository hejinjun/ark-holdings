"""Bucket definitions for the report's filter chips.

Each dimension is a list of (key, label, lower, upper) with the range
half-open on the right: lower <= value < upper. Edit the numbers here and the
chips, the assignment, and the counts all follow -- nothing else hardcodes them.

Two market-cap-shaped dimensions are deliberately kept apart. `cap` is how big
the company is; `pos` is how much ARK has riding on it. A micro-cap that ARK
holds $300M of is a different animal from a mega-cap it holds $3M of, and only
having both dimensions lets that combination be selected.
"""

INF = float("inf")

DIMENSIONS = [
    {
        "key": "cap", "label": "Market cap", "label_zh": "公司市值", "field": "market_cap",
        "buckets": [
            ("mega", "Mega ≥$200B", 200e9, INF),
            ("large", "Large $10–200B", 10e9, 200e9),
            ("mid", "Mid $2–10B", 2e9, 10e9),
            ("small", "Small $300M–2B", 300e6, 2e9),
            ("micro", "Micro <$300M", 0, 300e6),
        ],
    },
    {
        # Cut on powers of ten, which is how the size of a position is actually
        # read: hundred-million, ten-million, million. The report badges each
        # row with the same tiers, so chip and badge always agree.
        "key": "pos", "label": "ARK position", "label_zh": "ARK 持仓", "field": "position_value",
        "buckets": [
            ("p1", "≥$100M", 100e6, INF),
            ("p2", "$10–100M", 10e6, 100e6),
            ("p3", "$1–10M", 1e6, 10e6),
            ("p4", "<$1M", 0, 1e6),
        ],
    },
    {
        "key": "px", "label": "Share price", "label_zh": "股价", "field": "price",
        "buckets": [
            ("x6", "≥$300", 300, INF),
            ("x5", "$100–300", 100, 300),
            ("x4", "$50–100", 50, 100),
            ("x3", "$20–50", 20, 50),
            ("x2", "$5–20", 5, 20),
            ("x1", "<$5", 0, 5),
        ],
    },
    {
        # off_high is negative; buckets are stated on its magnitude.
        "key": "oh", "label": "Off 52w high", "label_zh": "距 52 周高点", "field": "drawdown",
        "buckets": [
            ("d1", "<10%", 0, 10),
            ("d2", "10–30%", 10, 30),
            ("d3", "30–50%", 30, 50),
            ("d4", "50–70%", 50, 70),
            ("d5", "≥70%", 70, INF),
        ],
    },
    {
        "key": "ol", "label": "Off 52w low", "label_zh": "距 52 周低点", "field": "off_low",
        "buckets": [
            ("r1", "<10%", 0, 10),
            ("r2", "10–50%", 10, 50),
            ("r3", "50–100%", 50, 100),
            ("r4", "100–200%", 100, 200),
            ("r5", "≥200%", 200, INF),
        ],
    },
    {
        "key": "rng", "label": "Range position", "label_zh": "区间位置", "field": "range_pct",
        "buckets": [
            ("top", "Top >75%", 75, INF),
            ("mid", "Middle 25–75%", 25, 75),
            ("bot", "Bottom <25%", 0, 25),
        ],
    },
    {
        # (high - low) / low: how wide a band the name traded in this year.
        "key": "amp", "label": "52w amplitude", "label_zh": "52 周振幅", "field": "amplitude",
        "buckets": [
            ("a1", "<50%", 0, 50),
            ("a2", "50–100%", 50, 100),
            ("a3", "100–200%", 100, 200),
            ("a4", "≥200%", 200, INF),
        ],
    },
    {
        "key": "nf", "label": "Funds holding", "label_zh": "持有基金数", "field": "n_funds",
        "buckets": [
            ("f1", "1 fund", 1, 2),
            ("f2", "2–3 funds", 2, 4),
            ("f3", "4+ funds", 4, INF),
        ],
    },
]

# The leaderboard needs its own cuts. Its universe starts around $60B, so the
# holdings page's cap buckets would collapse it into two chips -- "mega" and
# "large" -- and say nothing. Rank tiers and trillion-scale cap bands are what
# separate companies that are all already large.
LEADER_DIMENSIONS = [
    {
        "key": "tier", "label": "Rank", "label_zh": "排名", "field": "rank",
        "buckets": [
            ("t1", "Top 10", 1, 11),
            ("t2", "11–50", 11, 51),
            ("t3", "51–100", 51, 101),
            ("t4", "101–200", 101, INF),
        ],
    },
    {
        "key": "cap", "label": "Market cap", "label_zh": "市值", "field": "market_cap",
        "buckets": [
            ("c1", "≥$1T", 1e12, INF),
            ("c2", "$500B–1T", 500e9, 1e12),
            ("c3", "$200–500B", 200e9, 500e9),
            ("c4", "$100–200B", 100e9, 200e9),
            ("c5", "<$100B", 0, 100e9),
        ],
    },
    {
        # Same cuts as the holdings page's `oh`, so a name filtered as "30-50%
        # off its high" means the same thing on both pages.
        "key": "oh", "label": "Off 52w high", "label_zh": "距 52 周高点", "field": "drawdown",
        "buckets": [
            ("d1", "<10%", 0, 10),
            ("d2", "10–30%", 10, 30),
            ("d3", "30–50%", 30, 50),
            ("d4", "50–70%", 50, 70),
            ("d5", "≥70%", 70, INF),
        ],
    },
    {
        "key": "rng", "label": "Range position", "label_zh": "区间位置", "field": "range_pct",
        "buckets": [
            ("top", "Top >75%", 75, INF),
            ("mid", "Middle 25–75%", 25, 75),
            ("bot", "Bottom <25%", 0, 25),
        ],
    },
    {
        # Listing vintage, which is the cheapest available proxy for whether a
        # company got here the slow way or the fast way.
        "key": "ipo", "label": "Listed", "label_zh": "上市年代", "field": "ipo_decade",
        "buckets": [
            ("y5", "2020s", 2020, INF),
            ("y4", "2010s", 2010, 2020),
            ("y3", "2000s", 2000, 2010),
            ("y2", "1990s", 1990, 2000),
            ("y1", "Before 1990", 0, 1990),
        ],
    },
]

UNKNOWN = ("none", "Unclassified", "未分类")

# Buckets whose label is not already language-neutral. Numeric labels like
# "$50–200M" or "10–30%" read the same in both, so only these need a pair.
LABEL_ZH = {'Mega ≥$200B': '巨盘 ≥$200B', 'Large $10–200B': '大盘 $10–200B', 'Mid $2–10B': '中盘 $2–10B', 'Small $300M–2B': '小盘 $300M–2B', 'Micro <$300M': '微盘 <$300M', 'Top >75%': '顶部 >75%', 'Middle 25–75%': '中部 25–75%', 'Bottom <25%': '底部 <25%', '1 fund': '1 只', '2–3 funds': '2-3 只', '4+ funds': '4 只以上', '≥$100M': '≥1亿', '$10–100M': '1千万–1亿', '$1–10M': '100万–1千万', '<$1M': '<100万',
            'Top 10': '前 10', '11–50': '11–50 名', '51–100': '51–100 名', '101–200': '101–200 名',
            '2020s': '2020 年代', '2010s': '2010 年代', '2000s': '2000 年代', '1990s': '1990 年代',
            'Before 1990': '1990 年前'}


def assign(dim: dict, value) -> str:
    """Bucket key for one value, or the unknown key when there is no value."""
    if value is None:
        return UNKNOWN[0]
    for key, _label, lo, hi in dim["buckets"]:
        if lo <= value < hi:
            return key
    return UNKNOWN[0]


def spec(dim: dict, used: set[str]) -> dict:
    """The dimension as the page needs it: only buckets that matched something,
    so no chip on screen can ever return zero rows."""
    options = [{"v": k, "label": lb, "label_zh": LABEL_ZH.get(lb, lb)}
               for k, lb, _lo, _hi in dim["buckets"] if k in used]
    if UNKNOWN[0] in used:
        options.append({"v": UNKNOWN[0], "label": UNKNOWN[1], "label_zh": UNKNOWN[2]})
    return {"key": dim["key"], "label": dim["label"],
            "label_zh": dim["label_zh"], "options": options}
