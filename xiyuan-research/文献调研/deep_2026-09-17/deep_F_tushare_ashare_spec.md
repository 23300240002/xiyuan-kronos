# Deep Research F · Tushare 数据字典与 A 股时段语义规范（2026-09-17）

> 用途：为「Tushare Pro → 本地 parquet 快照 → `scripts/hf_data_pipeline.py`」建立唯一的字段契约与时刻语义规范。
> 前提：真实数据由用户本机（满积分）自行拉取，**项目侧不接触 token**，只读本地快照。因此本文的交付物是"采集契约 + 映射表"，不是采集代码。
> 引用规则：Tushare 官方文档/交易所规则原文以「」逐字标注（每条 ≤3 行）并注明页面；社区/镜像来源一律标 **[二手]**。

---

## 0. 方法（抓了哪些官方文档页）

**Tushare Pro 官方页面（web_fetch 直读，逐字照录）**

| 页面 | 内容 |
|---|---|
| `document/2?doc_id=370` | 股票历史分钟 `stk_mins`（含数据样例，本任务最关键页面） |
| `document/2?doc_id=419` | 指数历史分钟 `idx_mins`（同族口径的第二份官方样例） |
| `document/2?doc_id=374` / `457` | 实时分钟 `rt_min` / A股实时分钟-日累计 `rt_min_daily`（官方样例含 2026-04-15 实盘 bar） |
| `document/2?doc_id=372` | A股实时日线 `rt_k`（唯一带盘口字段的 A股实时接口） |
| `document/2?doc_id=109` | 通用行情接口 `pro_bar`（复权口径、http 不可用声明） |
| `document/1?doc_id=234` | 《如何获取分钟数据》（分钟权限与积分脱钩的官方声明、更新时间） |
| `document/1?doc_id=290` | 权限说明（积分×每分钟频次表、单独开权限价格表） |
| `document/2?doc_id=27` / `26` / `214` / `25` / `183` | `daily` / `trade_cal` / `suspend_d` / `stock_basic` / `stk_limit` |
| `document/2?doc_id=353` / `354` / `369` | `stk_auction_o` / `stk_auction_c` / `stk_auction`（三个集合竞价接口） |
| `document/2?doc_id=340` / `314` | 期货实时分钟 `rt_fut_min`（websocket 声明）/ 期货历史 Tick（非 API 交付） |
| `document/1?doc_id=130` | 《通过HTTP调取数据》（拉取式协议的官方说明） |
| 上述页面左侧导航 | 用于穷举「股票数据 → 行情数据」全部子接口清单（判定"有无 L2/逐笔"的否证依据） |

**交易所规则/官方发布（直读或经检索代理全文读取）**：上交所 2018-08-06 新闻稿（直读）、上证发〔2018〕59号规则修订条款、《深圳证券交易所交易规则》2018-03 版 PDF（docs.static.szse.cn）、《北京证券交易所交易规则》（北证公告〔2026〕17号，2026-07-06 施行）、上交所交易规则（2026年修订，上证发〔2026〕41号）、新华社 2026-07-06 盘后固定价格交易扩围报道。

**开源 SDK 源码**：`github.com/waditu/tushare` `tushare/__init__.py`、`tushare/stock/trading.py`（旧版 tick/quotes 系函数与 docstring）。

**二手来源（镜像/社区，仅作辅证并显式标注）**：掘金 `juejin.cn/post/7662159251481395242`、腾讯云开发者社区 `developer.cloud.tencent.com/article/2709162`、CSDN `blog.csdn.net/xiaogoumaogou/article/details/162876627`、知乎专栏 `zhuanlan.zhihu.com/p/2078808920374632999`、`github.com/DreamCats/tushare-cli/docs/api-catalog.md`（全量接口目录，用于否证）。

**文献**：Han et al. (2022, *PBFJ* 74)、Gu et al. (2010, *Physica A* 389(2):278–286)、Suen (2022, *JFM*)、Li (2021, *Quantitative Finance*)、Zhang/Jiang/Zhou (2021, *Accounting & Finance*)、Peng (2024, *PBFJ* 88)、López de Prado (2018)。

**本项目代码基线**：`scripts/hf_data_pipeline.py`（契约来源）、`research/scripts/kronos_context_adapter.py`、`KronosLocal/deps/Kronos/finetune_csv/finetune_base_model.py`（时间特征清单）。

---

## 1. 端点档案（字段 / 时间戳语义 / 更新时效 / 频率上限）

### 1.0 先决事实：满积分 ≠ 分钟权限（采购口径）

- 「Tushare Pro提供了全市场各类资产交易的分钟数据。但由于数据量庞大……目前各类分钟是分别单独开权限的，**跟平台积分没有关系**」（doc_id=234）
- 「此外，**分钟和港美股数据权限不在积分范畴内**，各类分钟单独分别开权限，且不加积分。」（doc_id=290）
- 「对于分钟数据有600积分用户可以**试用（请求2次）**」（doc_id=109）

| 数据类 | 权限形式 | 官方标价（个人/年或月） | 频次上限 |
|---|---|---|---|
| `daily`/`trade_cal`/`suspend_d`/`stock_basic`/`stk_limit` 等常规 | 积分门槛 | 2000 积分≈200 元/年 | 见下表 |
| `stk_mins`（1/5/15/30/60min，2009 起） | **单独开权限** | **单独 2000 元/年** | 每分钟 500 次、每次 8000 行、每天 30 万频次（24h 滚动窗口） |
| `rt_min` / `rt_min_daily`（盘中分钟） | 单独开权限 | 1000 元/月 | 每分钟 500 次，「单次可同时请求300个公司」 |
| `rt_k`（实时日线，含一档盘口） | 单独开权限 | 200 元/月 | 每分钟 50 次，每次可提取全市场 |
| `stk_auction_o` / `stk_auction_c` / `stk_auction` | 单独开权限 | 500 元/年 | 每分钟 500 次，总量不限制 |
| 积分档位（doc_id=290 表一） | 120→50 次/分、8000 次/天；2000+→200 次/分、10 万次/天/个 API；**5000+→500 次/分、常规数据无上限**；10000+→500 次/分（特色数据 300 次/分）；15000+→特色数据无总量 | | |
| 机构价 | 「如果是公司机构，费用为个人的10倍。」 | | |

> **结论**：本项目若要用 `stk_mins`，除满积分外**必须另购"历史分钟"权限**；`ticks`/L2 无论多少积分都没有（见 §1.4、§3.4）。

### 1.1 `stk_mins` — 股票历史分钟（doc_id=370）

- 官方限量原文：「单次最大8000行数据，每分钟500频次，每天的总量是30万频次，窗口24小时滚动刷新。可以通过股票代码和时间循环获取，本接口可以提供超过10年历史分钟数据」
- 官方描述：「获取A股分钟数据，支持1min/5min/15min/30min/60min行情，提供Python SDK和 http Restful API两种方式」
- 时效：「数据每天收盘后处理更新，时间在17~21点之间完成」（doc_id=234）→ **日终批处理数据，盘中不可得**
- 单标的限制：「目前只能一个个标的按时间段获取分钟」（doc_id=234）→ 每次调用一只股票；多代码逗号在 `stk_mins` 官方参数说明中**未声明支持**（`rt_min` 才明确「支持逗号分隔的多个代码同时提取」）
- 参数语义陷阱：「如是end_date输入的是不带时分秒的日期，返回的数据不包括end_date当日，即数据返回的是 < end_date的数据」（doc_id=234）→ 采集必须显式带 `HH:MM:SS`

| 字段 | 类型 | 官方描述 | 语义 |
|---|---|---|---|
| `ts_code` | str | 股票代码 | 带 `.SH/.SZ/.BJ` 后缀 |
| `trade_time` | **str** | 交易时间 | **bar 右端点（= bar_end）**，`YYYY-MM-DD HH:MM:SS`，时区-naive 北京时 |
| `open/close/high/low` | float | 开盘价/收盘价/最高价/最低价 | 未复权 |
| `vol` | **int** | 成交量**(股)** | 单位=股（**注意：`daily.vol` 单位=手**） |
| `amount` | float | 成交金额（元） | 单位=元（`daily.amount` 单位=千元） |

**官方样例（doc_id=370，600000.SH，2023-08-25，1min，行号 0…240 = 241 根）关键字段事实**：
- 末行 `09:30:00  close 6.99 open 6.99 high 6.99 low 6.99 vol 103700` → 四价合一 + 有量 ⇒ **开盘集合竞价单独占一根 09:30:00 bar**
- `09:31:00  open 6.99 close 7.02 high 7.02 low 6.97 vol 807500` → 第一根连续竞价 bar，量远大于竞价 bar
- `14:59:00 vol 0.0`、`14:58:00 vol 0.0`、`14:57:00 vol 51800`、`15:00:00 vol 235500` ⇒ 14:57–15:00 无连续成交，**收盘集合竞价撮合量落在 15:00:00 这一根**；且**无成交的分钟仍会下发 vol=0 的 bar**
- 全天 241 根 = 09:30(竞价) + 09:31–11:30(120) + 13:01–15:00(120)，**不存在 11:31–13:00 与 13:00:00 的 bar**
- 指数同族接口 `idx_mins`（doc_id=419）官方样例结构一致（09:30:00 四价合一，14:59:00 vol 0.0）
- 盘中接口 `rt_min_daily`（doc_id=457，2026-04-15 样例）同样以 `09:30:00  10.05 10.05 10.05 10.05 vol 133400` 开头 ⇒ 实时链路与历史链路 bar 网格一致

### 1.2 `daily` / `trade_cal` / `suspend_d` / `stock_basic` / `stk_limit`（对照与元数据侧）

| 端点 | doc | 时间戳语义 | 更新时效（官方原文） | 频率/限量（官方原文） |
|---|---|---|---|---|
| `daily` | 27 | `trade_date`（日粒度，无时刻） | 「交易日每天15点～16点之间入库」 | 「基础积分每分钟内可调取500次，每次6000条数据，一次请求相当于提取一个股票23年历史」 |
| `trade_cal` | 26 | `cal_date` + `pretrade_date` | 页面未标注（静态字典类） | 「需2000积分」 |
| `suspend_d` | 214 | `trade_date` + `suspend_timing`（日内停牌时间段） | 「不定期」 | 「至少需要2000积分 可以调用，5000积分可以获得更高的频次」 |
| `stock_basic` | 25 | `list_date` / `delist_date` | 页面未标注 | 「每次最多返回6000行数据（覆盖全市场A股，会随股票总数增长而增加）」「2000积分起，每分钟请求50次」 |
| `stk_limit` | 183 | `trade_date` | 「每个交易日9点左右更新当日股票涨跌停价格」 | 「单次最多提取5800条记录，可循环调取，总量不限制」 |

`daily` 关键字段：`pre_close`「昨收价【除权价】」、`pct_chg`「基于除权后的昨收计算的涨跌幅」、`vol`「成交量 （手）」、`amount`「成交额 （千元）」、**`ah_vol`「盘后成交量（手）」/`ah_amount`「盘后成交额（千元）」（默认不显示）**。
`daily` 官方声明：**「本接口是未复权行情，停牌期间不提供数据」**。
`trade_cal` 官方声明：「获取各大交易所交易日历数据,默认提取的是上交所。三大交易所的交易日历都是一样的，北交所交易日历参考上交所和深交所。」输入 `is_open`「'0'休市 '1'交易」，输出含 `pretrade_date`「上一个交易日」。
`suspend_d` 字段：`suspend_type`「S-停牌，R-复牌」、`suspend_timing`「日内停牌时间段（日内停牌才有值，否则为空值）」、`trade_date`「停复牌日期（覆盖从停牌到覆盖期间的连续日期）」。

### 1.3 集合竞价三接口（本项目"竞价 bar 是否可信"的交叉验证源）

| 端点 | doc | 官方描述 | 时效 | 字段 |
|---|---|---|---|---|
| `stk_auction_o` | 353 | 「股票开盘9:30集合竞价数据，每天盘后更新」 | **盘后** | `close/open/high/low`（开盘集合竞价四价）、`vol`、`amount`、`vwap`；单次最大 10000 行，可按日期循环 |
| `stk_auction_c` | 354 | 「股票收盘15:00集合竞价数据，每天盘后更新」 | **盘后** | 同上口径（收盘集合竞价）；单次最大 10000 行 |
| `stk_auction` | 369 | 「获取当日个股和ETF的集合竞价成交情况，**每天9点26~29分之间可以获取当日的集合竞价成交数据**。本接口历史数据开始于2025年1月。」 | **盘中 09:26–09:29 可得** | `vol`（成交量-股）、`price`（成交均价）、`amount`、`pre_close`、`turnover_rate`、`volume_ratio`、`float_share`；单次最大 8000 行 |

**官方样例中的市场差异（重要，直接可辨竞价 bar 归属）**：`stk_auction_o` 样例里 `.SH` 行 `open=high=low=close`（如 600938.SH 26.54/26.54），而 `.SZ` 行 `open≠close`（如 300504.SZ open 16.97 / close 16.80、300592.SZ 14.34/14.27）⇒ **沪市竞价只揭示最终撮合一价，深市竞价窗口内存在多价路径（虚拟参考价）**。这是官方样例事实，机理见 §2（SSE 交易规则 5.2.1 揭示虚拟参考价格/虚拟匹配量/虚拟未匹配量）。
`stk_auction_c` 样例同时含 `.SH`（603102.SH、600502.SH）与 `.SZ`（300504.SZ、300657.SZ）且量级可观 ⇒ **深市收盘集合竞价确实存在且有独立数据**（另见 §3.3）。
注：ETF 的竞价/涨跌停已从 `stk_auction`/`stk_limit` 拆出至 `etf_auction`（doc 493）与 `etf_limit`（doc 491）。

### 1.4 盘中可得性与盘口：`rt_min` / `rt_min_daily` / `rt_k`

- `rt_min`（374）：「获取全A股票实时分钟数据，包括1~60min」「单次最大1000行数据，可以通过股票代码提取数据，支持逗号分隔的多个代码同时提取」；freq 用**大写** `1MIN/5MIN/…`。
- `rt_min_daily`（457）：「获取A股当日盘中历史分钟数据，可以提取单只股票当日开盘以来的所有分钟数据」「开通了实时分钟权限自动获得本接口权限」。
- `rt_k`（372）：「获取实时日k线行情，支持按股票代码及股票代码通配符一次性提取全部股票实时日k线行情」「单次最大可提取6000条数据，等同于一次提取全市场」；输出含 `num`「开盘以来成交笔数」与 **一档盘口** `ask_price1/ask_volume1/bid_price1/bid_volume1` + `trade_time`；权限表标注「每天9点半开始」「每分钟50次，每次可以提取全市场」。
- **A股盘口档位结论：Tushare Pro 侧最高只有 1 档（`rt_k`），没有任何多档 L2 快照接口。**

### 1.5 `ticks` / `order` / `transaction`：在 Tushare Pro 中不存在（否证）

三条独立否证：
1. **官方左侧导航穷举**（从 doc_id=370/314/354 页面原文渲染出的「股票数据 → 行情数据」完整子菜单）只有：历史日线(27)、历史分钟(370)、周线(144)、月线(145)、复权行情(146)、周/月线(每日更新)(336/365)、复权因子(28)、每日指标(32)、通用行情接口(109)、每日涨跌停价格(183)、每日停复牌信息(214)、沪深股通十大成交股(48)、备用行情(255)。**无 tick / 逐笔 / 委托 / L2 / 盘口 任何一项。**「特色数据」子菜单亦无（292/293/294/296/328/353/354/364/399/275/267）。
2. **doc_id=290「单独开权限」表**穷举了分钟/实时/资讯/公告/集合竞价等 20 余类，**无 A股 L2 或逐笔条目**。
3. **全市场唯一的 Tick 级产品是期货，且不走 API**：「获取全市场期货合约的Tick高频行情，**当前不提供API方式获取，只提供csv网盘交付**……tick行情属于单独的数据服务内容，**不在积分权限范畴**」（doc_id=314）。其字段为 `InstrumentID / BidPrice1 / BidVolume1 / AskPrice1 / AskVolume1 / LastPrice / Volume / Turnover / OpenInterest / UpperLimitPrice / LowerLimitPrice / OpenPrice / PreSettlementPrice / PreClosePrice / PreOpenInterest / TradingDay / UpdateTime`（`UpdateTime` 样例 `10:00:00.500`，带毫秒；`Volume` 为快照累计口径）——**这是期货语义，与 A股无关，且不可编程拉取**。

**旧版（非 Pro）SDK 里的 tick 系函数**（`github.com/waditu/tushare` `tushare/stock/trading.py`，仅作文献性记录，**不得作为本项目数据源**）：
- `tick(code, conn, date, asset, market)` docstring：「Return … date, time, price, vol, **type:买卖方向，0-买入 1-卖出 2-集合竞价成交**」——逐笔**买卖方向与"竞价成交"标志**在这一层才有；且需要 `conn=ts.api()/ts.xpi()`（本地行情终端连接），分页「每次 300 条、最多循环 200 次」。
- `get_tick_data(code, date, src='sn'|'tt'|'nt')`：「获取分笔数据」，属性「成交时间、成交价格、价格变动，成交手、成交金额(元)，买卖类型」，数据源为新浪/腾讯/网易公开页面。
- `get_realtime_quotes(symbols)`：新浪源，「DataFrame 实时交易数据…bid，竞买价，即"买一"报价…b1_v，委买一（笔数 bid volume）…b5_v，"买五"…a1_v，委卖一…」→ 网页源五档快照，`volumn` 为**当日累计**（docstring 注「maybe you need do volumn/100」）。
- 任务书中提到的「`ticks` 每交易日每只 500 点」这一约束，**在 Tushare Pro 官方文档内找不到任何对应接口**（[二手] 该量级描述更接近新浪/腾讯网页分笔接口的截断行为，或第三方 L2 目录）。列入 §7 未核实项。

### 1.6 拉取式核实：无 websocket / 无流式推送（A股侧）

- 「Tushare HTTP数据获取的方式，我们采用了post的机制，通过提交JSON body参数，就可以获得您想要的数据」；请求参数为 `api_name / token / params / fields`，返回 `code / msg / data(fields+items)`（doc_id=130）。
- 「其实Tushare Pro新版的SDK，正是利用http方式来获取数据的，虽然我们也提供了tcp的方式」（doc_id=130）——该 "tcp" 是 SDK 内 `req_zmq_api` 的**请求/响应**通道（`if self.__protocol == 'tcp': self.req_zmq_api(req_params)`），**不是订阅推送**。
- **官方唯一出现 websocket 的地方是期货**：「获取全市场期货合约实时分钟数据…提供Python SDK、 http Restful API和**websocket**三种方式」（doc_id=340，`rt_fut_min`；权限表亦标「期货实时分钟 … 支持SDK/HTTP/WebSocket」）。**A股分钟/日线接口（`stk_mins`/`rt_min`/`rt_min_daily`/`rt_k`）官方原文只写「Python SDK和 http Restful API两种方式」（doc_id=370/419），无 websocket。**
- 「由于本接口是集成接口，在SDK层做了一些逻辑处理，**目前暂时没法用http的方式调取通用行情接口**」（doc_id=109，指 `pro_bar`）→ `pro_bar` 是 SDK 现算封装（含均线/换手/动态复权），**采集层应绕开 `pro_bar`，直接落 `stk_mins`+`adj_factor`**，理由见 §4-D7。
- 第三方全量接口目录交叉核对：「No interface is named "ticks"… no interface in this catalog contains "L2"… The word "websocket", "WebSocket", "streaming", or "流式" does not appear anywhere in this catalog.」[二手]（`github.com/DreamCats/tushare-cli/docs/api-catalog.md`）。

**「实时行情」产品归属判定**：`rt_k`（实时日线，200/月）、`rt_min`/`rt_min_daily`（实时分钟，1000/月）、`rt_min` 类是**"拉取式伪实时"**（每分钟 50/500 次轮询，无事件流、无快照序号、无交易方向标志）。它们**属于集成范围，但只作为"当日补拉/盘前对账"用途**，不得作为高频事件源（详见 §4-D1、§6.5）。

---

## 2. A 股时段语义（精确时间线 + 各端点数据表现）

### 2.1 官方时段边界（三市一致的股票口径）

| 时刻 | 阶段 | 规则原文（逐字，节选） | 出处 |
|---|---|---|---|
| 09:15–09:25 | 开盘集合竞价（可申报） | 「每个交易日的9:15至9:25为开盘集合竞价时间，9:30至11:30、13:00至14:57为连续竞价时间，**14:57至15:00为收盘集合竞价时间**。」 | SSE 交易规则 2.4.2；SZSE 交易规则 2.4.2（「9︰15至9︰25…13︰00至14︰57为连续竞价时间，14︰57至15︰00为收盘集合竞价时间」）；BSE 交易规则 2.3.2（同句式） |
| 09:20–09:25 | 开盘竞价后半段：**不可撤单** | 「每个交易日9:20至9:25的开盘集合竞价阶段、**14:57至15:00的收盘集合竞价阶段，本所交易主机不接受撤单申报**」 | SSE 3.4.1；SZSE 3.3.1；BSE 3.3.1 |
| 09:25 | 一次性集中撮合，产生开盘价 | 「集合竞价是指对一段时间内接受的买卖申报**一次性集中撮合**的竞价方式。」 | BSE 3.4.1（定义，沪深同） |
| 09:25–09:30 | **申报空窗**（交易主机不受理竞价申报） | 「本所接受交易参与人竞价交易申报的时间为每个交易日**9:15至9:25、9:30至11:30、13:00至15:00**。」 | SZSE 3.3.1 / BSE 3.3.1（沪市同构） |
| 09:30–11:30 | 上午连续竞价 | 同上 2.4.2 | — |
| 11:30–13:00 | **午休（无撮合、无行情）** | — | — |
| 13:00–14:57 | 下午连续竞价 | 同上 2.4.2 | — |
| 14:57–15:00 | **收盘集合竞价（沪深北三市均有）** | 「股票交易的收盘价产生方式调整为通过收盘集合竞价产生。收盘集合竞价的时间为14:57至15:00。收盘集合竞价阶段可以申报，不可撤单。行情揭示同开盘集合竞价。」 | 上交所 2018-08-06 新闻稿（自 **2018-08-20** 起实施）；SZSE 2.4.2；BSE 2.3.2 |
| 15:00 | 收盘价产生 | 「证券的收盘价通过集合竞价的方式产生。收盘集合竞价不能产生收盘价或未进行收盘集合竞价的，以当日该证券最后一笔交易前一分钟所有交易的成交量加权平均价（含最后一笔交易）为收盘价。」 | SSE 4.1.3 / SZSE 4.2.3；北交所 4.1.2 改为「以当日该证券竞价交易**最后一笔成交价**为收盘价」 |
| 竞价期间的行情揭示 | 只揭示虚拟价/虚拟量 | 「即时行情内容包括：证券代码、证券简称、前收盘价格、**集合竞价虚拟参考价格、虚拟匹配量和虚拟未匹配量**。」 | SSE 5.2.1 |
| 15:05–15:30 | **盘后固定价格交易**（2026-07-06 起扩至全部 A股+ETF，北交所暂不实施） | 「自7月6日起，盘后固定价格交易方式适用证券范围由科创板、创业板股票扩展至全部A股和ETF，**每个交易日的15:05至15:30为盘后固定价格交易时间**。」申报时间「沪市A股与ETF…9:30至11:30、13:00至15:30；深市A股与ETF、北交所股票则为9:15至11:30、13:00至15:30」 | 新华社 2026-07-06；SSE/SZSE/BSE 交易规则（2026 修订，2026-07-06 施行；BSE 3.7.1–3.7.10 施行日期另行通知） |

### 2.2 各端点在时段上的数据表现（官方样例证据）

| 时段 | `stk_mins` / `idx_mins` / `rt_min_daily` 表现 | 证据 |
|---|---|---|
| 09:15–09:25（竞价过程） | **完全静默**：无任何 09:15–09:29 的 bar | 官方样例首行即 09:30:00（doc 370/419/457）；[二手] 知乎实测「9:15–9:25 竞价窗口内，公开分钟接口是"静默"的」 |
| 09:30（竞价结果公布） | 出现**一根 09:30:00 bar**，`open=high=low=close`（四价合一），`vol`/`amount` = 09:25 集中撮合量 | doc 370 样例 `09:30:00 6.99 6.99 6.99 6.99 vol 103700`；doc 419 样例 `09:30:00 O=H=L=C`；doc 457 样例 `2026-04-15 09:30:00 10.05 10.05 10.05 10.05 vol 133400` |
| 09:31 | 第一根连续竞价 bar（量与四价正常展开） | doc 370 样例 `09:31:00 open 6.99 close 7.02 high 7.02 low 6.97 vol 807500` |
| 11:30 | 存在 11:30:00 bar（覆盖 (11:29,11:30]） | 241 根计数 |
| 11:31–13:00（午休） | **无任何 bar**（不产生 11:31…12:59） | 241 根计数 |
| 13:00 | **不存在 13:00:00 bar**；下午第一根是 13:01:00 | [二手] 镜像文档注「示例4中没有 13:00:00 便是这个原因」；官方 241 根计数一致 |
| 14:57 | 该 bar 覆盖 (14:56,14:57]，是**最后一根含连续成交的 bar** | doc 370 样例 `14:57:00 vol 51800` |
| 14:58 / 14:59 | **bar 存在但 `vol=0`**（收竞价期间不撮合连续单） | doc 370 样例 `14:59:00 … vol 0.0`、`14:58:00 … vol 0.0`；doc 419 样例 `14:59:00 vol 0.0` |
| 15:00 | 该 bar 承载**收盘集合竞价撮合量**（四价合一或近似合一） | doc 370 样例 `15:00:00 7.05 7.05 7.05 7.05 vol 235500`；交叉核对可用 `stk_auction_c.vol` |
| 15:05–15:30 | **分钟侧不下发**（日线侧另存 `ah_vol`/`ah_amount`，默认不返回） | `daily` 字段表含 `ah_vol`/`ah_amount`；分钟接口「暂未包含盘后固定价格交易的分钟行情」**[二手]**（官方 doc 370 页面直读文本中**未出现**该句，见 §7-①） |

### 2.3 三市收盘竞价的实施时间（务必按日分段处理）

| 市场 | 收盘集合竞价 | 起始时间 |
|---|---|---|
| 沪市（SSE 主板/科创板） | **有** | **2018-08-20**（上证发〔2018〕59号，上交所 2018-08-06 新闻稿） |
| 深市（SZSE 主板/创业板） | **有** | 中小板 2004 年率先、**主板 2006-07-01** 起 [二手]（规则文本 2.4.2 长期含此条，2018-03 版 PDF 已可查） |
| 北交所（BSE） | **有** | 2021-11-15 开市即采用 14:57–15:00（现行规则 2.3.2，2026-07-06 修订版同） |
| 2026-07-06 起新增 | 沪市基金（ETF/LOF/REITs）收盘阶段也改 14:57–15:00 集合竞价；全部 A股+ETF 启用 15:05–15:30 盘后固定价格交易（北交所股票暂不实施） | 上证发〔2026〕41号 / 新华社 |

> 对 300 只 × 2 年（2024-09 ~ 2026-09）窗口：**整个窗口三市都有 14:57–15:00 收盘竞价**，无需分段；但窗口**跨越 2026-07-06 盘后交易扩围断点**（见 §4-D8）。

---

## 3. 关键问题定论

### 3.1 `stk_mins` 的 `trade_time` 是 **bar_end（右端点，左开右闭）** — 置信度：高

- 官方页面文本（doc_id=370）**未写口径条款**（已定向检索，见 §7-①）；结论由**官方数据样例 + 二手口径原文 + 网格计数**三方一致确定：
  - [二手] 三处镜像文档正文一致：「本接口各频率统计区间口径是除了开盘第一个区间是左闭右闭之外，其他区间是**左开右闭**的，如 `(HH:MM:00, HH:MM+1:00]` 内的交易数据记为 `HH:MM+1:00`。」（掘金/腾讯云/CSDN 镜像，均称转录自 doc_id=370）
  - 官方样例 241 根的分布（09:30 竞价 + 09:31–11:30 + 13:01–15:00，**无 13:00:00**）只有"左开右闭 + 竞价单列"能解释。
  - 官方样例 `15:00:00` 承载收盘竞价量、`14:58/14:59` 为 vol=0，也与右端点语义自洽。
- **管道决策**：`normalise_kline(..., timestamp_semantics="bar_end", bar_frequency="1min", assume_tz="Asia/Shanghai")`，此时 `cutoff_time == bar_time`，不外加 `bar_frequency`（若误填 `bar_start`，所有特征整体右移一分钟，构成**一分钟未来函数**：09:31 的特征会被当作 09:32 可见）。

### 3.2 09:31 那根 bar 是否含集合竞价撮合量 — **不含**（置信度：高），但存在一处官方口径冲突未决

- 官方三处样例（`stk_mins` 2023-08-25、`idx_mins` 2023-08-25、`rt_min_daily` 2026-04-15）一致显示**竞价独立占据 09:30:00 bar**，特征为 `open=high=low=close` 且 `vol>0`；09:31:00 bar 四价展开，是纯连续竞价量。
- **冲突点**：[二手] 镜像正文写「早盘盘前竞价数据记为 **`09:00:00`**」，但同一镜像自己给出的样例是 `09:30:00`，官方 doc 370/419/457 样例也全是 `09:30:00`。判定：**"09:00:00" 是转录/版本错误**，实际以 `09:30:00` 为主；但不能排除**不同品种/频段/交易所（.SZ vs .SH、ETF、1min vs 5min）落在不同时间戳**的历史遗留差异 → 必须用 §3.2-验证脚本在首次采集时逐品种确认。
- **首次采集强制验证（3 次调用，成本可忽略）**：
  1. `stk_mins(600000.SH/000001.SZ/300750.SZ/832175.BJ, 1min, 单日)` → 检查是否存在 `09:00:00` 或 `09:30:00` 行、其四价是否合一；统计当日 bar 数（241? 240? 是否含 15:05+）。
  2. `stk_auction_o(trade_date=)` 与 `stk_auction_c(trade_date=)` 的 `vol` → 与分钟侧 `09:30:00.vol`、`15:00:00.vol` 逐只比对（应相等或在同一数量级）。
  3. `daily(trade_date=, fields='ts_code,vol,amount,ah_vol,ah_amount')` → 校验 `sum(stk_mins.vol) + (盘后? ) ≈ daily.vol×100`，从而确认分钟侧是否含盘后量、以及单位换算（股 vs 手）。
  把这三步的判定结果写入快照 `_manifest` 的 `timestamp_semantics_verified` 字段，作为全库的口径凭证。

### 3.3 深市/北交所收盘集合竞价 — **都有**（置信度：高）

任务书里的怀疑（「沪市 14:57–15:00 有，深市/北交所呢？」）结论是：**沪深北三市股票全部有 14:57–15:00 收盘集合竞价**，且深市比沪市早了 12 年。
- 深交所交易规则 2.4.2「13︰00至14︰57为连续竞价时间，14︰57至15︰00为收盘集合竞价时间」（官方 PDF）；4.2.3 收盘价由集合竞价产生。
- 北交所交易规则 2.3.2 同句式（北证公告〔2026〕17号，2026-07-06 施行）。
- 上交所 2018-08-06 新闻稿（该机制沪市自 2018-08-20 起）。
- 产品侧旁证：Tushare 提供 `stk_auction_c`「股票**收盘15:00**集合竞价数据」，且官方数据样例同时含 `.SH` 与 `.SZ`（300504.SZ 203.7 万股、300657.SZ 1091.6 万股）——若无深市收竞价，该接口对深市无意义。

### 3.4 竞价 tick 可辨性 — **Tushare Pro 侧不存在"逐笔 tick"层，因此没有 `type=2` 标志可用**（置信度：高）

- Pro 侧无任何 A股逐笔接口（§1.5）；能辨识竞价的**只有三条替代路径**：
  1. **bar 层**：09:30（或 09:00）bar 的"四价合一 + 有量"特征；15:00 bar 含收竞价量。→ 打派生标记 `is_call_auction`。
  2. **专用接口层**：`stk_auction_o` / `stk_auction_c` / `stk_auction` 显式给出竞价 `vol/amount/vwap`（历史分别自上线日与 2025-01 起）。→ 竞价量可从分钟总量中**精确剥离**。
  3. **旧版 SDK / L2 外部源**：`tick()` 的「type: 0-买入 1-卖出 **2-集合竞价成交**」——但需本地行情终端连接，不属本项目集成范围。
- 结论：**"竞价 tick 进不进盘口统计"在本项目退化成一个可解判定**：用 1+2 组合即可，无需 L2。

### 3.5 拉取式核实 — **确认为纯拉取，A股无任何流式推送**（置信度：高）

原文与判据见 §1.6。要点：HTTP `POST http://api.tushare.pro` + JSON body（`api_name/token/params/fields`）是唯一的 Pro 侧取数协议；`rt_*` 系列是"高频轮询的实时"，**无事件序号、无交易所毫秒时间戳、无买卖方向、无多档盘口**。期货 `rt_fut_min` 是官方唯一声明支持 websocket 的产品，且不在本项目范围。
→ **推论（规范级）**：任何"盘中低延迟"设计在本项目**不成立**；本项目的高频侧只能是"研究性事后重放 + 日终对齐"，不得宣称可用于盘中执行。

---

## 4. 管道规范决策建议（逐条：决策 + 理由 + 文献支持）

### D1 窗口聚合改为「交易时段感知」，由 `trade_cal` + 硬编码时段边界定义合法窗口全集

- **决策**：新增一张静态 `session_calendar`（`cal_date, exchange, open_auction=[09:15,09:25], gap=[09:25,09:30], morning=[09:30,11:30], afternoon=[13:00,14:57], close_auction=[14:57,15:00], after_hours=[15:05,15:30]`，`exchange` 来自 `ts_code` 后缀，日期合法性来自 `trade_cal.is_open=='1'`），并把 `aggregate_trades/aggregate_orderbook` 的 `resample(window, label="right", closed="right")` 的**候选 bin 全集**限制在 session 网格内；非交易时段 bin 一律**不生成行**（而不是生成空行）。窗口右端点即 `cutoff_time`，语义与 `normalise_kline` 的 `bar_end` 一致。
- **理由（代码事实）**：`aggregate_orderbook` 现用自然时钟 `work.resample(window, label="right", closed="right")`，11:31–13:00 的空 bin 会被 `min_snapshots` 丢掉，但 `(13:00,13:01]` 这类 bin 与 `stk_mins` 的 241-bar 网格并不等价；更关键的是 `snapshot_rate = len(g)/max(pd.Timedelta(window).total_seconds(),1)` 与 `event_ofi` 的相邻差分会**跨越午休把 11:29 的快照与 13:01 的快照视为相邻事件**，产生一条假 OFI/假 `log_mid_return`。竞价 bar 若参与同一网格，同理会把 09:25 撮合与 09:31 成交当成连续两个事件。
- **规范**：`cutoff_time` 序列**必须**能被 `session_calendar` 枚举（每交易日 241 个 1min 端点）；任何不在枚举内的 `cutoff_time` 视为脏数据，`CleaningReport` 计数后丢弃。
- **文献**：Gu et al. (2010, *Physica A* 389(2):278–286)——沪深开盘集合竞价的相对价格分布呈"零处尖峰、负向更宽"的非对称形态，竞价期订单簿结构与连续竞价**不可互换**；Han et al. (2022, *PBFJ* 74)——引入收盘集合竞价后「a shift of trading volume from closing to pre-closing; increased volatility at pre-closing」，即收盘前后的微观结构**不是同一时段**。

### D2 09:31 首根连续 bar / 09:30 竞价 bar / 沪市 15:00 末 bar：显式标记，不静默丢弃

- **决策**：在 `normalise_kline` 输出上追加两列派生标记（**不改函数签名**，由采集侧写入输入 DataFrame）：`is_call_auction ∈ {0,1}`（09:30 与 15:00 两根）、`session_slot`（该 bar 在 241 网格中的序号 0..240）。规范：
  - `bar_time == 当日 09:30:00` → `is_call_auction=1`，`auction_side='open'`；`bar_time == 15:00:00` → `is_call_auction=1`，`auction_side='close'`（沪市自 2018-08-20、深市自 2006、北交所自建市，本项目窗口内全适用）。
  - 14:58/14:59 两根 `vol==0` 的 bar **保留**（它们是"无成交"的合法证据，见 D5）。
  - 任何以 `bar_time` 价格为可成交价位的回测：**15:00 那根标记为 `tradable=0`**（收盘后不可成交）；09:30 竞价 bar 标记为 `tradable=1` 但 `execution_lag=1 bar`（撮合价 09:25 已定，09:30:00 起才可交易）。
- **理由**：`normalise_kline` 的价格校验（`high>=max(open,close)`、`low<=min(open,close)`、`volume>=0`）对四价合一 bar 与 vol=0 bar 天然放行，因此**不必改函数**即可安全入库；真正危险的是把竞价 bar 当普通 bar 混入量能/波动统计——[二手] 知乎实测指出「用首根 K 线量 vs 过去 N 日均量判断开盘强弱会把两种撮合机制的量混在一起（09:30 bar 596 手 vs 09:31 bar 2551 手），信号从第一根就失真」。
- **文献**：Suen (2022, *Journal of Financial Markets*)——以港交所自然实验说明**集合竞价的设计直接影响收盘价被操纵的程度**；Li (2021, *Quantitative Finance*) "Call auction, continuous trading and closing price formation"——收盘竞价与连续竞价的收盘价形成机制需分别建模。（以上两条书目取自检索列表条目名，全文未逐页复核，见 §7-⑤。）

### D3 集合竞价"量价"进特征、集合竞价"盘口/OFI"不进统计（折中方案）

- **决策（推荐）**：**双轨**——
  1. **进**：竞价的 `vol/amount/vwap/price`（来自 `stk_auction_o/c` 或 09:30、15:00 bar），作为**独立列** `auction_vol_open`、`auction_vwap_open`、`auction_vol_close`，与连续竞价列并存，不与连续竞价值相加。
  2. **不进**：把竞价阶段的快照/成交塞进 `clean_orderbook → add_event_ofi → aggregate_orderbook` 的 `event_ofi / spread_bps_mean / depth_imbalance_mean / book_slope / realized_mid_vol` 统计。
- **理由**：竞价期间交易所揭示的是「集合竞价虚拟参考价格、虚拟匹配量和虚拟未匹配量」（SSE 5.2.1），**不是可成交的买卖五档队列**；`add_event_ofi` 的队列增减定义（`1[b_n>=b_prev]q_b,n - 1[b_n<=b_prev]q_b,prev …`）依赖"报价排队"语义，虚拟匹配量是累计意向而非队列 → 直接混入会让 OFI 量纲跳变，且竞价 bar 四价合一使 `spread_bps=0` 拉低均值、`book_slope` 退化（`best_ask-best_bid` 为 0 走 `replace(0, np.nan)` 分支）。
- **反方案（把竞价 tick 一并纳入）的利弊**：利——开盘竞价量与订单失衡对当日收益有可预测性的证据链完整（Zhang/Jiang/Zhou 2021 *Accounting & Finance* 61(2):2809–2836 在中国市场检验订单失衡与收益；Peng 2024 *PBFJ* 88 综述指出证据**方向不一**，故"多喂一点数据"未必增益）；弊——特征分布在竞价 bar 上与其他 bar 不可比，模型会把"机制差异"学成"信号"，且 `hf_available`/`spread_bps` 出现系统性 0 值，破坏跨股票一致性。**折中方案（双轨）保留信息、隔离机制**，代价是多两列常量输入。

### D4 低频侧（Kronos 读 K 线窗口）：主键用**真实钟点**，模型时间特征用**交易序号**，两者都要有

- **决策**：
  1. **存储/对齐层主键 = 真实钟点（bar_end，Asia/Shanghai → UTC）**：`cutoff_time` 一律真实时刻，`make_future_labels` / `align_features_to_kline` 全部基于它。
  2. **模型时钟 = 压缩交易时间**：为每根 bar 生成 `session_seq`（0..240）与 `session_frac = session_seq/240`，并把喂给 Kronos 的时间特征由 `(minute, hour, weekday, day, month)` 改为 `(session_frac, minute, hour, weekday, day, month)`——即**保留** `hour/minute`（真实钟点，语义与预训练一致），**新增** `session_frac` 作为交易进度编码，同时**禁止**把 11:30→13:01 之间的 90 个自然分钟当作 bar 喂入（否则窗口长度含 90 个"假静默步"）。
- **理由（代码事实）**：`KronosLocal/deps/Kronos/finetune_csv/finetune_base_model.py` 的 `self.time_feature_list = ['minute','hour','weekday','day','month']`，`model/module.py` 中 `minute_size = 60; hour_size = 24; weekday_size = 7`；本项目 `research/scripts/kronos_context_adapter.py::_stamp_frame` 直接喂 `ts.minute/ts.hour/ts.weekday/ts.day/ts.month`。**若改用压缩交易时间重编 hour/minute（例如把交易日重映射为 0–240 分钟并令 hour=seq//60），会让 A股 13:01 被打成 10:40 之类，与预训练（7×24 连续、加密/股票 24/7 语义）的 embedding 分布错开**——这是零样本基线不该承受的分布漂移。反之，只用真实钟点也无法表达"日内进度"（11:29 与 14:59 的 `hour` 都不同但"进度"信息缺失，且午休导致 `minute` 序列出现 90 分钟空洞）。
- **文献/方法论支持**：López de Prado (2018)《Advances in Financial Machine Learning》第 2 章（time bars vs volume/tick bars；时间驱动采样的收益非正态、信息到达不均匀）——支持"以信息到达为准的时钟"作为**模型内部时钟**；本项目对 `session_seq` 的取舍与之相容。

### D5 稀疏 regime：`hf_available` 必须三态化（无事件 / 未采集 / 停牌）

- **决策**：管道输出的 `hf_available`（现为 `out[hf_cols].notna().any(axis=1)`）**保留为布尔"有可用特征"**，但其上游必须新增两列显式状态，且规范禁止用 `fillna` 造"有数据"假象：
  - `collect_status ∈ {ok, empty_no_event, not_collected, api_error, permission_denied, non_trading_day, suspended}`（采集侧逐 (股票,日) 写入；`not_collected`/`api_error` 是**采集失败**，`empty_no_event` 是**确实无事件**）。
  - `suspension_flag`（由 `suspend_d` 按 `trade_date + ts_code` 匹配，含 `suspend_timing` 日内停牌时段）。
  - 规则：只有 `collect_status=='ok'` 的 (股票,日) 才允许出现"特征列全 NaN"被解释为"无数据"；`empty_no_event` 对应 `stk_mins` 的 `vol=0` bar（**证据：官方样例 14:58/14:59 `vol 0.0` 是真实下发的 bar**）；`not_collected` 必须与 `empty_no_event` 区分，否则模型会把"我没拉回来"学成"这只股票这一分钟没有交易"。
- **理由**：`align_features_to_kline` 用 `merge_asof(direction="backward")` + `hf_cols.notna().any()`，**未命中与命中但值缺失不可分**；`aggregate_orderbook`/`aggregate_trades` 在空 bin 上 `continue`（不产行）→ 稀疏小票会大面积缺行 → 小票 `hf_available=False` 大面积成立，正是"小票样本被隐性丢弃"的风险。Han et al. (2022) 摘要明确指出「the regime appears to have a pronounced impact, particularly on **small-cap** stocks」——小票时段效应本身不同，不能被缺失机制二次污染。
- **补充规范**：小票 1min 会出现**整天 `vol=0` 的连续段**（一字板/停牌前后）；` CleaningReport` 之外需产出"每股票每日有效 bar 比例"分布报告，作为 `hf_available` 阈值与样本加权的依据。

### D6 停牌日 / 节假日在 asof 对齐与未来标签中的处理

- **决策**：
  1. `align_features_to_kline` **必须显式传 `tolerance`**，规范值 `tolerance="120s"`（1min 频度）；跨午休/跨日的 backward 匹配一律**视为不命中**（配合 D1 的 session 网格，120 秒容差在语义上等价于"同 session 内相邻"）。
  2. 停牌日：**不生成 kline 行**（`daily` 官方声明「停牌期间不提供数据」），`trade_cal` 保证不生成非交易日行；日网格用 `trade_cal.pretrade_date` 做"上一交易日"链，而非日历日减一。
  3. **跨停牌的未来标签**：`make_future_labels(horizon=1)` 现按 `groupby("asset_id")` 的**行序** `shift(-horizon)` ⇒ 停牌后第一根 bar 与停牌前最后一根 bar 在行序上相邻，标签会隐含"跨多日隔夜收益"。规范改为**在同一交易日的 session bar 序列内计数**（`horizon` 以交易分钟为单位），并新增 `target_valid`：若 `[cutoff_time, 目标 cutoff_time]` 区间内存在 `suspension_flag=1`、`is_call_auction` 跨越日界、或缺 `trade_cal` 连续性，则 `target_valid=False`（**丢样本，不前向填充价格**）。
  4. 隔夜/跨日：显式区分 `intraday` 与 `overnight` 两类标签；**禁止**用 15:00 收盘竞价 bar 的 close 作为可成交 entry（D2 已标 `tradable=0`）。
- **理由**：停牌期间前向填充价格会人为制造零收益段、压低 `target_realized_vol`，并把不可交易状态计入训练；而 `merge_asof` 无 tolerance 时，停牌数周后第一根 bar 会 asof 到停牌前的旧特征，`hf_available=True` 但特征"过期数周"——这是典型的隐性泄漏。`pretrade_date` 是官方提供的唯一"上一交易日"权威字段（doc 26），必须用它而不是 `date-1`。

### D7 复权与单位：入库一律未复权 + 独立复权因子，禁止依赖 `pro_bar` 的动态复权

- **决策**：采集层落 `stk_mins`（未复权，元/股）与 `daily`（未复权，手/千元）+ `adj_factor`；**单位归一化在管道入口显式声明**：`vol_stk_mins`（股）→ `volume = vol`；`vol_daily`（手）→ `volume = vol*100`。`pro_bar(qfq)` 不作为数据源。
- **理由（官方原文）**：「复权机制是**根据设定的end_date参数动态复权**，采用分红再投模式」、「目前只支持日线复权」（doc 109）→ qfq 结果依赖 `end_date`，**同一股票同一天的历史价格会随查询窗口变化**，直接摧毁快照可复现性；且分钟侧无复权支持。`pct_chg` 是「基于除权后的昨收计算」（doc 27），若用未复权 `close` 自算收益会在除权日出现假跳空——必须用 `pre_close`（官方已注明是除权价）或 `adj_factor`。

### D8 2026-07-06 盘后固定价格交易扩围 = 显式 regime 断点

- **决策**：把 2026-07-06 记入快照元数据 `regime_breaks`，并在特征侧固定两件事：(a) 分钟量**不含**盘后成交（`stk_mins` 至 15:00 为止）；(b) 若需要全日量，用 `daily.vol + ah_vol`（`ah_*` 默认不返回，须 `fields='trade_date,vol,amount,ah_vol,ah_amount'` 显式请求）。断点前后不得混用"日成交量"口径做同一特征。
- **理由**：断点前只有科创板/创业板有盘后固定价格交易，断点后全部 A股+ETF 都有 → 同一特征（当日总成交量、量比、成交额占比）在断点前后分布不同，且**北交所股票暂不实施**（三市又不一致）。这是纯机制断点，不是市场变化，必须显式声明而非让模型去学。

### D9 `clean_orderbook` 的 5 档契约在 Tushare A股侧**不可满足** → 高频侧降级声明

- **决策（规范级）**：本项目 A股高频侧的"盘口特征"**不成立**，除非另购外部 L2。规则：
  - 若走 `rt_k`：它只有一档 `bid_price1/ask_price1/bid_volume1/ask_volume1` + `trade_time`（快照时刻，非事件）。映射为 `bid_price_0←bid_price1`、`ask_price_0←ask_price1` 等，`clean_orderbook(levels=1)` 可通过，但 `aggregate_orderbook` **硬要求 `BOOK_COLUMNS`（5 档，含 `bid_price_4`/`ask_price_4` 用于 `book_slope`）** → 必须降级为"只用一档"或补 5 档占位（**禁止补 0/前向填充**，会触发 `clean_orderbook` 的 `(bid_p>0).all()` 与 `ordered_book` 判定而整行丢弃）。
  - `rt_k` 的 `trade_time` 是**快照时间**（同一秒重复轮询产生同值快照）→ `clean_orderbook` 的 `drop_duplicates(subset=["event_time"], keep="last")` 会把同一秒内多票/多次轮询误删，**必须先按 `(ts_code, trade_time)` 双键去重且分组处理**。
  - 轮询上限 50 次/分钟 ⇒ 理论最优 1.2 s 一条快照，但**无交易所时序保证**，因此不得声称"逐笔"或"盘口动态"。
- **理由**：这是"任务书假设 L2 可得"与现实"Pro 无 A股 L2"的硬冲突，必须写进规范而不是留待实现时踩坑。

---

## 5. 数据字典表（核心交付物）

> 目标列名一律为 `scripts/hf_data_pipeline.py` 所需列名。"需显式声明"指调用管道函数时必须由采集侧提供的参数（否则 `ValueError` 或语义错误）。

| Tushare 端点 | 字段 | 类型 | 时间戳语义（事件/快照，bar start/end） | 更新时效 | 映射到管道函数 → 列 | 需显式声明 | 备注 |
|---|---|---|---|---|---|---|---|
| **`stk_mins`**(370) | `ts_code` | str | — | 日终 17–21 点 | `normalise_kline(asset_id=…)` → `asset_id` | `asset_id` 或 `asset_col='ts_code'` | 一次一只（官方：「只能一个个标的按时间段获取分钟」） |
| | `trade_time` | **str** | **bar_end（左开右闭，(t-Δ, t]）**；北京时、tz-naive | 同上 | `normalise_kline(timestamp_col='trade_time')` → `bar_time`,`cutoff_time` | **`timestamp_semantics="bar_end"`**、**`assume_tz="Asia/Shanghai"`**、`bar_frequency="1min"` | str 需先 `to_datetime`；填 `bar_start` 即引入 1 分钟前视 |
| | `open/high/low/close` | float | 随所属 bar（end） | 同上 | → `open/high/low/close` | — | 未复权；09:30 与 15:00 bar 四价合一=竞价结果 |
| | `vol` | int | bar 内**增量**成交量 | 同上 | → `volume` | **单位=股，勿再 ×100** | `vol=0` 合法（无成交），非缺失 |
| | `amount` | float | bar 内成交额（元） | 同上 | 管道外（可算 VWAP） | 单位=元 | — |
| | *(派生)* `is_call_auction` | int8 | — | 采集侧生成 | 透传（供 D2/D3 过滤） | — | 09:30 / 15:00 bar 置 1 |
| | *(派生)* `session_seq` | int16 | 241 网格序号 | 采集侧生成 | 供 Kronos 时钟（D4） | — | 由 `session_calendar` 枚举校验 |
| | *(派生)* `collect_status` | str | — | 采集侧生成 | `align_features_to_kline` 的 `hf_available` 三态化依据（D5） | — | ok/empty_no_event/not_collected/api_error/suspended |
| **`idx_mins`**(419) | 同 `stk_mins` | — | 同 bar_end | 日终 | 同 `normalise_kline` | 同上 | 官方样例结构一致（09:30 四价合一、14:59 vol 0） |
| **`daily`**(27) | `trade_date` | str(YYYYMMDD) | **日粒度**，无时刻 | 「交易日每天15点～16点之间入库」 | 低频侧直接作为 `cutoff_time = trade_date+15:00` 的日 bar | `timestamp_semantics="bar_end"`（日频）、`assume_tz` | 停牌期间不提供数据（官方） |
| | `vol` / `amount` | float | 日累计 | 同上 | 校验 `stk_mins` 汇总 | **单位=手 / 千元**（×100 / ×1000 才等于股/元） | 与分钟侧单位不同 |
| | `ah_vol` / `ah_amount` | float | 盘后固定价格（15:05–15:30） | 同上 | 不入 bar；单独列 | `fields=` 显式请求（默认不返回） | 2026-07-06 扩围，北交所暂不实施（D8） |
| | `pre_close` / `pct_chg` | float | 日 | 同上 | 日频标签/除权校验 | — | `pre_close` 是**除权价**，自算收益须用它 |
| **`trade_cal`**(26) | `exchange`,`cal_date`,`is_open`,`pretrade_date` | str | 日历日 | 静态字典 | D1 的 session 网格合法性；D6 的"上一交易日"链 | `exchange='SSE'`（默认）| 「三大交易所的交易日历都是一样的」→ 单一日历可用 |
| **`suspend_d`**(214) | `ts_code`,`trade_date`,`suspend_type`,`suspend_timing` | str | 日期 + 日内时段 | 「不定期」 | `suspension_flag` / `target_valid`（D5/D6） | — | `S`=停牌 `R`=复牌；`trade_date` 覆盖整段停牌期 |
| **`stock_basic`**(25) | `ts_code`,`list_date`,`delist_date`,`list_status`,`market`,`exchange` | str | 日期 | 静态 | 样本池构造、防幸存者偏差 | `list_status='L'` 与 `'D'` 各拉一次 | 每分钟仅 50 次；官方建议「保存倒本地存储后使用」 |
| **`stk_limit`**(183) | `trade_date`,`ts_code`,`up_limit`,`down_limit` | float | 日 | 「每个交易日9点左右更新当日」 | 涨跌停不可成交掩码（回测约束） | — | 单次 5800 条覆盖全市场；ETF 已拆到 `etf_limit`(491) |
| **`stk_auction_o`**(353) | `ts_code`,`trade_date`,`open/high/low/close`,`vol`,`amount`,`vwap` | float | **09:25 一次性撮合结果**（日粒度，无时刻） | 「每天盘后更新」 | 剥离 09:30 bar 的竞价量（D3）；交叉验证 §3.2 | 按 `trade_date` 循环 | 官方样例：`.SH` 四价合一、`.SZ` open≠close |
| **`stk_auction_c`**(354) | 同上（收盘口径） | float | **15:00 收盘竞价撮合结果** | 「每天盘后更新」 | 剥离 15:00 bar 的竞价量 | 按 `trade_date` 循环 | 样例含 `.SH` 与 `.SZ` ⇒ 深市收竞价确证 |
| **`stk_auction`**(369) | `ts_code`,`trade_date`,`vol`,`price`,`amount`,`pre_close`,`turnover_rate`,`volume_ratio`,`float_share` | — | 当日开盘竞价（快照） | **「每天9点26~29分之间可以获取」**；历史自 2025-01 | 盘中唯一可得的竞价结果；对账 | 按 `trade_date` | ETF 已拆到 `etf_auction`(493) |
| **`rt_min`**(374) | `ts_code`,`time`,`open/close/high/low`,`vol`,`amount` | str | 分钟 bar（与 `stk_mins` 同网格；官方样例 09:30 四价合一） | 盘中轮询（每分钟 500 次；单次可同时 300 只） | 仅用于**当日补拉/盘前对账**，不做事件源 | `freq='1MIN'`（**大写**）；`assume_tz` | 单次 1000 行上限 |
| **`rt_min_daily`**(457) | `code`,`freq`,`time`,`OHLC`,`vol`,`amount` | str | 当日开盘以来全部分钟 bar | 盘中 | 同上 | `freq` 大写 | 权限随"实时分钟"自动获得 |
| **`rt_k`**(372) | `ts_code`,`trade_time`,`open/high/low/close/pre_close`,`vol`,`amount`,`num`,`bid_price1/bid_volume1`,`ask_price1/ask_volume1` | str/float | **查询时刻的 L1 快照（非事件）** | 盘中轮询，每分钟 50 次，每次全市场 6000 条 | 唯一含盘口者：`bid_price1→bid_price_0` 等 → `clean_orderbook`；`num` 差分 → `aggregate_trades.trade_count` 近似 | **`assume_tz="Asia/Shanghai"`**、`levels=1`；先按 `(ts_code,trade_time)` 去重 | ⚠ `aggregate_orderbook` 硬需 5 档（D9）；`vol` 是当日**累计** |
| **`pro_bar`**(109) | 集成 | — | 随 `freq` | 「股票和指数通常在15点～17点之间」 | **不入库**（现算、动态复权） | — | qfq 依赖 `end_date`，破坏可复现性（D7） |
| *(不存在)* `ticks` / `order` / `transaction` | — | — | — | — | `clean_trades` / `aggregate_trades` / `clean_orderbook`(5档) **无 Tushare 数据源** | — | §1.5 否证；旧版 SDK `tick()` 有「type … 2-集合竞价成交」但需本地行情终端，不属集成范围 |
| *(非 API)* `期货历史Tick`(314) | `InstrumentID`,`BidPrice1/…`,`UpdateTime`(带毫秒) | — | 快照，`UpdateTime` 为事件时刻 | 网盘 csv 交付 | 不接入 | — | 「当前不提供API方式获取」，期货专用 |

---

## 6. 批量拉取与本地快照方案（满积分 + 已购分钟权限）

### 6.1 工作量估算（300 只 × 2 年 1min K 线 + "1 年逐笔"）

设 2 年 = **484 个交易日**（A股每年约 242 个），每股票每日 **241 根** 1min bar。

| 任务 | 行数 | 单次上限 | 调用次数 |
|---|---|---|---|
| `stk_mins` 1min：300 只 × 484 天 | 300×484×241 ≈ **3.50×10⁷ 行** | 8000 行/次 | 理论下限 `ceil(116,644/8000)=15` 次/只 → **4,500 次**；**建议按 20 交易日/窗**（20×241=4,820 行，留 40% 余量）→ 25 次/只 → **7,500 次** |
| `daily`（按 `trade_date` 全市场循环） | 484 次（每次 6000 行覆盖全市场） | 6000 | **≈484 次**（含 `ah_*` 字段的 fields 显式请求，同一次即可） |
| `stk_limit`（按日） | 484 | 5800 | **484 次** |
| `suspend_d`（按日） | 小 | — | **484 次** |
| `stk_auction_o` + `stk_auction_c`（按日，各 1 次覆盖全市场） | 10000 行/次 | 10000 | **968 次** |
| `trade_cal` / `stock_basic`(L+D) | — | — | **≈3 次** |
| **合计** | ≈ 3.6×10⁷ 行 | | **≈ 9,930 次 ≈ 1.0×10⁴ 次** |
| 「1 年逐笔 / L2」 | **Tushare Pro 无此接口** → **0 次** | — | 替代见 §6.4 |

### 6.2 分批与限速

- 上限：历史分钟 **500 次/分钟、8000 行/次、30 万频次/24h 滚动窗口**（官方原文见 §1.1）。总频次 9,930 « 30 万 ⇒ **日窗口不 binding，瓶颈是每分钟 500 次**。
- **令牌桶限速 300 次/分钟**（留 40% 余量给重试与常规接口共用），并发 worker **2 个**（按股票分片，互不重叠）：`7,500 次 ÷ 300 次/分 ≈ 25 分钟`；叠加网络实测（8000 行响应 ~0.4–1.2 s）→ 单线程串行为 `7,500×0.8s ≈ 100 分钟`，2 worker ≈ **50–60 分钟**；再计入分页边界重试、`api_error` 退避（指数 2/4/8/16 s，最多 5 次）→ **总预算 2–3 小时**（含常规接口 ~2,000 次，约 +10 分钟）。
- 分批顺序（先元数据、后行情，保证可中断续跑）：① `trade_cal`/`stock_basic`/`suspend_d`/`stk_limit` ② `daily`（含 `ah_*`）③ `stk_auction_o`/`stk_auction_c` ④ `stk_mins`（按股票 × 20 日窗口，**先跑 4 只样本票做 §3.2 三步口径验证，通过后再全量**）。
- 每次调用落 **调用日志**（`api_name, params_hash, http_code, tushare_code, rows, requested_window, fetched_at, elapsed_ms, retry_n`）；`tushare_code==2002`（权限问题）单列告警，不当作空数据。

### 6.3 本地快照设计规范（parquet 契约）

```
data/hf_snapshot/
  _manifest/
    calls.parquet                     # 每次调用一行（§6.2 日志）
    regime.parquet                    # collected_at, data_as_of, schema_version, 分钟权限到期日
    timestamp_semantics_verified.parquet  # §3.2 三步验证的逐品种结论（bar_end / 竞价 bar 时间戳 / bar 数 / 单位对账）
  stk_mins/freq=1min/exchange=SSE/trade_date=20260630/600000.SH.parquet
  daily/trade_date=20260630/all.parquet
  trade_cal/exchange=SSE/all.parquet
  suspend_d/trade_date=20260630/all.parquet
  stk_auction_o/trade_date=20260630/all.parquet
  stk_auction_c/trade_date=20260630/all.parquet
  stk_limit/trade_date=20260630/all.parquet
```

- **分区**：`(端点, 频率/市场, 股票, 日期)`；`stk_mins` 必须带 `freq=` 层（1/5/15/30/60 分线口径不可混存）。文件名小写、`_` 分隔，与 Hive 风格 `key=value` 目录并存（读侧用 `pyarrow.dataset`，只按 `trade_date` 过滤即可增量）。
- **列契约**：每份 parquet 内**只放原始字段**（不改名、不换算），派生列（`is_call_auction`、`session_seq`、`collect_status`、单位归一后的 `volume`）在管道入口生成——保证快照是"证据"，派生是"可重算的解释"。禁止在快照里落复权价（D7）。
- **元数据（关键）**：每个文件写 parquet key-value metadata：`{"api_name","api_params_json","requested_window_start/end","rows","fetched_at_utc","data_as_of_local(=北京时点该窗口最后一根 bar 的时刻)","schema_version","collector_version"}`；`data_as_of` 是训练期唯一合法的"世界截止点"，任何标签/特征不得越过它。
- **增量**：每日 **17:30 之后**（`stk_mins` 官方窗口 17–21 点，建议 20:30 起跑并留重试）拉当日；`daily` 15:30 后可先拉（15–16 点入库），`stk_auction_o/c` 盘后即可。重跑用 `(端点,股票,日期)` 幂等覆盖。
- **上游修正处理**：Tushare 会对历史数据回溯修订，因此**每周做一次全窗口 checksum**（对每 (股票,日) 记录 `md5(trade_time+close+vol)` 与 `sum(vol)`），checksum 变化即写 `revisions.parquet` 并触发下游重训标记；训练一律"按快照日期版本化"（`data_as_of` 命名），不覆盖旧版本。
- **体积**：3.5×10⁷ 行 × 8 列 → 1min 全库（zstd + 字典编码）约 **250–450 MB**；其余接口合计 < 60 MB。
- **不直连 API 的理由（规范级）**：① **可复现性**——同一 `trade_date` 区间两次拉取可能因上游修订/动态复权（D7）而不同，只有快照能给出确定的 `data_as_of`；② **频率限制**——500 次/分钟、30 万频次/日 的硬约束使"训练中按需取数"不可行（每个 epoch 重复取数会立刻打满），且 `stock_basic` 每分钟只有 50 次这类不规则限流；③ **权限与成本**——分钟/实时/竞价权限与积分脱钩且按年计费（§1.0），到期即 `code==2002`，训练中途失权会让任务不可恢复；④ **上游修订不可见**——只有带 checksum 的本地快照才能发现修订，直连则静默改变结果；⑤ **合规**——「数据只供策略研究和学习使用，不允许作为商业目的」（doc 234），项目对外交付形态是模型而非数据再分发，快照层隔离也避免 token 进入仓库。

### 6.4 「1 年逐笔」的替代方案（因 Pro 无 A股 L2）

- **方案 A（推荐，纯 Tushare）**：放弃逐笔，高频侧改为"分钟三轨"——1min bar（`stk_mins`）+ 竞价分离列（`stk_auction_o/c`）+ 全市场一档快照轮询（`rt_k`，50 次/分钟，接受其 L1 语义与 D9 的降级声明）。管道内 `aggregate_orderbook` 需显式改为一档模式（`levels=1` + 跳过 `book_slope`/5 档 `depth_imbalance`）。
- **方案 B（外部 L2，明确移出本项目 Tushare 集成范围）**：交易所/券商 L2 逐笔（如 掘金 quant-open `get-realtime-tick-by-tick`/`get-realtime-order-book`、QMT/xtquant、Wind/聚宽/米筐）。量级参考：小票日均逐笔成交 ~10³–10⁴ 条、委托更多，300 只 × 250 日 ≈ **10⁸–10⁹ 条**、数十 GB–TB 级；这类源通常需独立合同与本地落盘链路，且**不属于"用户本机满积分 Tushare"能力**。若采用，`clean_trades(side_col=…)` 才有真实 `buy/sell` 方向可用（Tushare Pro 无处提供方向标志，故 §4 中所有 signed-volume 特征在方案 A 下必须置为缺失，不得用价格跳动猜方向——`clean_trades` 原文即「Unknown side values remain missing and are not guessed from price movements」）。

### 6.5 盘中可得性分级（给训练/回测侧的硬约束）

| 级别 | 源 | 最早可得时刻 | 允许用途 |
|---|---|---|---|
| T+0 日终 | `stk_mins`/`daily`/`stk_auction_o/c`/`suspend_d` | 当日 17:00–21:00（分钟）、15:00–16:00（日线） | 唯一合法的**研究与训练**数据面 |
| T+0 盘中（伪实时） | `rt_min`/`rt_min_daily`（1000/月）、`stk_auction`（09:26–09:29）、`rt_k`（每分钟 50 次轮询） | 当日盘中 | 仅用于**当日补拉、对账、开盘竞价核对**；不得用于声称低延迟执行（§3.5） |
| 静态 | `trade_cal`/`stock_basic`/`stk_limit` | 前一日/当日 09:00 前 | 样本池与时段网格构建 |

---

## 7. 未能核实的点（须首拉验证 / 需向官方确认）

1. **`stk_mins` 的"左开右闭"与"盘后固定价格未包含"两条口径，官方页面直读文本中不存在。** 我对 doc_id=370 做过定向二次核验，逐项回答：「盘后固定价格」ABSENT、「口径」ABSENT、「左开右闭」ABSENT、「19点~20点更新」ABSENT；页面正文（接口/描述/限量/权限/参数表/用法/数据样例）已全部照录。这些表述只出现在镜像文档（掘金/腾讯云/CSDN，均自称转录 doc_id=370）与 Tushare 更新日志类文章中。**可能解释**：官网正文为前端渲染，存在未被抓取到的说明块/折叠区，或镜像转录自更新公告。**处理**：§3.2 的三步首拉验证为**强制前置工序**，其结论（而非文档措辞）才是本项目的口径依据。
2. **竞价 bar 时间戳：`09:30:00` vs `09:00:00` 的措辞冲突未决**，且未核实是否按 `.SH/.SZ/.BJ`、按频段（1/5/15/30/60min）、按 ETF 而不同。官方样例支持 `09:30:00`。
3. **深市股票是否同样为 241 根/日、15:00 bar 是否含收竞价量**：官方样例只给了 600000.SH / 000001.SH / 600000.SH(rt_min_daily)。`stk_auction_c` 含 .SZ 行属强旁证，但**分钟侧未直读**。
4. **停牌股票的分钟侧行为未核实**：整日无 bar？还是下发 `vol=0` 的 241 根？（`daily` 官方明确「停牌期间不提供数据」，分钟接口无对应声明。）→ 首拉时用 `suspend_d` 挑一只当日停牌票核对，这是 D5 `collect_status` 取值划分的前提。
5. **两处文献未逐页复核全文**：Suen (2022, *JFM*)、Li (2021, *Quantitative Finance*) 的书目与主题取自检索结果条目；Zhang/Jiang/Zhou (2021)、Peng (2024) 的方向性结论来自检索代理摘要；López de Prado (2018) 第 2 章内容凭文献记忆、本次未联网核实。引用时如需作为论证支点，应补原文页码。另注：Han et al. (2022) 摘要给出的样本区间表述为「from May to January 2018」，与上交所 2018-08-20 的实施日期不完全吻合（RePEc 页面亦有排版歧义），本文仅引用其摘要中的结论方向，未据其推断实施时点。
6. **任务书所述 `ticks`「每交易日每只 500 点」在 Tushare Pro 文档中找不到任何对应接口**（§1.5 三条否证）。该描述可能来自新浪/腾讯网页分笔的截断行为、第三方 L2 目录，或已废弃的旧版 `ts.get_tick_data`。需向数据提供方确认出处。
7. **实时类接口的"盘中延迟秒数"官方从未量化**：`rt_k`/`rt_min`/`rt_min_daily` 的文档只写「实时」「每天9点半开始」，无延迟 SLA、无快照序号字段（`rt_k` 的 `trade_time` 与 `num` 是唯一的时点线索）。因此高频侧一切"延迟"参数只能由用户本机实测（连续轮询记录 `fetched_at - trade_time` 分布）后写回快照元数据。
8. **`stk_auction_o/c` 与 `stk_mins` 竞价 bar 的一致性、以及 `stk_auction`（历史自 2025-01）在 2024 年区间的替代方案**未核实——2024 年的竞价量只能靠分钟 bar 的四价合一特征辨识（D3 路径 1）。
9. **北交所股票（`.BJ`）在 `stk_mins` 的覆盖起点与 bar 网格**未核实（`trade_cal` 声明北交所参考上交所/深交所，但分钟接口是否含 .BJ 无官方说明；2026-07-06 盘后交易扩围亦明确"北交所暂不实施"）。

---
