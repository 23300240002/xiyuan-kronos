# Deep Research A · 微观结构标准 vs 项目代码审计（2026-09-17）

审计对象：`scripts/hf_data_pipeline.py`（403 行，8 个待审函数）
外部标准来源：见 §0；所有公式均给英文原文逐字 + 出处 + [一手]/[二手] 标注。
本地复现证据：所有"偏差"结论均用离线合成数据跑过（`/tmp/t_audit.py`、`t2.py`、`t4.py`，无网络、无改动源码），关键数字写在对应行。

---

## 0. 方法（查了什么源，一手/二手标注）

**工具与通路**：`web_search`（DashScope 检索代理）+ `web_fetch`（arXiv abs / arXiv HTML 全文 / 出版商页 / 交易所官方文档）。本机 `pdftotext` 与 pypdf/fitz/pdfminer 均不可用（`python3 -c "import pypdf..."` 全部 NO），因此**所有只存在于付费/扫描 PDF 里的原文一律降级为 [二手]**，已下载成功的两个 PDF（Andersen-Bollerslev-Diebold-Labys 2003 Econometrica、Andersen-Bollerslev 1997 Journal of Finance）为**扫描图像，无文字层，无法逐字核对**，只作为出处指针，不作为引文。

**[一手=原文核对]（本轮实际打开并逐字摘录的页面）**

| # | 文献 | 标识 | 取到的原文位置 |
|---|---|---|---|
| S1 | Cont, Kukanov & Stoikov, *The Price Impact of Order Book Events* | arXiv:1011.6402v3（HTML 全文）＝JFEC 12(1):47–88 (2014) | §1.1、§2.1 Variables、§2.3、§3.1、§3.2 |
| S2 | Xu, Gould & Howison, *Multi-Level Order-Flow Imbalance in a Limit Order Book* | arXiv:1907.06230v2（HTML 全文） | §2.1、§3.1 式 (9)(10)(11)(12) |
| S3 | Cont, Cucuringu & Zhang, *Cross-Impact of Order Flow Imbalance in Equity Markets* | arXiv:2112.13213（abs 页，v1 2021-12-25 / v4 2023-06-13） | 摘要逐字 |
| S4 | Su, Sun, Li & Yuan, *The Price Impact of Generalized Order Flow Imbalance* | arXiv:2112.02947（abs 页） | 摘要逐字 |
| S5 | *The Micro-Price: A High-Frequency Estimator of Future Prices* 的复述与推导 | arXiv:2411.13594v1（HTML 全文）；原始出处 Stoikov (2018), *Quantitative Finance* 18(12):1959–1966, DOI 10.1080/14697688.2018.1489139 | §2 式 (1)(5)、加权中间价定义、对 mid-price 的批评 |
| S6 | *VOLatility Archive for Realized Estimates (VOLARE)* | arXiv:2602.19732v1（HTML 全文） | §4.4 From Tick Data to Regular Intervals、§5.1、§5.1.4 |
| S7 | *A Frequency-Controlled Comparison of Tick- and Minute-Based Information Bars for Cryptocurrency Markets*（Binance aggTrade, BTCUSDT 永续, 2020-01–2025-12） | arXiv:2608.26158v1（HTML 全文） | §I-A、§III-C、§IV 开头、§IV-A |
| S8 | Binance 官方 Spot API 文档（trade / aggTrade 字段语义） | github.com/binance/binance-spot-api-docs `web-socket-streams.md`；dev.binance.vision/t/5660 | payload 注释逐字、maker/taker 判定表 |

**[二手=转述]**（记录来源，不当作原文引用）：Næs & Skjeltorp (2006) 与 Ghysels & Nguyen (2019)、Della Vedova et al.、Hasbrouck & Seppi (2001) 的 slope 公式来自聚合站 `frds.io/measures/limit_order_book_slope/` 的排版复述（该站给出 LaTeX 级公式，但未回核对原始期刊 PDF）；Hansen & Lunde (2006, JBES 24(2):127–154) 的噪声修正项、Lee & Ready (1991, JF 46(2):733–746) 与 Chakrabarty–Pascual–Shkilko (2015, JFM 25:52–79)、Theissen (2001)、Ellis–Michaely–O'Hara (2000) 的正确率数字，均来自检索代理读取的 RePEc/NBER/BoE 页面摘要，未逐字核对正文。

**两条给定引文无法核实（重要）**
1. **"Cont & Stoikov 2010, *A consistency-based order flow metric*"**：arXiv 与检索均无此标题；检索代理明确回复 the exact phrase "consistency-based order flow metric" does not appear anywhere in the Cont–Stoikov literature. 实际存在的同名年份论文是 **Cont, Stoikov & Talreja (2010), "A Stochastic Model for Order Book Imbalance", *Operations Research* 58(3), 549–563, DOI 10.1287/opre.1090.0780**（项目 inventory #47 已记此篇，标题记成"订单簿随机模型"）。OFI 的**唯一定义出处是 S1（arXiv:1011.6402，2010 年投稿 / 2014 年 JFEC 刊出）**，即项目已记的"CKS 2014"。→ 本审计以 S1 为 OFI 的唯一标准式，不假设存在第二个 CS2010 定义。
2. **"Humpage et al. 2015, Order Book Imbalance, arXiv:1502.07438"**：arXiv:1502.07438 是天文物理论文（*Iron and s-elements abundance variations in NGC5286*，A.F. Marino et al., 2015-02-26）；`https://arxiv.org/search/?searchtype=all&query=Humpage+order+book` 返回 **No search results were found**。→ 多层 OFI 标准式改用可核实的 S2（MLOFI）与 S3（integrated OFI）。
3. **"Egorov, Li & Xu 2016 (JF, 'Liquidity at mid') trade-based OFI"**：未找到任何 JF 论文匹配"Egorov Li Xu + liquidity + order flow imbalance"；Egorov–Li–Xu 在 JF 的已知论文是共同基金流动性转换方向。→ trade-based 标准式改用可核实的 S7（加密市场 aggressor-flag 的 buy-sell imbalance）+ S1（CKS 明确说他们**不做**订单类型判别）。

已吸收文献（CKS 2014 OFI、arXiv:2411.08382、arXiv:2602.00776、arXiv:2504.13521、Roll 1984、Hasbrouck 1991）按项目记录引用，不重复研究；本轮只做"代码 ↔ 定义"的对照。

---

## 1. 标准定义汇编

### 1.1 OFI 的事件级贡献 e_n（top-of-book, quote-based）

**出处**：S1 arXiv:1011.6402v3, §2.1 Variables。[一手]
> "We define the variable $e_{n}$ which measures the contribution of the $n-$th event to the size of bid and ask queues:
> $$e_{n}=I_{\{P^{B}_{n}\geq P^{B}_{n-1}\}}q^{B}_{n}-I_{\{P^{B}_{n}\leq P^{B}_{n-1}\}}q^{B}_{n-1}-I_{\{P^{A}_{n}\leq P^{A}_{n-1}\}}q^{A}_{n}+I_{\{P^{A}_{n}\geq P^{A}_{n-1}\}}q^{A}_{n-1}$$"

同页 §2.1 还给出**建模前提**（对本项目最关键的一句）：
> "We enumerate these observations by $n$ and compare with $n-1$. **Between two such observations, only one of the following events can occur**: …"（四类：需求增/需求减/供给增/供给减）

以及直觉定义（§1.1）：OFI "**increasing every time the bid size increases, the ask size decreases or the bid/ask prices increase** / **decreases every time the bid size decreases, the ask size increases or the bid/ask prices decrease**"，并且
> "Interestingly, this variable **treats a market sell and a cancel buy of the same size as equivalent**, since they have the same effect on the size of the bid queue."

**对本项目意味着**：`add_event_ofi` L148–153 的四个符号项、`>=`/`<=` 的双闭区间指标（价格不变时退化为 Δq）与 S1 逐项同构，**公式层面完全一致**；但"两次观测之间只发生一个事件"是**假设**，不是定理——项目输入是**快照（snapshot）**而非事件流，一次快照间隔里可能夹了 N 个订单事件（吃单+补单），此时 e_n 是 OFI 的下采样近似，必须按快照频率给出误差说明；同时"不需要判别订单类型"正是 CKS 的**设计卖点**，为项目"不推断方向"提供了直接文献背书（见 1.9）。

### 1.2 OFI 的窗口聚合（跨 bar 归属与 overlap）

**出处**：S1 §2.1。[一手]
> "Events affecting the order book occur at random times $\tau_n$, and we define $N(t)=\max\{n|\tau_n\leq t\}$ to be the number of events during $[0,t]$. We define the order flow imbalance over time intervals $[t_{k-1},t_{k}]$ as a sum of individual event contributions $e_n$ over these intervals:
> $$OFI_{k}=\sum_{n=N(t_{k-1})+1}^{N(t_{k})}{e_{n}},$$
> where $N(t_{k-1})+1$ and $N(t_{k})$ are the index of the first and the index of the last event in the interval $[t_{k-1},t_{k}]$."

配套的价格变化与被解释变量（同节、§2.3 式(2)、§3.1）：
> "$$\Delta P_{k}=(P_{k}-P_{k-1})/\delta,$$ where $P_{k}$ is the mid-quote price at time $t_{k}$ and $\delta$ is the tick size" ; "$$\Delta P_{k}=\beta\quad OFI_{k}+\epsilon_{k}, \tag{2}$$" ; "We use a uniform grid in time $\{t_{0},\dots,t_{N}\}$ with a timescale $t_{k}-t_{k-1}\equiv\Delta t=10$ seconds to compute the price changes and the order flow imbalances."

**对本项目意味着**：标准求和的**下标是 N(t_{k−1})+1**，即"窗口内第一个事件"必然计入（它的 e_n 用上一窗口最后一个事件的报价做参照）；每个事件**恰好归属一个窗口**，跨边界的只有"参照状态"，不是"贡献项"。项目 L274–275 的 `iloc[1:]` 正好把这一项丢了 → 定义性偏差（§2 表 R3、§4 修复①）。另外 CKS 用**均匀时间网格**做 OFI–ΔP 回归，说明"右闭右标 + 固定网格"在标准文献里是成对使用的（特征与同期价格变化同一标签），项目设计与此一致。

### 1.3 多层 / 加权 OFI（多层聚合的标准做法）

**出处 A（向量式）**：S2 arXiv:1907.06230v2, §3.1 式 (9)–(12)。[一手]
> $$\text{MLOFI}^m(t_{k-1}, t_k) := \sum_{\{n \mid t_{k-1} < \tau_n \leq t_k\}} e^m(\tau_n) \tag{11}$$
> $$e^m(\tau_n) = \Delta W^m(\tau_n) - \Delta V^m(\tau_n) \tag{12}$$
> （式(9)(10) 为 bid 侧 $\Delta W^m$ 与 ask 侧 $\Delta V^m$ 的三段式：价格上/平/下分别取 $r^m(\tau_n)$、$r^m(\tau_n)-r^m(\tau_{n-1})$、$-r^m(\tau_{n-1})$；ask 侧对称。）
> "Observe that the definition of MLOFI is very similar to the definition of OFI in equation (5), albeit extended to include order flow at the best $m=1,2,\ldots,M$ **occupied** price levels. **When $M=1$, MLOFI and OFI are identical**; when $M\ge 2$, MLOFI becomes a more general measure of order-flow imbalance."
> 脚注 3："Observe that we only count populated price levels, so it does not necessarily follow that $a^{m+1}(\tau_n)$ is exactly one tick greater than $a^{m}(\tau_n)$."

**出处 B（压成标量的标准做法）**：S3 arXiv:2112.13213 摘要。[一手]
> "we propose a systematic approach for **combining OFIs at the top levels of the limit order book into an integrated OFI variable which better explains price impact, compared to the best-level OFI**. … On the other hand, we show that **lagged cross-asset OFIs do improve the forecasting of future returns**."

**出处 C（放宽"一档一跳"）**：S4 arXiv:2112.02947 摘要。[一手]
> "This paper considers the change of **non-minimum quotation units** in real transactions, and proposes a generalized order flow imbalance construction method to improve Order Flow Imbalance (OFI) and Stationarized Order Flow Imbalance (log-OFI)."

**对本项目意味着**：(a) 多层聚合的标准形态是**逐层向量 + 回归系数**（S2）或**加权整合成"integrated OFI"**（S3），而不是把 5 层的量**等权相加**；项目 `depth_imbalance`（L256）把 level1 与 level5 等权，且窗口内先算比值再取均值，属于自造口径（低-中风险，见 R3/R6）。(b) S2 脚注 3 明确"**只数有挂单的价位**"，直接支持 §2 R1 的结论：空层价格 0 应该"按不存在处理"而不是整行丢弃。(c) S1/S2 的求和式都写成 $t_{k-1}<\tau_n\le t_k$（左开右闭），与项目 `closed="right"` 一致——右闭右标本身不是问题，丢首事件才是问题。

### 1.4 mid-price、micro-price、spread、imbalance 的基础定义

**出处**：S1 §2.1（mid-price 为被解释变量，见 1.2 引文）；S5 arXiv:2411.13594v1 §2。[一手]
> mid-price：$M=\frac{P_b+P_a}{2}$；spread：$S=P_a-P_b$（S1 用 tick 数 $\delta$ 归一）。
> 加权中间价："$$W = I P_a + (1-I) P_b$$" with "$$I = \frac{Q_b}{Q_b + Q_a}$$"（$Q_b$=best bid 量，$Q_a$=best ask 量）。
> micro-price（Stoikov 2018 原文的复述式）："$$P_{\text{micro}} = M + g(I,S)$$"，即 "the mid-price plus an adjustment term based on the imbalance $I$ and the spread $S$"。
> 对 mid 的批评（S5 转述 Stoikov 2018）："[1] claims the mid-price and weighted mid-price are common in finance, but they have **several drawbacks, including their high auto-correlation and lack of theoretical justification as true estimators of asset value**"；"However, this [weighted price based on current spread and imbalance] is **rarely a true reflection of the next price** as order sizes tend to be amended or even canceled completely due to reasons such as market spoofing or informed market taking."
> 归一化多层量占比（S5）：$V_{\text{total}}=\sum_{i=1}^{L}A_i+\sum_{i=1}^{L}B_i$，$P_{A,i}=\frac{A_i}{V_{\text{total}}}$，$P_{B,i}=\frac{B_i}{V_{\text{total}}}$。

**对本项目意味着**：项目 L248–250 用 $(P_b+P_a)/2$ 作 mid、$(P_a-P_b)/M\times10^4$ 作 bps 价差，**与 S1/S5 一致**（恒等式 $(A-B)/M=2(A-B)/(A+B)$，即"relative quoted spread"）；imbalance 项目用 $(Q_b-Q_a)/(Q_b+Q_a)$，与 S5 的 $I=Q_b/(Q_b+Q_a)$ 只差一个仿射变换 $2I-1$，**无实质偏差**。真正缺的是 micro-price：项目所有价格类特征都建立在 mid 上，而 S5 说明 mid 在高失衡/宽价差时是"下一价格的较差估计"——这是**可选增强**，不是错误（CKS 的回归本身就用 mid，故与 S1 完全对齐）。

### 1.5 realized variance / realized volatility（1 分钟窗口内高频收益平方和）

**出处（定义与构造）**：S6 arXiv:2602.19732v1 §5.1.4。[一手]
> "The plain vanilla realized variance ([Andersen and Bollerslev, 1998]; [Andersen et al., 2003]) is defined as
> $$rv=\sum_{i=1}^{m}r_{i}^{2},$$ where $r_{i}=\ln(p_{i}/p_{i-1})$ denotes the return of the $i$-th interval. Under the assumption of no jumps, it provides a consistent estimator of the integrated variance $IV=\int_{0}^{T}\sigma_{u}^{2}du$ as the sampling frequency increases."
> §5.1: "All realized measures are computed using **returns on equally-spaced intervals, typically at 1-minute or 5-minute frequencies**." ; "To ensure estimation reliability, realized measures are computed only for trading days with **at least 40 intraday observations** or with trading activity spanning less than two hours."

**出处（tick → 规则网格）**：S6 §4.4（完整引文见 §3 参照系 B）。[一手]
**出处（噪声偏差项，[二手]）**：Hansen & Lunde (2006, JBES 24(2):127–154) 的自协方差修正形式 $\mathrm{RV}+2\sum_i r_i r_{i-1}$（检索代理给出的转述，未逐字核对正文）；S6 §4.4 亦称等间隔采样 "helps in reducing the impact of market microstructure noise (Gençay et al., 2001; Hansen and Lunde, 2006; Bandi and Russell, 2008)"。

**对本项目意味着**：(a) `realized_mid_vol = sqrt(Σ r²)` 里的 r 是相邻**快照**的 log mid 差（L258 `np.log(mid).diff()` 在整条序列上求差分，再在窗口内 dropna 求平方和），因此**收益个数 m 每窗口不同**且**不等间隔**；标准做法是先等间隔重采样再求 RV，理由是降噪。(b) 中价一跳一跳存在**负一阶自相关（买卖报价弹跳）**，未修正的 tick 级 RV 期望被抬高，抬量 ∝ 快照数 → 特征里混进"活跃度"。项目用 mid 而非成交价是对的（成交价弹跳更严重），但**没有做任何降噪/归一**。(c) `sqrt(Σ r²)` 与"方差"相差一个平方：文献里 rv 是**方差口径**，取 sqrt 是波动率口径——这不是错，但项目**特征用 sqrt(Σr²)、标签用 std(ddof=0)（含去均值且除以 √h）**，两套归一化不同（见 §4 修复②）。

### 1.6 spread 的 bps 约定

标准式见 1.4（$2(A-B)/(A+B)$）。项目 L250 `(best_ask - best_bid)/mid.replace(0,np.nan)*1e4` **一致**。[一手=S5 的 $S=P_a-P_b$ + mid 定义；bps 化乘 1e4 属行业惯例，未核到期刊正文级定义 → 该项标注为"惯例，未见一手定义"]
**窗口聚合的偏差**：项目对**比率**取算术均值（L276）。比率均值受小 mid 的样本主导、且分母含 0 时给 NaN，文献里更常见的是先聚合再取比或直接报告 tick 数价差（S1 用 $\delta$ 归一的整点数）。→ 低风险、需说明口径。
**`spread_bps_std` 用 ddof=0**（L277）：样本标准差惯例是 ddof=1；小样本窗口（1–2 个快照）下 ddof=0 会把"单点窗口的价差波动"报成 0（实测：`spread_bps_std=0.0` 而该窗口只有 1 个快照）。→ 低风险但会静默造假数据。

### 1.7 book slope（"这个是否标准？"→ 是标准的，但项目实现的不是它）

四种可查到的标准式全部是 **volume 与 price 的比值（深度供给曲线的斜率）**：
- Næs & Skjeltorp (2006, *JFM* 9(4):408–432)，[二手=frds.io 复述]：$\text{Bid Slope}=\frac{1}{N^B}\{\frac{v^B_1}{|p^B_1/p_0-1|}+\sum_{\tau=1}^{N^B-1}\frac{v^B_{\tau+1}/v^B_\tau-1}{|p^B_{\tau+1}/p^B_\tau-1|}\}$，其中 $v^B_\tau=\ln(\sum_{j=1}^{\tau}V^B_j)$ 是**累积量的对数**，$p_0$ 为中间价；$\text{LOB Slope}=(\text{Bid}+\text{Ask})/2$。
- Ghysels & Nguyen (2019, *JRFM* 12(4):164，**比特币交易所**），[二手=frds.io 复述]：$QP_{it\tau}=\alpha_i+\beta_i|P_{it\tau}-m_{it}|+\varepsilon$，$\beta_i$ 即斜率（累积深度对价格距离回归）。
- Della Vedova, Gao, Grant & Westerholm（WP），[二手=frds.io]：$\text{Bid Slope}=\sum_{x=1}^{K}\text{Bid Depth}_{itx}/|\text{Bid Price}^K_{it}-m_{it}|$。
- Hasbrouck & Seppi (2001, *JF* 56(4))，[二手=frds.io]：$\text{Quote Slope}_k=\frac{A_k-B_k}{\log N^A_k+\log N^B_k}$（唯一把价格在分子上的变体，**分母仍是量**）。

项目 L259–263：
```
book_slope = ((bid_price_0 - bid_price_4) + (ask_price_4 - ask_price_0)) / (ask_0 - bid_0) / 2
```
**分子分母全是价格，一个量的信息都没有**。实测：每层间隔 1 元的书给出 `book_slope_mean = 4.0`（恒等于层数−1 除以 spread 的倍数），把全部 5 层压到同一价格则得 0；spread 变大时该值机械地变小。
**对本项目意味着**：名字叫 slope 的特征实际是"**第 5 层离盘口的价格距离，以价差为单位**"，(i) 不是文献里的 book slope，(ii) 与 `spread_bps` 存在 1/x 的机械共线，(iii) 对深度完全盲（同价差、量差 100 倍的两本书给同一个数）。→ 定义性错误（不是"偏"，是"张冠李戴"），风险高。

### 1.8 快照率 / 更新强度

未见期刊级"标准式"。最近的标准概念是 CST 模型里的**事件到达强度**（Cont, Stoikov & Talreja 2010, *Operations Research* 58(3):549–563, DOI 10.1287/opre.1090.0780 [二手=出版商页]，即"queue-reactive"模型中 bid/ask 队列的 Poisson 强度 $\lambda^b,\lambda^a$）与 Sirignano & Cont (2019, arXiv:1803.02269，项目已吸收) 把时序/更新类变量作为普适特征。项目 L283 `len(g)/60` 就是 snapshot_count 的常数倍，**信息完全冗余**（与 snapshot_count 相关系数 1.0），并作为"率"混进特征表。→ 无标准可依，属自造；风险低（共线/伪区分度），但应显式声明。

### 1.9 逐笔侧：VWAP、量聚合、方向

**VWAP 标准式**（加密市场，BTCUSDT）：S7 arXiv:2608.26158v1 §IV-A。[一手]
> "Additional outputs available only from the tick pipeline include the volume-weighted average price $\mathrm{VWAP}=\sum_i(p_i q_i)/\sum_i q_i$ and the buy-sell imbalance $(V_{\mathrm{buy}}-V_{\mathrm{sell}})/(V_{\mathrm{buy}}+V_{\mathrm{sell}})$, where $V_{\mathrm{buy}}$ and $V_{\mathrm{sell}}$ are the dollar volumes attributable to buyer-initiated and seller-initiated trades respectively, **as identified by the aggressor-side flag in each trade record**."
> 并给出 K 线侧的近似误差："dollar volume is approximated as close price times total minute volume… This approximation **discards the intra-minute price path and introduces a systematic bias** relative to the exact tick-level computation."；"The approximation error is **proportional to intra-minute price volatility** and is largest during fast-moving markets where the closing price deviates substantially from the average transaction price."

→ 项目 L226 `notional_sum / volume_sum`（notional = price*volume，逐笔累加）**与标准式完全一致**，且正是 S7 说的"tick 管线才能算准"的那一项，实现正确。

**方向不推断是否合理**：**合理且有文献背书**，但要分清两件事。
1. 不推断（不用 tick rule/BVC 猜）——**对**。S1 逐字：OFI "treats a market sell and a cancel buy of the same size as equivalent, since they have the same effect on the size of the bid queue"（[一手]，即 CKS 刻意绕开订单类型判别，因为 TAQ 里认不出来）；[二手] 判别正确率的历史证据：Theissen (2001) 测得 Lee/Ready 式算法 **72.8%**、Ellis–Michaely–O'Hara (2000, *JFQA* 35(4)) 在 Nasdaq 真值上测得 quote rule 76.4% / tick rule 77.66% / Lee–Ready 81.05%、Chakrabarty–Pascual–Shkilko (2015, *JFM* 25:52–79) 结论 TR/LR 优于 BVC。**推断方向 = 引入 ~20–27% 的符号错误**，保守做法 justified。
2. 但**不要放弃已有的真值 flag**。S7 用的是"aggressor-side flag in each trade record"（[一手]），Binance 官方文档逐字给出该 flag 的真实语义（S8）：
   > `"m": true, // Is the buyer the market maker?`（aggTrade payload）
   > 官方解释表：`buyer(maker) × seller(taker) → m = true`；`buyer(taker) × seller(maker) → m = false`
   也就是说**字段标识的是 maker 侧，不是 aggressor 侧**，方向与"买方主动"相反。项目 L195–197 只把 `side` 归一为 `buy/sell/b/s`，然后 L216 直接 `buy → +volume`，**没有任何参数声明这个 side 是 aggressor 还是 maker**（而 `normalise_kline` L303 对 K 线时间戳语义明确"never guesses"）。→ 语义风险高（符号可能整体反号，而符号反向在回归里表现为"OFI 系数为负"这种看起来仍可解释的结果）。

**imbalance 的分母**：标准式 $(V_{buy}-V_{sell})/(V_{buy}+V_{sell})$ 的分母是**已判定的买卖量之和**（S7 [一手]）。项目 L232 用 `row["signed_volume"]/row["volume_sum"]`，`volume_sum` 含 `side` 缺失的成交 → 实测（6 笔各 10，其中 1 笔 side 缺失）：`signed_volume=10, volume_sum=60, signed_volume_imbalance=0.1667`，而标准口径是 10/50 = **0.20**。稀释比例 = 未判定量占比，非平稳 → 中风险。

### 1.10 未来标签（forward return / future RV）

- forward log return：$\frac{1}{h}\log(P_{t+h}/P_t)$ 或 $\log(P_{t+h}/P_t)$（项目用后者，[一手] 同 S1 的 $\Delta P_k$ 思路、S6 的 $r_i=\ln(p_i/p_{i-1})$）。项目 L367 `np.log(future_close/out["close"])` **一致**。
- future RV：按 S6 式应为 $\sum_{i=1}^{h} r_{t+i}^2$（方差口径）或其平方根。项目 L371 用 `std(ddof=0)`（**先对样本去均值**再除以 $\sqrt{h}$）。实测 h=3：`target_realized_vol[0]=0.020490` vs $\sqrt{\sum r^2}=0.037286$，比值 0.5496 ≈ $1/\sqrt3$（且还含去均值项）→ 与特征端 `sqrt(Σr²)` 口径不同；**h=1（默认值）时 `target_realized_vol` 整列恒等于 0.0**（实测 8 行全 0，见 §2 R8）。

---

## 2. 逐函数对照表

（R1–R8；"偏差"精确到行号与实测数字。修复列只给方向，代码见 §4。）

| # | 函数 | 实现的标准(引用) | 完全一致? | 偏差（精确到代码行行为） | 修复建议 | 理论风险 |
|---|---|---|---|---|---|---|
| R1 | `clean_orderbook` (L71–126) | S2 脚注 3"只数 populated 价位"[一手]；crossed/locked 处理无统一标准 | 否 | ① L107 `positive_prices` 要求 5 层价格全 >0：vendor 对空层填 0（Binance depth 流只给有单层级，导出时常见 0 填充）→ **实测 4/4 行全部以 `dropped_bad_price` 丢弃**，整段盘口历史归零且不报错（只进 report 计数）。② L109 `not_crossed = bid_p[:,0] < ask_p[:,0]` 严格小于：锁定价盘口(bid==ask) **实测 3/3 全丢**；锁定虽罕见但是真实状态，被当成脏数据。③ L108 `ordered_book` 允许相邻层价格相等（`>=`/`<=`），于是"5 层重复同一价格"这类明显异常被当合法保留（正是 §1.7 的 `book_slope=0` 来源）。④ L120 `drop_duplicates(keep="last")` 在 `sort_values("event_time")`（稳定排序）后取输入顺序的最后一条：语义是"同一微秒内取 vendor 最后一条"，但**跨快照顺序未定义时 OFI 会被该选择改变**（队列 10→50 与 50→10 的 e_n 符号相反），报告里也只记一个总数。⑤ 无"时间断裂/停牌/采集缺口"检测：跨 3 小时缺口的相邻两条快照仍按"一次事件"计算 e_n（见 R2）。⑥ 无 tick-size 对齐检查（价格是 vendor 原值），与 S1 用整 tick 数归一的口径不可比。 | 把"层级不足"与"数据非法"分开：空层（price≤0 且 volume==0）→ 记为缺失并把该层从 ordered_book/positive 检查中剔除（或 `levels` 逐行取有效层数），只有**有效层内部**乱序/负价才丢行；锁定盘口单列计数（`dropped_locked`）而不是混进 `dropped_bad_price`；`not_crossed` 改为 `<=` + 单独统计 locked；加"最大快照间隔"参数并在超长处打 `gap_flag`（供 R2 复位）；dedupe 规则写进 docstring（保留 vendor 原始 index 的 last）。 | **高**（静默丢掉全部深度历史；锁定盘口/顺序选择不进入模型可见字段） |
| R2 | `add_event_ofi` (L128–156) | **S1 §2.1 e_n 公式** [一手] | **是**（公式逐字一致，含 `>=`/`<=` 双闭退化） | L148–153 四项与 1.1 引文逐项同构：`bp>=prev_bp)*bq − (bp<=prev_bp)*prev_bq − (ap<=prev_ap)*aq + (ap>=prev_ap)*prev_aq` ✔；`np.roll` + 首行自照（L147–149）使 e_1=0 ✔ 并由 L154 `ofi_valid` 标记 ✔。**但**：① 隐含假设 S1 的 "Between two such observations, only one of the following events can occur"——项目输入是快照，一条快照间隔内可有任意多订单事件（吃单后补单会**互相抵消**，e_n 系统性低估真实 OFI 绝对量），代码与 docstring 均未声明该假设或给出快照频率要求。② L154 `ofi_valid = np.arange(len)>0` 只对全序列第一条为 False：**数据缺口/session 边界后的第一条快照被当作"普通事件间增量"**，产生一个巨大且无意义的 e_n（例：隔夜跳空 → e_n ≈ 新 bid 队列 + 旧 ask 队列）。③ 无多层扩展（MLOFI 只取 level 0，与 S2/S3 的多层标准无关，属"只用 top-of-book"的选择而非错误）。 | 在 docstring 明确"本函数假设快照频率 ≥ 事件频率的采样，快照内多事件被抵消"；把 `ofi_valid` 扩展为 `prev 快照存在 且 (t_n − t_{n−1}) ≤ max_gap 且同一 session`（与 R1 的 gap_flag 联动）；缺位时 e_n=NaN + `ofi_valid=False`（让窗口聚合可区分"0 冲击"与"不可测"）；若要贴 S2/S3，可选加 `mlofi`（逐层向量输出）。 | 中（定义正确；假设与缺位语义未表达，尾部会产生极端离群值） |
| R3 | `aggregate_orderbook` (L237–287) | S1 §2.1 的 $OFI_k=\sum_{n=N(t_{k-1})+1}^{N(t_k)}e_n$ [一手]；S2 式(11) 左开右闭 [一手]；S6 §4.4/§5.1.4 [一手]；S5（spread/imbalance 口径）[一手] | 否 | ① **L274–275 `g["event_ofi"].iloc[1:].sum()` 丢掉每个窗口的第一条事件贡献**，与 S1/S2 的求和定义直接矛盾（标准只丢"全序列第一条"，已由 `ofi_valid` 表达，L274 却按窗口再丢一次）。实测 60 分钟 1 Hz 随机盘：**60/61 个窗口的 event_ofi 与标准值不同；平均相对误差 20%（中位 2%）；被丢项 |均值| = 窗口 OFI |均值| 的 10%；1 个窗口（2%）连符号都被翻转；corr=0.983。窗口越空（快照少）失真越大：只有 2 条快照的窗口 → 只剩 1 项。② **同一行内部口径自相矛盾**：`realized_mid_vol`（L270 `log_mid_return` 来自 L258 全序列 `.diff()`）**保留**跨左边界的那一条收益，而 `event_ofi` **丢弃**跨左边界的那一条事件——同一 cutoff 的两个特征对"边界事件算谁的"给出相反答案。实测：mid 在窗口起点后 1 秒跳 9.9% → `mid_return=0.000000`、`realized_mid_vol=0.094862`（同一行）。③ L279 `mid_return = log(mid_last/mid_first)` 是**窗口内部首尾差**，不是 S1 式 $\Delta P_k=(P_k-P_{k-1})/\delta$ 的"bar 到 bar 变化"，也不与 `mid_price_last` 自洽（`log(mid_price_last[t]/mid_price_last[t-1]) ≠ mid_return[t]`）；同时标签端用 K 线 close 的首尾差，两者定义域不同。④ L280 RV 用**逐快照不等间隔**收益、项数逐窗口浮动，未做任何等间隔化/降噪（S6 §4.4 明确要等间隔以降噪）；快照数与 RV 机械正相关 → 特征混入活跃度。⑤ **空/单点窗口返回 0.0 而非 NaN**：L274/275/280/279 在 `len(g)==1` 时分别给 0.0/0.0/0.0/0.0，实测单快照窗口 `mid_return=0, realized_mid_vol=0, spread_bps_std=0, event_ofi=0`——"无观测"被写成"零波动、零收益"（S6 用"至少 40 个日内观测"作门槛，项目把阈值设成默认 `min_snapshots=1`）。⑥ 首条快照恰好落在整分钟时，pandas 右闭 resample 会**造出一个宽度为 0 的伪窗口**（实测 cutoff `00:00:00`, `snapshot_count=1`）并进入输出表。⑦ L257 `log_mid` 计算后从未使用（死列）；L283 `snapshot_rate` 与 `snapshot_count` 完全共线（相关 1.0）。 | 求和改为按 `ofi_valid` 选取（保留窗口内全部有效事件，只排除全序列首条与缺位）；`mid_return` 改为"本窗口末 mid 相对**上一窗口末 mid**"（与 S1 的 ΔP_k、与标签的 close-to-close 同一口径），并保留一个 `mid_within_return` 作诊断；`realized_mid_vol` 前先按固定子网格（如 1s/5s）用 previous-tick 采样，或直接改为对等间隔 mid 序列求 RV，并把 0.0 与 NaN 分开（不足 `min_snapshots` 的窗口给 NaN，同时把 `min_snapshots` 提到与数据频率匹配的量级，如 ≥10）；丢弃宽度为 0 的首窗口；删除 `log_mid` 或在输出中声明保留理由；`snapshot_rate` 改名 `snapshot_count` 的派生并注明冗余。 | **高**（①②③④⑤ 都是定义级/口径级问题且会系统性改变特征分布与符号） |
| R4 | `clean_trades` (L158–200) | 无期刊标准；对齐 S7 的 "aggressor-side flag" 语义 [一手] | 否 | ① L195–197 把 `side` 归一为 `buy/sell`，**不声明它是 aggressor 还是 maker**；而 S8 的 Binance 字段 `"m": Is the buyer the market maker?` 标的是 maker（与 aggressor 相反）。项目对 K 线时间戳语义坚持"never guesses"（L303），对 trade side 却没有对应参数 → 语义空洞。② L188 `good_volume = volume >= 0` 允许 0 量成交通过，之后 L226 VWAP 依赖 `volume_sum>0` 兜底（可，但 0 量记录应计数）。③ 保留同时间戳多笔（L169 docstring 与 L199 不 dedupe）**正确**（trade 时间戳是事件时间）。④ 没有 trade-id 去重（aggTrade 有 `a` 聚合 id，重复导出会静默翻倍 volume），也没有把成交价与同刻盘口 bid/ask 交叉校验（成交价在价差之外/盘口之间的记录不检出）。 | 增加 `side_semantics: Literal["aggressor","maker","absent"]` 必填参数（对齐 `timestamp_semantics` 的设计哲学），maker 语义时内部翻号；加可选 `id_col` 去重并计数；加可选"成交价是否落在同刻 [bid,ask] 内"的诊断计数（只报不删）。 | **高**（①为符号级错误，一旦上游给的是 `is_buyer_maker`，`signed_volume` 全序列反号且不会报错） |
| R5 | `aggregate_trades` (L203–234) | S7 §IV-A VWAP 与 buy-sell imbalance [一手] | 部分一致 | ① VWAP/量/笔数/首末价（L224–228）与 S7 一致 ✔（含 `volume_sum>0` 的 NaN 兜底）。② L232 `signed_volume_imbalance = signed_volume/volume_sum`：**分母含未判定成交**，S7 的分母是 $V_{buy}+V_{sell}$。实测 1/6 笔 side 缺失 → 0.1667 vs 标准 0.20（稀释 17%），且稀释率随时间变化 → 非平稳。③ L231 `sum(min_count=1)`：全部未判定时给 NaN ✔，但"部分判定"与"全部判定"不可区分——没有输出 `classified_volume_share`。④ L219 `len(group) < min_trades: continue`：整窗消失（与 R3⑤ 同类），下游 `hf_available` 仍可能 True（见 R7）。⑤ 无 side 缺失率上限、无 cross-bar 归属说明（与 R3 同一 resample 语义，右闭 ✔）。 | 分母改成"已判定买卖量之和"（并单独输出 `classified_volume_share` 供质量门），未判定占比过高时把该行 imbalance 置 NaN；把空窗口的行保留为 NaN（不要 `continue`）以便与 K 线一一对应；显式声明 imbalance 用 base-volume 还是 dollar-volume 口径（S7 用 dollar）。 | 中（②为非平稳测量误差；④造成下游静默错配） |
| R6 | `normalise_kline` (L290–333) | 无外部公式；S7 对 K 线近似的警告 [一手]；S6 的右端点标签惯例 [一手] | 基本一致（本模块最规范的一段） | ① `timestamp_semantics` 显式二选一 + 不加猜测（L302–303, L323–326）与 S6"Each interval is labeled using the right endpoint"**同向** ✔。② 但 `assume_tz` 默认 `"Asia/Shanghai"`（L294）与 `clean_orderbook`/`clean_trades` 默认 `"UTC"`（L75/L165）**不一致**：调用方漏传时，naive 时间戳会被分别按两个时区解释，造成 8 小时系统性错位；且 `align_features_to_kline` 在 `tolerance=None` 下照样 join 成功（实测 3 小时前的特征 `hf_available=True`）→ 组合后果是"整表特征全为陈旧值但看起来齐全"（见 R7）。③ L315–321 的有效性掩码只检查 OHLCV 数值与 high/low 包络，**不检查 `bar_time` 是否为 NaT**（`tz_localize(..., ambiguous="NaT", nonexistent="NaT")` 在 L61 可产生 NaT），NaT cutoff 会静默进入输出（未用真实 DST gap 触发，仅代码路径分析）。④ 未做 bar 完整性检查（缺分钟不补），而 `make_future_labels` 的 `shift(-h)` 依赖连续网格 → 与 R8③ 联动。 | 把 `assume_tz` 默认改为必填或统一默认，并在返回表里带上 `source_tz`/`semantics` 元数据列；掩码加 `bar_time.notna()`；输出 `expected_bars vs actual_bars` 的缺口统计（供 R8 判断 horizon 是否被拉长）。 | 中（②③是数据完整性/时区耦合风险，函数本身语义无错） |
| R7 | `align_features_to_kline` (L336–356) | S6 右端点标签 + past-only 对齐；S1 的"同期"配对思路 [一手] | 否 | ① **多资产直接崩溃**：L345 `left.sort_values(["asset_id","cutoff_time"])` 使 `cutoff_time` 全局非单调，而 `merge_asof` 要求 on-key 全局单调 → 实测两个 `asset_id` 时抛 `ValueError: left keys must be sorted`（单资产正常）。本函数签名带 `by="asset_id"`、`normalise_kline` 会写 `asset_id`、`make_future_labels` 按资产分组，**多资产是设计意图，但这条路 100% 跑不通**。② L348 当 features 缺 `asset_id` 且 kline 有多资产时，把 features 标成字面量 `"asset"` → 与任何资产都不匹配（若①不崩，结果会是"全 NaN 特征 + hf_available=False"的静默失败）。③ **staleness 不设限**：`tolerance` 默认 `None`（L340, L351–352），`direction="backward"` → 实测 cutoff 与特征相差 **3 小时**仍成功 join，`hf_available=[True,True,True]`、`snapshot_count=59` 被当作当期特征使用；对 1 分钟标签而言这就是"用 3 小时前的微观结构预测下一分钟"，信息衰减但字段完好，模型不会报错。④ L354–355 `hf_available = notna().any(axis=1)`：只要有**任一**特征非缺失就算可用，既不看staleness也不看完整度（例如只有 `mid_price_last` 非 NaN、其余全缺，仍 True）。⑤ 右闭右标下 kline cutoff 与 feature cutoff 理论上**应精确相等**，用 as-of backward 而非等值 join 使"缺窗口"被悄悄回退成旧窗口（R3⑤/R5④ 的空洞在这里被掩埋）。 | 逐资产分组做 `merge_asof`（或先把 left 按 cutoff 全局排序再 `by=`）并加断言；`tolerance` 默认改为窗口长度（1 个 bar，最多 2 个 bar），超限即 NaN；输出 `feature_age_ms` 与 `n_features_present/n_features_total`，`hf_available` 由"age 在容差内 **且** 完整度≥阈值"决定；当 cutoff 应精确相等时优先等值 merge，as-of 只作为显式放宽。 | **高**（②③是"看起来正常、实际用旧信息"的路径，直接污染训练集） |
| R8 | `make_future_labels` (L359–373) | forward log return：与 S1/S6 的 log 口径一致 ✔；future RV：S6 §5.1.4 $rv=\sum r_i^2$ [一手] | 否 | ① **默认 horizon=1 时 `target_realized_vol` 整列恒为 0.0**（实测 8 行：全 0.0，仅末行 NaN）。机理：`r.shift(-1).rolling(1).std(ddof=0)` 对单样本的 ddof=0 标准差 = 0，再 `shift(0)` → 恒 0。默认参数即产出**零方差标签**，任何用它训练波动率头/做 GARCH 残差检验都会静默退化。② 口径与特征端不一致：L371 的 `std(ddof=0)` 先**去均值**并除以 $\sqrt{h}$，而 S6 的 RV 是 $E[r^2]$ 型不去均值；实测 h=3 得 0.020490，标准 $\sqrt{\sum r^2}$ 得 0.037286（比值 0.5496≈1/√3）。特征 `realized_mid_vol`=√Σr² 与标签 std 相差 √h 且一个含均值扣除 → 模型必须额外学一个与 horizon 相关的尺度。③ `shift(-horizon)` 在**时间索引上做行位移**（L366–367）：K 线缺分钟（R6④）时，标签实际跨 >1 分钟，但列名仍叫 `target_log_return`（horizon=1），标签分布被离群间隔污染。④ 窗口归属本身正确（实测推导与 `r.shift(-1)→rolling(h)→shift(-(h-1))` 的组合确实覆盖 $r_{t+1..t+h}$ ✔，末 h 行为 NaN ✔），与特征窗口 (c−Δ, c] 无重叠、无未来信息泄漏 ✔。 | 单样本情形显式返回 NaN（`min_periods` 保持 h，但把 ddof=0 的一元退化改成显式判空），或对 horizon=1 直接输出 $\lvert r_{t+1}\rvert$/√RV 并改名；标签与特征统一到同一口径（都用 √Σr² 或都用 std，docstring 写明 $\sqrt{\cdot}$ 是波动率而非方差）；在按 `cutoff_time` 重建成**完整分钟网格**后再 shift（或给 shift 加时间校验 `cutoff[t+h] − cutoff[t] == h·Δ`，不满足则 NaN）；`horizon` 建议改为必填。 | **高**（①是默认参数直接产坏标签；③会让"1 分钟标签"语义失效） |

**"偏差"非空的行数：8 / 8**（其中理论风险=高：R1、R3、R4、R7、R8 共 5 行；中：R2、R5、R6；无一行"完全一致"）。

---

## 3. 窗口与标签约定的标准做法（2–3 个参照系）

**结论先说**：项目的"**右闭 + 右标**"（窗口 (c−Δ, c]，特征记在 c）是微观结构文献的**主流做法**，不是自造；但"丢掉窗口内第一个事件"在任何参照系里都**没有依据**，且项目内部两个特征对边界处理互相矛盾（R3②）。

**参照系 A — CKS 2014（arXiv:1011.6402 §2.1/§3.1）** [一手]：$N(t)=\max\{n\mid \tau_n\le t\}$，$OFI_k=\sum_{n=N(t_{k-1})+1}^{N(t_k)}e_n$，$\Delta P_k=(P_k-P_{k-1})/\delta$，"We use a uniform grid in time … with a timescale $t_k-t_{k-1}\equiv\Delta t=10$ seconds"。
→ cutoff 语义：**右闭、右标、特征与被解释变量同期**（同一 $t_k$ 标签）；每个事件只计一次，窗口只切分"贡献"，**参照状态允许跨窗**；网格是均匀时间的（不是"事件数固定"）。这正是项目 `resample(label="right", closed="right")` 想要的形状；项目唯一多出来的是"每窗再丢一条"。

**参照系 B — VOLARE（arXiv:2602.19732 §4.4）** [一手]：
> "we adopt the previous-tick approach, which selects the last observed price before or at the end of each fixed-time interval. If no price is recorded within a given interval, the price from the previous interval is carried forward. (Barndorff-Nielsen et al., 2009). … **Each interval is labeled using the right endpoint, ensuring that the upper boundary of the interval is included in the aggregation.**"
> §5.1: "All realized measures are computed using returns on **equally-spaced intervals**, typically at 1-minute or 5-minute frequencies" ；"computed only for trading days with **at least 40 intraday observations**"。
→ 三点直接对表：① 右端点标签 + 上界包含 = 项目 ✔；② 空窗**前值延用**（carried forward）而非丢行 = 项目 ✘（L268/L219 丢行 + R7③ 无容差）；③ 波动率类量在**等间隔**价格序列上算，且有观测数门槛 = 项目 ✘（逐快照 + min_snapshots=1）。项目"不 fill"作为**防泄漏**立场是站得住的（它宁可 NaN），但必须与 R7 的"tolerance=None 的 backward 会把 fill 偷偷做回来"配套修好，否则"不 fill"只是名义上的。

**参照系 C — 事件驱动信息棒（arXiv:2608.26158 §IV，加密 Binance aggTrade）** [一手]：
> "Each bar type maintains a running accumulator of its activity signal across successive observations (minutes or ticks), **closing a new bar when the accumulated signal first reaches the adaptive threshold** $\hat\theta_n$ …, subject to the duration bounds $[d_{\min},d_{\max}]$. **At bar closure**, all standard OHLCV fields are recorded alongside the accumulated bar size, bar return, …"
> §I-A（对固定 1 分钟窗的批评）："Partitioning such a process into fixed one-minute windows forces the analyst to treat an interval of five hundred high-velocity trades during a volatility spike identically to an interval of two passive fills during a quiet overnight session, a conflation that is theoretically unjustifiable and statistically damaging."
→ 含义：加密文献里同样"以闭合事件为标签"（右标），并且**显式把"每窗观测数不同"当作时间棒的已知缺陷**。项目的对应物就是 `snapshot_count`/`trade_count`：把它们保留是对的，但 R3⑤ 让 2 快照窗返回 `realized_mid_vol=0.0` 恰好把该缺陷坐实成"0 波动"的假样本。→ 建议：0 长度/超稀疏窗一律 NaN，并把 S6 的"观测数门槛"变成可调参数。

---

## 4. Top 3 修复（按理论风险排序）

**① 把 OFI 的窗口求和恢复成标准定义，并统一窗口左边界的口径**（对应 R3①②③；风险=高；文献 S1 式 $OFI_k=\sum_{n=N(t_{k-1})+1}^{N(t_k)}e_n$、S2 式(11)）
改动描述：`aggregate_orderbook` 内不再按窗口位置切 `iloc[1:]`，改为**按 `ofi_valid` 逐事件筛选后整窗求和**（全序列首条、以及缺口/session 边界后的首条由 R2 的新 `ofi_valid` 置 False），`event_ofi_abs` 同理；同时把 `mid_return` 从"窗口内首尾差"改为"本窗末 mid 相对上一窗末 mid 的变化"，使 OFI、mid 变化、RV 三者对"左边界归谁"给出同一个答案。验收：把 `mid_return[t]` 与 `log(mid_price_last[t]/mid_price_last[t−1])` 对齐；在同一数据上比较新旧 `event_ofi`，实测基线为"60/61 窗不同、平均相对误差 20%、2% 窗符号翻转、被丢项 ≈ 窗口 OFI 量级的 10%"，改后应为 0 差异（仅全序列首条除外）。**这条最优先**，因为 OFI 是项目微观特征清单里的锚点变量，且它是**可证明的**定义偏离（不是口径偏好），审稿人一眼可查。

**② 统一并显式化"波动率"口径，消灭 horizon=1 的零方差标签**（对应 R8①②③ + R3④⑤；风险=高；文献 S6 §5.1.4 + §4.4）
改动描述：特征端先把 mid 按固定子网格（1s 或 5s）previous-tick 采样，再在窗口内求 $rv=\sum r_i^2$，输出保留 `rv`（方差）与 `rv_sqrt`（波动率）两列或明确声明取哪一口径；单快照/低于观测门槛的窗口返回 NaN 而不是 0.0。标签端把 `target_realized_vol` 改成与特征端同一算子（未来 h 根 bar 的 $\sqrt{\sum r^2}$），显式处理 h=1 的退化（不得输出 0），并**在完整时间网格上 shift**（缺 bar 时把标签置 NaN 或按实际时间跨度重算 horizon）。这条同时消除"特征与标签尺度差 √h + 一个均值扣除"的系统性偏，使波动率头的评估与 §理论信息预算推导可比。

**③ 把"方向语义"与"新鲜度"变成必填/有界参数**（对应 R4① + R7②③④⑤ + R8 的崩溃路径；风险=高；文献 S8 Binance `"m": Is the buyer the market maker?` + S7 "as identified by the aggressor-side flag"）
改动描述：(a) `clean_trades` 增加与 `timestamp_semantics` 同风格的必填 `side_semantics ∈ {aggressor, maker, absent}`，maker 时翻号，`absent` 时不产出 signed 列；imbalance 分母改为已判定量之和并输出 `classified_volume_share`。(b) `align_features_to_kline` 逐资产 merge（修 `left keys must be sorted`），`tolerance` 默认设为 1 个 bar，输出 `feature_age_ms` 与特征完整度，`hf_available` 由 age+完整度共同决定。(c) 多资产但 features 无 `asset_id` 时**直接报错**而不是填 `"asset"`。理由：这三处的共同特征是"错了也不报错、且错得很像正常数据"——符号反号与 3 小时前的旧特征都能生成完整的训练矩阵，属于最难在实验里被发现、却能让全部实证结论反向的一类。

---

## 5. 未能核实的点（诚实列出）

1. **三条给定引文不存在/无法定位**（详见 §0）："Cont & Stoikov 2010, A consistency-based order flow metric"（该措辞不存在于 Cont–Stoikov 文献；OFI 唯一定义出处为 arXiv:1011.6402）、"Humpage et al. 2015 Order Book Imbalance, arXiv:1502.07438"（该 ID 是天体物理论文；arXiv 作者检索 0 结果）、"Egorov, Li & Xu 2016 JF, Liquidity at mid"（未找到任何 JF 匹配）。**若项目文档已写入这三条，需要撤稿或改引。**
2. **CKS 2014 的"Joss 分解 / signed volume decomposition"这一名称**未出现在 arXiv:1011.6402v3 全文里（我逐字核对的 §2.1 只有 $e_n$、$OFI_k$、$\Delta P_k$、式(2)(4)）。可能指：(a) S2 的 $\Delta W^m-\Delta V^m$ 分解（式 9–12），或 (b) 按订单类型的分解。**未核实**，因此 §1.1/§1.3 只给可核对的原文，不引用"Joss 分解"这一说法。
3. **Andersen & Bollerslev (1997) 与 ABD (2003) 的原文公式未能逐字核对**：两份 PDF 已成功下载（`public.econ.duke.edu/~boller/Published_Papers/ecta_03.pdf`、`.../jf_97.pdf`），但本机无 `pdftotext`/pypdf/fitz，且为扫描图像无文字层 → §1.5 的 RV 定义与"等间隔/前值延用"约定改由 S6 [一手] 承载，ABD 只作为原始出处指针（[二手]）。AB97 的"按美元成交量重标时间轴"的具体公式未取到，故未用于本项目建议。
4. **Hansen & Lunde (2006) 的自协方差修正项**（$\mathrm{RV}+2\sum r_ir_{i-1}$）来自检索代理转述 [二手]，未逐字核对 JBES 正文；§1.5 因此只写"存在一阶自协方差修正"的方向性结论，不给可引用公式。
5. **Næs & Skjeltorp (2006) / Ghysels & Nguyen (2019) / Della Vedova et al. / Hasbrouck & Seppi (2001) 的 slope 公式**全部来自聚合站 frds.io 的 LaTeX 复述 [二手]；卷期页码与 frds.io 一致但我未能打开原始 PDF。**结论不受影响**（四种变体的分子/分母都含成交量，而项目实现完全不含量），但若要在论文里引 slope，必须先取到原始 PDF 核对。
6. **relative quoted spread 的"bps 标准定义"**未找到期刊正文级逐字定义（黄-斯托尔 1997 / Bessembinder 2003 的 PDF 均取不到文本），只有实务文档级表述 [二手/三手]。项目实现 $(A-B)/M\times10^4$ 与恒等式 $2(A-B)/(A+B)$ 相符，我判定为"与惯例一致"，但**不给一手引文**。
7. **snapshot rate（更新率）没有可引用的标准定义**，只找到概念相邻的 CST 2010 Poisson 强度 [二手=出版商页]；§1.8 因此只说"自造、冗余"，不能说"违反标准"。
8. **项目数据实际字段语义未核实**：`BTC_USDT` 订单簿/逐笔的导出脚本未在本轮读取，因此无法判定上游 `side` 到底是 aggressor 还是 `is_buyer_maker`（R4①的风险是否已经落地）、深度流的空层是否被填 0（R1①是否已经造成丢行）。→ 下一步应对着 `data/` 里的真实 parquet 跑 `clean_orderbook` 的 `report`，看 `dropped_bad_price/output_rows`。
9. **`normalise_kline` 的 NaT cutoff 路径未实测触发**（R6③）：我构造的时区日期不构成真实 DST gap，只做了代码路径分析（L61 可产生 NaT，L315–321 的有效性掩码不检查 `bar_time`），未声称已在生产数据中复现。
10. **R3① 的量化失真幅度依赖合成盘的激进度**：60/61 窗不同、平均相对误差 20%、符号翻转 1/61 是在"1 Hz、队列对数正态波动 σ=0.06、30% 概率改价"的合成书上测得；真实 BTC_USDT 的快照频率与队列波动不同，**失真会更严重**（真实快照远密于 1 Hz，但窗口内事件数与抵消也更少）。真实数据上的误差仍需在 `data/` 上重跑一遍量化。
