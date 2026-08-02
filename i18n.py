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
