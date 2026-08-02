"""Bilingual UI copy for the report.

Both languages ship inside the page, so the toggle is instant and the file stays
self-contained -- no fetch, no second build. Keys are referenced by name from the
template; adding a language means adding a block here and an option to LANGS.

Company and fund names are deliberately left untranslated: a Chinese reader
searching for a holding types the ticker or the English name, and ARK's own file
is the authority on how a security is named.
"""

LANGS = [("en", "EN"), ("zh", "中文")]

# Short badge shown against each position's market value. Keyed by the bucket
# keys in segments.py DIMENSIONS["pos"], so the badge and the filter chip can
# never drift apart.
POSITION_BADGE = {
    "en": {"p1": "100M+", "p2": "10M+", "p3": "1M+", "p4": "<1M"},
    "zh": {"p1": "亿", "p2": "千万", "p3": "百万", "p4": "<百万"},
}

# The magnitude of a company's market cap, in the units the reader's language
# counts in. Three levels, because that is how many the units themselves give
# you: 万亿, 千亿, 亿.
#
# Deliberately NOT keyed to the filter buckets in segments.py, unlike
# POSITION_BADGE. Those cut the range five ways to make the chips useful for
# filtering; this answers "what size of number am I looking at", which the
# units already answer and finer cuts only muddy.
CAP_BADGE = {
    "en": {"t": "1T+", "h": "100B+", "b": "<100B"},
    "zh": {"t": "万亿", "h": "千亿", "b": "亿"},
}

SECTORS = {
    "Technology": "科技",
    "Industrials": "工业",
    "Health Care": "医疗保健",
    "Consumer Discretionary": "非必需消费",
    "Finance": "金融",
    "Telecommunications": "电信",
    "Basic Materials": "基础材料",
    "Utilities": "公用事业",
    "Energy": "能源",
    "Real Estate": "房地产",
    "Consumer Staples": "必需消费",
}

UI = {
    "en": {
        "byFund": "By fund",
        "byFundHint": "Market value is the sum of position values, which tracks fund NAV.",
        "colFund": "Fund",
        "colPositions": "Positions",
        "colMarketValue": "Market value (USD)",
        "colShare": "Share of complex",
        "total": "Total",
        "holdings": "Merged holdings",
        "holdingsHint": "Click a row for the per-fund share split. Click a column head to sort.",
        "search": "Search ticker, company, or CUSIP",
        "clear": "Clear filters",
        "colTicker": "Ticker",
        "colSecurity": "Security",
        "colPrice": "Price",
        "colRange": "52-week range",
        "colOffHigh": "Off high",
        "colOffLow": "Off low",
        "colShares": "Total shares",
        "colFunds": "Funds",
        "colHeldBy": "Held by",
        "sharesByFund": "shares by fund:",
        "finRevenue": "revenue",
        "finMargin": "gross margin",
        "finNetIncome": "net income",
        "finCash": "cash",
        "finRunway": "runway",
        "finDilution": "shares y/y",
        "finBasisChanged": "share basis changed",
        "finQuarters": "q",
        "finNone": "no filings yet",
        "empty": "No security matches those filters.",
        # {n} shown, {t} total, {v} market value, {p} percent
        "status": "{n} of {t} securities  ·  ${v}  ·  {p}% of complex market value",
        "feedLink": "Trade feed \u2192",
        "leadersLink": "Top 300 \u2192",
    },
    "zh": {
        "byFund": "分基金",
        "byFundHint": "市值为各持仓市值之和，与基金净值同步。",
        "colFund": "基金",
        "colPositions": "持仓数",
        "colMarketValue": "市值（美元）",
        "colShare": "占比",
        "total": "合计",
        "holdings": "合并持仓",
        "holdingsHint": "点击某一行查看分基金持股拆分，点击列头排序。",
        "search": "搜索代码、公司名或 CUSIP",
        "clear": "清除筛选",
        "colTicker": "代码",
        "colSecurity": "证券",
        "colPrice": "现价",
        "colRange": "52 周区间",
        "colOffHigh": "距高点",
        "colOffLow": "距低点",
        "colShares": "总股数",
        "colFunds": "基金数",
        "colHeldBy": "持有基金",
        "sharesByFund": "分基金持股：",
        "finRevenue": "营收",
        "finMargin": "毛利率",
        "finNetIncome": "净利",
        "finCash": "现金",
        "finRunway": "现金可撑",
        "finDilution": "股本同比",
        "finBasisChanged": "股本口径变更",
        "finQuarters": "个季度",
        "finNone": "暂无财报",
        "empty": "没有符合筛选条件的证券。",
        "status": "{n} / {t} 只  ·  ${v}  ·  占组合市值 {p}%",
        "feedLink": "交易流 \u2192",
        "leadersLink": "市值榜 \u2192",
    },
}

PAGE = {
    "en": {
        "eyebrow": "Tradeable universe",
        "title": "What ARK holds that you can actually buy",
        "standfirst": (
            "The ARK ETF book reduced to ordinary shares listed on a US exchange. Cash, "
            "the OpenAI private placement, the bitcoin holdcos, foreign local lines and "
            "OTC ADRs are all removed, as is IZRL — its universe trades in Tel Aviv. "
            "Everything below is buyable from a US brokerage account."
        ),
        "tileValue": "Tradeable market value",
        "tileValueNote": "US-listed equities only",
        "tileSymbols": "Symbols",
        "tileSymbolsNote": "across {n} funds",
        "tileMulti": "Held by 2+ funds",
        "tileMultiNote": "{p}% of symbols",
        "tileNearLow": "Near 52-week low",
        "tileNearLowNote": "bottom quarter of range, of {n} quoted",
        "provenance": ("as of {date}  ·  {funds} ETFs after excluding {excl}  ·  "
                       "{n} US-listed symbols  ·  listing status from Nasdaq Trader "
                       "symbol directories"),
    },
    "zh": {
        "eyebrow": "可交易标的",
        "title": "ARK 持仓中你真正买得到的部分",
        "standfirst": (
            "ARK 全部 ETF 持仓筛选后，只保留在美国交易所挂牌的普通股。已剔除现金、"
            "OpenAI 私募份额、比特币 HoldCo、境外本地挂牌股票和场外 ADR，"
            "以及 IZRL——它的成分股在特拉维夫交易所交易。以下每一只都能用美股账户买到。"
        ),
        "tileValue": "可交易市值",
        "tileValueNote": "仅美股上市股票",
        "tileSymbols": "标的数",
        "tileSymbolsNote": "分布于 {n} 只基金",
        "tileMulti": "2 只以上基金持有",
        "tileMultiNote": "占全部标的 {p}%",
        "tileNearLow": "接近 52 周低点",
        "tileNearLowNote": "位于区间下四分之一，共 {n} 只有报价",
        "provenance": ("数据日期 {date}  ·  剔除 {excl} 后剩 {funds} 只 ETF  ·  "
                       "{n} 只美股标的  ·  上市状态来自 Nasdaq Trader 官方代码目录"),
    },
}

FOOTNOTES = {
    "en": [
        ["Listing status is checked, not inferred.",
         "Every symbol is matched against Nasdaq Trader's official directories, which "
         "cover Nasdaq, NYSE, NYSE American, NYSE Arca, Cboe and IEX. CUSIP cannot "
         "answer this — CRISPR carries a Swiss CINS and trades on Nasdaq as CRSP."],
        ["Ticker equality alone is not evidence.",
         "Issuer names must agree too. Airbus trades as AIR in Paris while AIR on the "
         "NYSE is AAR Corp; Titomic is ASX:TTT while TTT is a Treasury ETF. Each quote "
         "is also cross-checked against ARK's own mark to catch what slips through."],
        ["Business descriptions are generated, not sourced from filings.",
         "Each was written by a language model, web-checked for recent listings and "
         "renames, and says what the company sells rather than how it markets itself. "
         "Treat them as orientation, not diligence."],
        ["Sector labels come from Nasdaq and are often wrong.",
         "SpaceX is tagged Computer Software, GE Aerospace is tagged Consumer "
         "Electronics, X-energy is tagged Metal Fabrications. Use the sector filter to "
         "narrow, not to classify — the descriptions are the reliable read."],
        ["Prices are a live quote, not ARK's mark.",
         "Last price and the 52-week range come from Yahoo Finance and are newer than "
         "the holdings file, so market value and price will not reconcile exactly."],
        ["", "Source: ARK's own daily holdings files on assets.ark-funds.com. "
             "Holdings data, not investment advice."],
    ],
    "zh": [
        ["上市状态是逐个核对的，不是推断的。",
         "每个代码都与 Nasdaq Trader 官方目录比对，覆盖 Nasdaq、NYSE、NYSE American、"
         "NYSE Arca、Cboe 和 IEX。CUSIP 判断不了这件事——CRISPR 用的是瑞士 CINS 编码，"
         "却在纳斯达克以 CRSP 交易。"],
        ["代码相同不等于是同一家公司。",
         "发行人名称也必须对得上。空客在巴黎的代码是 AIR，而纽交所的 AIR 是 AAR Corp；"
         "Titomic 是澳交所 TTT，而美股 TTT 是国债 ETF。每条报价还会与 ARK 自己的隐含价"
         "交叉校验，兜住漏网的。"],
        ["公司介绍由模型生成，不是取自财报。",
         "每条都经过联网核实近期上市和更名情况，写的是这家公司卖什么，而不是它如何宣传自己。"
         "请当作快速了解，而非尽职调查。"],
        ["板块标签来自 Nasdaq，错误不少。",
         "SpaceX 被标成「计算机软件」，GE 航空发动机被标成「消费电子」，X-energy 核反应堆"
         "被标成「金属加工」。板块筛选适合粗筛，不适合当分类依据——以公司介绍为准。"],
        ["价格是实时报价，不是 ARK 的估值。",
         "现价和 52 周区间来自 Yahoo Finance，比持仓文件新，所以市值与现价不会精确对得上。"],
        ["", "数据来源：ARK 官方每日持仓文件（assets.ark-funds.com）。"
             "仅为持仓数据，不构成投资建议。"],
    ],
}


# ---- activity feed ----

ACTIVITY = {
    "en": {
        "new": "opened", "buy": "added", "sell": "trimmed", "exit": "closed",
        "search": "Search ticker or company",
        "clear": "Clear filters",
        "filterAction": "Action",
        "filterFund": "Fund",
        "filterConviction": "Agreement",
        "convictionAny": "any",
        "convictionMulti": "2+ funds",
        "convictionHigh": "3+ funds",
        "colDate": "Date", "colAction": "Action", "colTicker": "Ticker",
        "colCompany": "Company", "colShares": "Shares", "colValue": "Value",
        "colFunds": "Funds",
        "status": "{n} of {t} moves  ·  {d} session(s)",
        "empty": "No move matches those filters.",
        "holdings": "Holdings \u2192",
        "leaders": "Top 300 \u2192",
        "fundsWord": "funds",
    },
    "zh": {
        "new": "建仓", "buy": "加仓", "sell": "减仓", "exit": "清仓",
        "search": "搜索代码或公司名",
        "clear": "清除筛选",
        "filterAction": "动作",
        "filterFund": "基金",
        "filterConviction": "一致性",
        "convictionAny": "不限",
        "convictionMulti": "2 只以上",
        "convictionHigh": "3 只以上",
        "colDate": "日期", "colAction": "动作", "colTicker": "代码",
        "colCompany": "公司", "colShares": "股数", "colValue": "金额",
        "colFunds": "基金",
        "status": "{n} / {t} 笔  ·  {d} 个交易日",
        "empty": "没有符合筛选条件的操作。",
        "holdings": "持仓明细 \u2192",
        "leaders": "市值榜 \u2192",
        "fundsWord": "只基金",
    },
}

ACTIVITY_PAGE = {
    "en": {
        "eyebrow": "Trade feed",
        "title": "What ARK actually did",
        "standfirst": (
            "ARK publishes what it holds, never what it traded. These moves are "
            "differenced out of consecutive daily snapshots, with creations and "
            "redemptions divided back out first \u2014 otherwise a day of outflows reads "
            "as the firm selling its entire book. Rows are merged across funds: the "
            "number of funds moving the same way on the same day is the signal."
        ),
        "tileSessions": "Sessions", "tileSessionsNote": "since {first}",
        "tileMoves": "Moves", "tileMovesNote": "merged across funds",
        "tileConviction": "In agreement", "tileConvictionNote": "{n}+ funds, same day, same way",
        "tileOpened": "Opened / closed", "tileOpenedNote": "new and exited positions",
        "provenance": ("{first} to {last}  \u00b7  {days} sessions  \u00b7  {n} moves  \u00b7  "
                       "derived from ARK's daily holdings files"),
    },
    "zh": {
        "eyebrow": "交易流",
        "title": "ARK 实际做了什么",
        "standfirst": (
            "ARK 只公布持仓，从不公布交易。这些操作是从相邻两日快照中差分推导出来的，"
            "并且先把申购赎回的等比缩放除掉了\u2014\u2014否则资金流出的日子会被读成"
            "\u300c把整个组合都卖了\u300d。同一天同方向的操作已跨基金合并："
            "有几只基金同时动手，才是真正的信号。"
        ),
        "tileSessions": "交易日", "tileSessionsNote": "自 {first} 起",
        "tileMoves": "操作数", "tileMovesNote": "已跨基金合并",
        "tileConviction": "一致操作", "tileConvictionNote": "{n} 只以上基金同日同向",
        "tileOpened": "建仓 / 清仓", "tileOpenedNote": "新开与清空的持仓",
        "provenance": ("{first} 至 {last}  \u00b7  {days} 个交易日  \u00b7  {n} 笔操作  \u00b7  "
                       "由 ARK 每日持仓文件差分推导"),
    },
}

ACTIVITY_FOOTNOTES = {
    "en": [
        ["Share counts are differenced, never market value.",
         "Market value moves with price every day whether or not anyone traded."],
        ["Creations and redemptions are divided out first.",
         "Each fund's counts are scaled by the day's flow factor \u2014 the median share "
         "ratio across positions held on both days \u2014 so only active decisions remain. "
         "A position must move more than 0.5% of itself to be counted."],
        ["Dates are trade dates, not file dates.",
         "ARK's file for a day states the portfolio at that day's open, so a change "
         "between two files is the previous session's trading."],
        ["Derived, not published.",
         "Checked against an independent reconstruction over 29 sessions: 81% of "
         "tickers in common, 221 of 222 directions agreeing. Small moves below the "
         "threshold are deliberately dropped."],
        ["", "Source: ARK's own daily holdings files on assets.ark-funds.com. "
             "Holdings data, not investment advice."],
    ],
    "zh": [
        ["差分的是股数，不是市值。",
         "市值每天都随价格变动，跟有没有交易无关。"],
        ["先除掉申购赎回的影响。",
         "每只基金的股数先除以当日流动因子\u2014\u2014两日共同持仓股数比值的中位数"
         "\u2014\u2014剩下的才是主动决策。单个持仓变动需超过自身 0.5% 才计入。"],
        ["日期是交易日，不是文件日期。",
         "ARK 某日的文件反映的是该日开盘时的组合，所以两份文件之间的变化，"
         "是前一个交易日做的交易。"],
        ["这是推导结果，不是官方发布。",
         "与独立重建的数据对比 29 个交易日：代码交集 81%，方向一致 221/222。"
         "低于阈值的小额变动被有意剔除。"],
        ["", "数据来源：ARK 官方每日持仓文件（assets.ark-funds.com）。"
             "仅为持仓数据，不构成投资建议。"],
    ],
}


# ---- market cap leaderboard ----

LEADERS = {
    "en": {
        "board": "The ranking",
        "boardHint": "Click a row for sector, listing vintage and links. Click a column head to sort.",
        "search": "Search ticker or company",
        "clear": "Clear filters",
        "colRank": "#",
        "colMove": "Move",
        "colTicker": "Ticker",
        "colCompany": "Company",
        "colSector": "Sector",
        "colCap": "Market cap",
        "colWeight": "Weight",
        "colYtd": "YTD",
        "colPe": "P/E",
        "colDy": "Yield",
        "colPrice": "Price",
        "colChange": "Change",
        "colRange": "52-week range",
        "colOffHigh": "Off high",
        "colOffLow": "Off low",
        "colArk": "ARK",
        "arkHeld": "held",
        "listed": "listed",
        "listedUnknown": "listing year not reported",
        "wasRanked": "was #{r}",
        "newEntry": "new to the top {n}",
        "arkPosition": "ARK position",
        "dropped": "Dropped out",
        "droppedHint": "In the top {n} on {d}, not today.",
        "status": "{n} of {t} companies  ·  ${v}  ·  {p}% of the leaderboard",
        "empty": "No company matches those filters.",
        "toHoldings": "ARK holdings →",
        "toFeed": "Trade feed →",
    },
    "zh": {
        "board": "榜单",
        "boardHint": "点击某一行查看板块、上市年份和外部链接，点击列头排序。",
        "search": "搜索代码或公司名",
        "clear": "清除筛选",
        "colRank": "排名",
        "colMove": "变化",
        "colTicker": "代码",
        "colCompany": "公司",
        "colSector": "板块",
        "colCap": "市值",
        "colWeight": "权重",
        "colYtd": "年初至今",
        "colPe": "市盈率",
        "colDy": "股息率",
        "colPrice": "现价",
        "colChange": "涨跌",
        "colRange": "52 周区间",
        "colOffHigh": "距高点",
        "colOffLow": "距低点",
        "colArk": "ARK",
        "arkHeld": "持有",
        "listed": "上市于",
        "listedUnknown": "未提供上市年份",
        "wasRanked": "前值第 {r} 名",
        "newEntry": "新进前 {n}",
        "arkPosition": "ARK 持仓",
        "dropped": "跌出榜单",
        "droppedHint": "{d} 时位于前 {n}，今天不在。",
        "status": "{n} / {t} 家  ·  ${v}  ·  占榜单市值 {p}%",
        "empty": "没有符合筛选条件的公司。",
        "toHoldings": "ARK 持仓 →",
        "toFeed": "交易流 →",
    },
}

LEADERS_PAGE = {
    "en": {
        "eyebrow": "Market cap leaderboard",
        "title": "The 300 largest companies on the US market",
        "standfirst": (
            "Every operating company whose shares trade on a US exchange, ranked by "
            "market capitalisation, cut at 300. Where a company is incorporated does not "
            "decide membership — TSMC, ASML and Novo Nordisk are all buyable from a US "
            "brokerage account and all rank here — but it is a filter, so the domestic "
            "list stays one chip away. Nasdaq's screener has no memory, so each day's "
            "ranking is archived here; the movement column is what that archive buys."
        ),
        "tileCap": "Leaderboard market cap",
        "tileCapNote": "{p}% of all {n} US-listed companies",
        "tileCutoff": "Entry threshold",
        "tileCutoffNote": "#300 is {t}",
        "tileTop10": "Top 10 share",
        "tileTop10Note": "of the 300's combined value",
        "tileTurnover": "In / out",
        "tileTurnoverNote": "since {d}",
        "tileArk": "Held by ARK",
        "tileArkNote": "overlap with the ARK book",
        "provenance": ("as of {date}  ·  top {n} of {u} US-listed companies  ·  "
                       "{held} also held by ARK  ·  market caps from the Nasdaq screener"),
    },
    "zh": {
        "eyebrow": "市值榜",
        "title": "美股市值最大的 300 家公司",
        "standfirst": (
            "在美国交易所挂牌交易的经营性公司，按市值排序取前 300 名。"
            "注册地不决定是否入榜——台积电、ASML、诺和诺德都能用美股账户买到，"
            "也都排在榜上——注册地只是一个筛选维度，想只看美国公司点一下就行。"
            "Nasdaq 的筛选器不保留历史，所以每天的排名都在这里存档，"
            "「变化」这一列就是存档换来的东西。"
        ),
        "tileCap": "榜单总市值",
        "tileCapNote": "占全部 {n} 家美股上市公司的 {p}%",
        "tileCutoff": "入榜门槛",
        "tileCutoffNote": "第 300 名是 {t}",
        "tileTop10": "前十占比",
        "tileTop10Note": "占榜单总市值",
        "tileTurnover": "进榜 / 出榜",
        "tileTurnoverNote": "相比 {d}",
        "tileArk": "ARK 持有",
        "tileArkNote": "与 ARK 持仓的重叠",
        "provenance": ("数据日期 {date}  ·  {u} 家美股上市公司中的前 {n} 名  ·  "
                       "其中 {held} 家被 ARK 持有  ·  市值来自 Nasdaq 筛选器"),
    },
}

LEADERS_FOOTNOTES = {
    "en": [
        ["This ranks the US market, not US companies.",
         "Membership is decided by where the shares trade, not by where the issuer is "
         "incorporated: TSMC ranks sixth and SK hynix thirteenth, and ASML, Alibaba, "
         "Shell, Arm, Sony, PDD and the Canadian banks all rank. Domicile is a filter "
         "instead — one chip narrows the board to US-incorporated issuers, which is a "
         "different and smaller list. Most foreign issuers trade here as ADRs, which "
         "the ranking counts as the company they represent."],
        ["Dual-class lines are collapsed by hand, not by rule.",
         "Nasdaq reports Alphabet's whole market cap against both GOOG and GOOGL, and "
         "Berkshire's against both BRK.A and BRK.B — summing them would invent a "
         "company and shift every rank below it. Fox and News Corp are the other kind, "
         "each class carrying its own cap, and are left alone. The build fails if a new "
         "pair appears rather than counting it twice."],
        ["Market cap moves with the price, so the ranking is a daily snapshot.",
         "Neighbouring ranks are usually within a few percent of each other, which means "
         "the exact ordering in the middle of the list is noise. Read the tiers, not the "
         "individual positions."],
        ["Sector labels come from Nasdaq and are often wrong.",
         "SpaceX is tagged Computer Software, GE Aerospace is tagged Consumer "
         "Electronics. Useful for narrowing the list, not for classifying it."],
        ["Companies with no reported market cap are absent, not zero.",
         "Around 330 listings — almost all 2025-26 SPACs — return a blank cap "
         "from the screener. None are anywhere near the threshold."],
        ["Two sources, cross-checked, neither overwritten.",
         "The ranking and market caps come from Nasdaq; year-to-date, trailing P/E "
         "and dividend yield from Xueqiu's US screener. Both price the same security "
         "at the same last sale, so a disagreement about market cap is a disagreement "
         "about share count — which is what an ADR ratio makes hard. Ferrari is 33% "
         "high here, Toyota 21%; Petrobras differs because Nasdaq counts the preferred "
         "class and Xueqiu does not. Flagged, never silently corrected."],
        ["Membership is not taken from the second source.",
         "Xueqiu's ranking still lists RDS.A, ANTM, BK, STO, MMC and MTU beside the "
         "renamed lines that replaced them, so six companies appear twice in its top "
         "300 and twelve real ones are pushed out. Nasdaq Trader's symbol directory "
         "decides what is listed."],
        ["A blank P/E or yield is a fact, not a gap.",
         "No trailing P/E means the company lost money over the last twelve months; "
         "no yield means it pays no dividend."],
        ["", "Sources: Nasdaq's stock screener and Xueqiu, archived daily. "
             "Market data, not investment advice."],
    ],
    "zh": [
        ["这份榜单排的是美股市场，不是美国公司。",
         "决定是否入榜的是股票在哪里交易，而不是公司在哪里注册：台积电排第六、SK 海力士第十三，"
         "ASML、阿里巴巴、壳牌、Arm、索尼、拼多多和加拿大的几家银行也都在榜上。注册地改成了筛选维度——点一下就能把榜单收窄成「在美国注册的公司」，那是另一份更短的名单。"
         "多数外国公司以 ADR 形式在美股交易，榜单把 ADR 计为它所代表的那家公司。"],
        ["双重股权是逐个手工归并的，不是靠规则。",
         "Nasdaq 把 Alphabet 的整家公司市值同时挂在 GOOG 和 GOOGL 两条线上，"
         "Berkshire 的 BRK.A 和 BRK.B 也一样——两条相加会凭空造出一家公司，"
         "并把它下面所有排名整体挪一位。Fox 和 News Corp 属于另一种，每个类别各报各的，"
         "不作归并。如果出现新的配对，构建会直接失败，而不是默默重复计算。"],
        ["市值随股价波动，所以排名只是当日快照。",
         "相邻名次之间通常只差百分之几，也就是说榜单中段的具体顺序是噪音。"
         "看档位，不要看单个名次。"],
        ["板块标签来自 Nasdaq，错误不少。",
         "SpaceX 被标成「计算机软件」，GE 航空发动机被标成「消费电子」。"
         "适合用来缩小范围，不适合当分类依据。"],
        ["没有市值数据的公司是缺失，不是零。",
         "约 330 只标的——几乎全是 2025-26 年的 SPAC 壳——"
         "在数据源里市值为空，没有一只接近入榜门槛。"],
        ["两个数据源交叉校验，互不覆盖。",
         "排名和市值来自 Nasdaq，年初至今、市盈率和股息率来自雪球美股筛选器。"
         "两边对同一只股票的现价完全一致，所以市值上的分歧本质是股数分歧"
         "——而股数正是 ADR 折算比例最容易搞错的地方。法拉利这里高了 33%，丰田高了 21%；"
         "巴西石油的差异是口径不同，Nasdaq 计入了优先股而雪球没有。只标注，不做静默修正。"],
        ["成分名单不采用第二个数据源。",
         "雪球的榜单里仍然挂着 RDS.A、ANTM、BK、STO、MMC、MTU 这些已被改名代码取代的旧代码，"
         "导致六家公司在它的前 300 里出现两次，挤掉十二家真实公司。"
         "以 Nasdaq Trader 官方代码目录为准。"],
        ["市盈率或股息率为空是事实，不是缺数据。",
         "没有市盈率意味着这家公司过去十二个月是亏损的；没有股息率意味着它不分红。"],
        ["", "数据来源：Nasdaq 股票筛选器与雪球，每日存档。"
             "仅为市场数据，不构成投资建议。"],
    ],
}


# ---- shared navigation ----

# One nav for every page, so a new page is added here and appears on all of
# them. Keys match the file each entry points at.
NAV = {
    "en": {
        "index": "Today", "holdings": "Holdings", "activity": "Trades",
        "leaders": "Top 300", "archive": "Archive",
    },
    "zh": {
        "index": "今日", "holdings": "持仓", "activity": "交易",
        "leaders": "市值榜", "archive": "存档",
    },
}


# ---- home ----

# Labels for the freshness strip. Keyed by the source keys in home.SOURCES.
SOURCES = {
    "en": {
        "holdings": "ARK holdings", "trades": "Trades", "quotes": "Quotes",
        "leaders": "Market cap", "financials": "Financials", "venture": "ARKVX",
    },
    "zh": {
        "holdings": "ARK 持仓", "trades": "交易", "quotes": "报价",
        "leaders": "市值榜", "financials": "财报", "venture": "ARKVX 创投",
    },
}

HOME = {
    "en": {
        "sources": "Data on file",
        "sourcesHint": "Every source overwrites in place at origin. These are the "
                       "newest copies archived here, and how far behind they are.",
        "ok": "current", "late": "late", "stale": "stale", "missing": "missing",
        "sessionBehind": "1 session behind",
        "sessionsBehind": "{n} sessions behind",
        "dayBehind": "1 day old",
        "daysBehind": "{n} days old",
        "never": "never fetched",
        "moves": "What ARK did",
        "movesHint": "Newest session, merged across funds. Agreement first.",
        "movesTally": "{new} opened · {buy} added · {sell} trimmed · {exit} closed",
        "movesMore": "all {n} moves →",
        "movesAgree": "{n} funds",
        "book": "The book",
        "bookHint": "US-listed equities only, the part you can actually buy.",
        "bookAll": "all holdings →",
        "bookSymbols": "symbols",
        "bookSince": "vs {d}",
        "bookAdded": "+{n} new", "bookRemoved": "−{n} gone",
        "leaders": "Top of the market",
        "leadersHint": "Rank movement since the previous snapshot.",
        "leadersAll": "full ranking →",
        "leadersFirst": "First snapshot on file — movement starts with the next one.",
        "leadersIn": "in", "leadersOut": "out", "leadersHeld": "{n} held by ARK",
        "leadersCutoff": "entry at ${v}B",
        "next": "Not wired up yet",
        "nextHint": "Collected or planned, but not yet on a page.",
        "empty": "Nothing on file yet.",
        "arkHeld": "ARK holds",
    },
    "zh": {
        "sources": "已存档的数据",
        "sourcesHint": "每个数据源在原站点都是就地覆盖、不留历史。这里是本地存档的最新副本，"
                       "以及它落后了多久。",
        "ok": "最新", "late": "偏旧", "stale": "过期", "missing": "缺失",
        "sessionBehind": "落后 1 个交易日",
        "sessionsBehind": "落后 {n} 个交易日",
        "dayBehind": "1 天前",
        "daysBehind": "{n} 天前",
        "never": "从未抓取",
        "moves": "ARK 今天做了什么",
        "movesHint": "最近一个交易日，跨基金合并，按一致性排序。",
        "movesTally": "建仓 {new} · 加仓 {buy} · 减仓 {sell} · 清仓 {exit}",
        "movesMore": "查看全部 {n} 笔 →",
        "movesAgree": "{n} 只基金",
        "book": "持仓全景",
        "bookHint": "仅美股上市普通股，也就是你真正买得到的部分。",
        "bookAll": "查看全部持仓 →",
        "bookSymbols": "只标的",
        "bookSince": "相比 {d}",
        "bookAdded": "新增 {n}", "bookRemoved": "移出 {n}",
        "leaders": "市场最前排",
        "leadersHint": "相比上一份快照的排名变化。",
        "leadersAll": "查看完整榜单 →",
        "leadersFirst": "这是第一份快照——排名变化从下一份开始有。",
        "leadersIn": "进榜", "leadersOut": "出榜", "leadersHeld": "{n} 家被 ARK 持有",
        "leadersCutoff": "入榜门槛 ${v}B",
        "next": "尚未接入",
        "nextHint": "已经在采集或已列入计划，但还没有对应页面。",
        "empty": "还没有数据。",
        "arkHeld": "ARK 持有",
    },
}

HOME_PAGE = {
    "en": {
        "eyebrow": "Daily brief",
        "title": "What moved, and whether the data is any good",
        "standfirst": (
            "One screen answering two questions before anything else: what ARK did in "
            "the last session, and whether every feed behind these pages actually "
            "updated. A stale source is indistinguishable from a quiet market until "
            "someone checks, so the check goes first."
        ),
        "provenance": "holdings {holdings}  ·  ranking {leaders}  ·  {n} sessions archived",
    },
    "zh": {
        "eyebrow": "每日简报",
        "title": "今天发生了什么，以及数据本身还可不可信",
        "standfirst": (
            "一屏之内先回答两个问题：ARK 在最近一个交易日做了什么，"
            "以及这些页面背后的每一路数据到底有没有更新。"
            "在有人核对之前，数据源不动和市场没动看起来一模一样——所以核对放在最前面。"
        ),
        "provenance": "持仓 {holdings}  ·  榜单 {leaders}  ·  已存档 {n} 个交易日",
    },
}

HOME_FOOTNOTES = {
    "en": [
        ["Freshness is counted in sessions, not clock time.",
         "A Friday file read on Sunday is current, not two days late. Market holidays "
         "are not modelled, so the day after one reads as a session behind — the "
         "error points at looking, which is the safe direction."],
        ["Agreement is the ranking, not size.",
         "Four funds adding the same name on the same day is the firm agreeing with "
         "itself; one fund moving twice the shares is a rebalance. The moves list "
         "sorts on the number of funds first for that reason."],
        ["", "Sources: ARK's daily holdings files, Nasdaq's screener, Yahoo quotes, "
             "SEC XBRL. Holdings data, not investment advice."],
    ],
    "zh": [
        ["新鲜度按交易日计算，不按自然日。",
         "周五的文件在周日看仍然是最新的，不算落后两天。节假日没有建模，"
         "所以长假之后会显示落后一个交易日——这个误差指向「去看一眼」，方向是安全的。"],
        ["排序看的是一致性，不是金额。",
         "四只基金在同一天买同一个标的，是这家公司在跟自己达成一致；"
         "一只基金买了两倍的股数，多半只是再平衡。所以动作列表先按参与基金数排序。"],
        ["", "数据来源：ARK 每日持仓文件、Nasdaq 筛选器、Yahoo 报价、SEC XBRL。"
             "仅为持仓数据，不构成投资建议。"],
    ],
}


# What the home page's last card lists: collected or planned, no page yet.
# Kept as copy rather than derived from the modules, because "exists but is
# not shown" is a judgement about the site, not a fact about the code.
HOME_NEXT = {
    "en": [
        ["13F managers", "thirteenf.py ingests a filer's quarterly positions into the "
                         "same schema as ARK's. No comparison page yet."],
        ["Company financials", "Revenue, margin, cash and runway are pulled from SEC "
                               "XBRL and cached. The detail panel that shows them is "
                               "switched off."],
        ["Watchlist", "Nothing here follows what you own or want to own. That is the "
                      "next thing worth having."],
    ],
    "zh": [
        ["13F 管理人", "thirteenf.py 已能把某位管理人的季度持仓抓成与 ARK 相同的表结构，"
                       "但还没有对比页面。"],
        ["公司财务", "营收、毛利率、现金和续航月数已从 SEC XBRL 抓取并缓存，"
                     "展示它们的详情面板还没有打开。"],
        ["关注列表", "目前没有任何一页跟踪你自己持有或想持有的标的。这是下一个值得做的东西。"],
    ],
}
