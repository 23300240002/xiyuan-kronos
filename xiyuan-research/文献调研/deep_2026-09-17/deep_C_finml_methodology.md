# Deep Research C · 防泄漏方法论与 TP13 基准规范（2026-09-17）

> 服务对象：(a) `scripts/hf_data_pipeline.py` 的 point-in-time 正确性审计；(b) TP13「预测时点 / purging / 预算」基准实验规范草案。
> 已按要求**排除**重复吸收：arXiv 2506.07928（波动率预测简单基准难超越）、arXiv 2511.18578（TSFM 金融适用性的数据侧质疑）。

---

## 0. 方法

**可达性：`web_fetch` 可用（未出现 NO_WEB_ACCESS）。**

### 0.1 成功抓取并逐字引用的源（★=本轮实际打开并取到原文）

| # | 源 | 类型 | 用于 |
|---|---|---|---|
| ★1 | https://www.corr.ai/docs/methodology/purged-cv-embargo | 机构方法论文档 [二手] | purge/embargo 形式定义、embargo 非对称性、1% 起点 |
| ★2 | https://ml4trading.io/docs/diagnostic/methods/cpcv/ | 开源库文档 [二手] | purge/embargo 一句式定义、`label_horizon`/`embargo_size` 参数语义 |
| ★3 | https://ppuertos.github.io/financial-ml-core/reference/model_selection/split/ | 开源库文档（明示实现 LdP Ch.7） [二手] | purge 的区间重叠判据公式、`pct_embargo` 默认 0.01 |
| ★4 | https://javiermeseguer.me/projects/fmlcv/purged_cv_python.html | 讲义 [二手] | purge/embargo 操作性定义、`t1_i = i+h` |
| ★5 | https://www.quantresearch.org/Innovations.htm | 作者团队自建站 [二手] | "K-Fold CV with Purging & Embargo" 的目的表述（labels overlap + serial conditionality） |
| ★6 | https://docs.databricks.com/aws/en/machine-learning/feature-store/time-series | 官方文档 [一手(工程标准)] | point-in-time correctness、AS OF join、8:50/8:52 泄漏例 |
| ★7 | https://learn.microsoft.com/en-us/azure/machine-learning/offline-retrieval-point-in-time-join-concepts | 官方文档 [一手(工程标准)] | `source_delay`、`temporal_join_lookback`、stale feature |
| ★8 | https://www.hopsworks.ai/dictionary/point-in-time-correct-joins | 官方词典 [一手(工程标准)] | ASOF LEFT JOIN 定义、label leakage、多管道异频更新 |
| ★9 | https://pandas.pydata.org/docs/reference/api/pandas.merge_asof.html | 官方文档 [一手] | `direction='backward'` = "less than or equal to"；`tolerance`；排序要求 |
| ★10 | https://nightlies.apache.org/flink/flink-docs-stable/docs/concepts/time/ | 官方文档 [一手] | event time vs processing time、`Watermark(t)` |
| ★11 | https://arxiv.org/html/2207.07048v1 (Kapoor & Narayanan; 期刊版 Patterns 4(9):100804, 2023) | 论文 [一手] | L1.2 / L1.4 / L3.1 / L3.2 逐字定义、block CV、info sheet 三论证 |
| ★12 | https://ar5iv.labs.arxiv.org/html/1808.03668 (Zhang, Zohren & Roberts, DeepLOB, IEEE TSP 2019/2020) | 论文 [一手] | 标签=平滑中价方向、horizon k 以**事件数**计、归一化只用"前 5 天" |
| ★13 | https://ar5iv.labs.arxiv.org/html/1810.09965 (Tsantekidis et al.) | 论文 [一手] | k∈{10,50,100,200} LOB 事件、α 阈值配平类别、causal padding、按日滚动统计量归一化 |
| ★14 | https://ar5iv.labs.arxiv.org/html/2105.10430 (Zhang & Zohren, Multi-Horizon Forecasting for LOBs) | 论文 [一手] | 标签式 l_t=(m_+−m_−)/m_−、"in 'tick time', i.e. consecutive LOB updates"、时序不重叠 split |
| ★15 | https://otexts.com/fpp3/tscv.html + /accuracy.html (Hyndman & Athanasopoulos, FPP3) | 教科书 [一手] | rolling-origin 定义、naïve-scaled error |
| ★16 | https://arxiv.org/html/2512.12924v1 (Deep, Deep & Lamptey 2025) | 论文 [一手] | Definition 5 walk-forward 分区（W=252/H=63/Δ=63）、"information set discipline"、"not optimized on the test dataset" |
| ★17 | Corsi, F. (2009), *J. Financial Econometrics* 7(2):174–196，PDF: https://statmath.wu.ac.at/~hauser/LVs/FinEtricsQF/References/Corsi2009JFinEtrics_LMmodelRealizedVola.pdf | 论文 [一手] | HAR-RV 式(8)、式(3)(4)、年年化、moving window 1000 再估、基准族、MZ 回归式(11)(12)、周末剔除 |
| ★18 | https://portfoliooptimizer.io/blog/volatility-forecasting-har-model/ | 讲义 [二手] | HAR-RV 式与 5/22 日均、Corsi 引文核对 |
| ★19 | Barndorff-Nielsen, Hansen, Lunde & Shephard (2009), *Econometrics Journal* 12(3):C1–C32 摘要（pure.au.dk / ora.ox.ac.uk 记录） | 论文摘要 [一手] | 高频核估计、"local trends ... over periods of around 10 minutes" |

### 0.2 尝试但**未取得**（结论进 §4）

- `hudsonthames.org/purged-k-fold-cross-validation/` → 404；`www2.ciando.com` 出版社样章 PDF → 连接超时；SSRN 摘要/全文页（4686376、3104816、1138418、6752822 等）→ 403；SlideShare（LdP 讲义）→ 连接超时；`econ.duke.edu/~boller/...jfm_97.pdf` → 404；`api.semanticscholar.org` → 429（多次）；OpenAlex `title.search` 对 Kozlovskiy 面板 CV 论文与 "HARning OBV" → 空命中；arXiv 全文检索对 `"Leakage in Deep Learning-based Quantitative Trading Strategies"`、`"purged" cross-validation finance embargo` → 0 结果（该文/该措辞在 arXiv 检索不到，我不再凭记忆引用其编号：先前两次按记忆猜的 arXiv id 抓回来是**另两篇无关论文**，已在 §4 记为一次性教训）。
- 工具事实：本机 `pdftotext` 缺失（`read_file` 读 PDF 失败），改用 `pypdf`（已 `pip install --user`）成功抽取 Corsi (2009) 全文文本，故 ★17 的引文为原文逐字。

### 0.3 本地一手核对（代码 + 行为实验）

- 完整读 `scripts/hf_data_pipeline.py`（409 行）；`grep` 全仓 `merge_asof|train_test_split|TimeSeriesSplit|embargo|purge|ffill|interpolat`。
- 在 `pandas 2.3.3` 下对该模块跑 5 组**最小行为实验**（构造数据、断点定位），结果内嵌 §2（每条标注「实测」）。

---

## 1. 标准规则汇编

格式：**定义（英文原文逐字）→ 出处 → [一手]/[二手] → 适用条件 → 项目含义**。

### 1.1 Purging（清洗重叠标签）

**(R1) 一句话定义.** "Purging removes training labels that overlap a test period." — ML4Trading CPCV 文档 [二手]（明示转述 López de Prado 2018 Ch.7）。

**(R2) 形式判据（区间重叠）.** "let training observation i have label window [t_{i,0}, t_{i,1}] and test observation j have label window [t_{j,0}, t_{j,1}]. Observation i is purged if the intervals overlap — whether i's window ends inside j's, starts inside j's, or envelops it entirely." — Corr.ai 方法页 [二手]。开源实现给出的等价布尔式：
> "A training observation is purged if its interval \([t_{i,0}, t_{i,1}]\) overlaps with the test interval \([T_{j,0}, T_{j,1}]\): $$(t_{i,0} \le T_{j,1}) \land (t_{i,1} \ge T_{j,0})$$" — financial-ml-core `PurgedKFold` docstring [二手，自称实现 "Advances in Financial Machine Learning" (Chapter 7)]。

**(R3) 为什么重叠标签必须 purge.** "Standard K-Fold CV assumes IID data, which is false in finance due to overlapping labels and serial correlation." — financial-ml-core docstring [二手]；作者侧表述："CV method that prevents informational leakage from the testing set into the training set, due to labels overlap and serial conditionality." — quantresearch.org（LdP 团队创新列表）[二手]；操作解释："remove from the training set every observation whose label window overlaps the test set's window." — Meseguer 讲义 [二手]。
> **项目含义**：`target_log_return` 是 (c, c+h] 的前向收益 ⇒ 样本 i 的标签区间天然延伸到 i 之后 h 根 bar。任何把行打乱/随机 k 折的评估，都会让"训练行的标签"覆盖"验证行的 cutoff"，即训练标签里含验证集的答案 → TP13 的所有切分必须显式 purge。

**(R4) purge 的工程长度（推导，非引文）.** 若标签为 h 根 bar 的前向收益，测试块为 bar 区间 [T0, T1]，则 (R2) 等价于：**剔除训练集中 cutoff ∈ (T0 − h, T1] 的行**，即在测试块**左边界之前多砍 h 根 bar**；前瞻块右端之外 purge 不生效。
> 这是"purge 只管前向标签"的直接推论，也是 TP13 §3b 的公式来源。

### 1.2 Embargo（封口）

**(R5) 定义.** "An embargo can remove training observations immediately after a test period." — ML4Trading [二手]；"additionally drop a small block of training observations *immediately after* each test fold, to kill leakage through serial correlation that purging alone misses." — Meseguer [二手]。

**(R6) 非对称性（只封后面，不封前面）— 逐字.**
> "Note the asymmetry. The embargo applies only *after* the test interval. Leakage from before the test set travels through forward-looking label windows, and purging has already removed it. Leakage after the test set travels through backward-looking features, which purging cannot see." — Corr.ai [二手]。

**(R7) 长度取值.** "López de Prado suggests an embargo on the order of 1% of total observations as a starting point; the appropriate width ultimately depends on how persistent your features are — long trailing windows and slow-moving signals warrant wider embargoes." — Corr.ai [二手]。参数实现口径：`label_horizon` = "the number of observations used by each forward label"，且 `embargo_size` 与 `embargo_pct` 二选一（示例 `label_horizon=5` 配 `embargo_size=2`）— ML4Trading [二手]；`pct_embargo`: "Total timeline percentage for embargo. Defaults to 0.01 (1%)." — financial-ml-core [二手]。
> **精确陈述未取到**：书籍 §7.4.2 关于 "e ≥ ?" 的原文、以及任何 `e = (1+T)·test_size/(k−1)` 之类闭式，均**未在可访问文本中核实**（见 §4-U1）。本项目采用 §3b 的**可审计下界公式**（R4/R6 的直接推论）+ 1% 作为下限体检。

### 1.3 Point-in-time 正确性：available-at 时间 vs event 时间

**(R8) PiT 正确性定义（逐字）.** "Point-in-time correctness creates a training dataset that reflects feature values as of the time each label observation was recorded. This is important to prevent *data leakage*, which occurs when you use feature values for model training that were not available at the time the label was recorded." — Databricks Feature Store [一手(工程标准)]。
> 同一页给出失败模式的具象例子："this is not a valid observation for training, because the co2 reading of 630 was taken at 8:52, after the observation of the ground truth at 8:50. The future data is 'leaking' into the training set"。

**(R9) as-of 联结 = backward 最近一条（逐字）.** "In SQL, a PiT Join is an ASOF LEFT JOIN. That is, a point-in-time correct join is a temporal join between two tables where the output reflects the state of the both tables at a specific point in time defined by timestamps from the left table (containing the labels) ... every row in the output table containing the feature AS OF the value of the point in time of timestamp value from the label table." — Hopsworks [一手(工程标准)]；其目的表述："Ensuring that the features used for training are only derived from data available at the point in time corresponding to the label prevents label leakage."
> pandas 侧的实现语义："A 'backward' search selects the last row in the right DataFrame whose 'on' key is less than or equal to the left's key." — `pandas.merge_asof` 文档 [一手]。⇒ **`direction='backward'` 的 ≤ 语义就是 PiT 标准做法本身**，不是近似。

**(R10) 两个必须显式声明的时间参数（逐字）.**
> "For an observation event that has a timestamp `t` value, the feature value with the latest timestamp in the window `[t - temporal_join_lookback, t - source_delay]` joins to the observation event data." — Microsoft Learn（离线特征 point-in-time join）[一手(工程标准)]
> "An event that happened at time `t` lands in the source data table at time `t + x`, due to the latency in the upstream data pipeline. The `x` value is the source delay." + "When you train a model with offline data, without consideration of source delay, the model uses feature values from the nearest past. When you deploy a model to a production environment, the model only uses feature values delayed by at least the amount of source delay time. As a result, the predictive scores degrade."
> 上界侧（陈旧状态）："A search for feature values with time values that are too early impacts the query performance ... Feature values produced too early are stale. As model input, these values can degrade model prediction performance." + "If you don't set the `temporal_join_lookback` value, its default value is infinity. It looks back as far as possible during the point-in-time join."
> **项目含义**：本项目 = "不做插值/ffill 的 backward 最近邻"，恰好满足 R9 的下界语义，但 **`tolerance=None` 即 lookback=∞**，且完全没有 `source_delay` 概念（见 §2 偏差 B3/B5）。

**(R11) event time / processing time 与"窗口何时算完成"（逐字）.**
> "Event time is the time that each individual event occurred on its producing device. ... In event time, the progress of time depends on the data, not on any wall clocks." / "Processing time refers to the system time of the machine that is executing the respective operation." / "A *Watermark(t)* declares that event time has reached time *t* in that stream, meaning that there should be no more elements from the stream with a timestamp *t' <= t*." — Apache Flink 时间语义文档 [一手(工程标准)]。
> **项目含义**：右端标 `c` 的 1min 窗口只有在"不再有 ts ≤ c 的事件"时才是完备的。离线导出天然满足（若上游不回填/不改标），但**该假设必须写成断言**，否则 cutoff_time 混入 collection time 就等价于用 processing time 冒充 event time。

**(R12) 学术侧的时间泄漏定义（逐字）.** "[L3.1] Temporal leakage. When an ML model is used to make predictions about a future outcome of interest, the test set should not contain any data from a date before the training set. If the test set contains data from before the training set, the model is built using data 'from the future' that it should not have access to during training, and can cause leakage." — Kapoor & Narayanan (2022/2023) [一手]。
**(R12b) 全样本预处理的泄漏（逐字）.** "[L1.2] Pre-processing on training and test set. Using the entire dataset for any pre-processing steps such as imputation or over/under sampling." — 同上 [一手]。**高频侧的标准规避写法（逐字）**："we again use standardisation (z-score) to normalise our data, but use the mean and standard deviation of the previous 5 days' data to normalise the current day's data (with a separate normalisation for each instrument)." — DeepLOB [一手]；同族写法："normalisation statistics were calculated using previous day's data to avoid distribution shifts." — Tsantekidis et al. [一手]。

### 1.4 标签约定：horizon 的量纲、平滑与零 overlap

**(R13) 高频文献的 horizon 以「事件数」而非「墙上时钟」计（逐字）。**
> "The direction of the mid-price of that stock is defined as $l_k(t)=\{-1,0,1\}$ depending on whether the mid price decreased (-1), remained stationary (0) or increased (1) after $k$ LOB events occurred." + 实测网格 k ∈ {10, 50, 100, 200} — Tsantekidis et al. (arXiv:1810.09965) [一手]。
> "it studied five prediction horizons at k = (10, 20, 30, 50, 100) in 'tick time', i.e. consecutive LOB updates." — Zhang & Zohren (arXiv:2105.10430) [一手]；DeepLOB 的 LSE 数据集事件间隔："$\Delta_{k,k+1}$ is on average 0.192 seconds in the dataset" [一手] ⇒ k=10~100 事件 ≈ **2–20 秒**的时钟跨度。
> **项目含义**：本项目 horizon=1 个 1min bar（60 s）比 LOB 微观结构预测的常用时钟跨度**长 1–2 个数量级**，但比"日频/多日"任务短得多；它落在"中频单 bar 收益/波动率"任务带，而不是 DeepLOB 的 tick 带。故 horizon=1bar 本身不异常，异常的是**用 tick 级论文的精度期望去评价它**。

**(R14) 标签用「过去 k 均值 vs 未来 k 均值」的平滑比值，且特征/标签严格不重叠（逐字）。**
> "$l_{t}=\frac{m_{+}(t)-m_{-}(t)}{m_{-}(t)}$, $m_{-}(t)=\frac{1}{k}\sum_{i=0}^{k-1}p_{t-i}$, $m_{+}(t)=\frac{1}{k}\sum_{i=1}^{k}p_{t+i}$, where $k$ is the prediction horizon and $p_{t}$ is the mid-price" + "We compare $l_{t}$ with a threshold ($\alpha$) to decide on the label, and if $l_{t}>\alpha$, we label it as up or $l_{t}<-\alpha$ is a down. We label everything else as the stationary class" — Zhang & Zohren [一手]；DeepLOB 同族："Because financial data is highly stochastic, if we simply compare $p_t$ and $p_{t+k}$ to decide the price movement, the resulting label set will be noisy." [一手]。
> **项目含义**：$m_-$ 用到 t（含）为止，$m_+$ 从 t+1 开始 ⇒ **前向标签区间与特征区间零 overlap 是文献标准做法，不是本项目额外的保守设定**。α 阈值（DeepLOB/Tsantekidis 用其配平类别分布，约 20%/20%/60%）是**必须预注册的超参**，不得由测试集反推。

**(R15) 切分与前瞻的最低标准（逐字）。**
> "the first 7 days are used as the train data and the last 3 days as the test data. We split the last 20% observations from the train set as the validation set to optimise hyperparameters." / "...we take the first 6 months as training data, the next 3 months as validation data and the last 3 months as testing data." — Zhang & Zohren [一手]
> "To minimise the problem of overfitting to backtest data, we carefully optimise any hyper-parameter on a separate validation set before moving to the out-of-sample test set." — DeepLOB [一手]
> "First, it enforces strict information set discipline where features, signals, and execution decisions use only data available up to that point in time, preventing lookahead bias that pervades much backtesting research." + "Second, it employs walk-forward validation with rolling windows, where the system must prove itself repeatedly across 34 independent out-of-sample test periods spanning multiple market regimes rather than succeeding in one fortunate backtest." + Definition 5 的 "training window W=252 days, testing window H=63 days, and step size Δ=63 days" — Deep, Deep & Lamptey (arXiv:2512.12924) [一手]。
> "In this procedure, there are a series of test sets, each consisting of a single observation. The corresponding training set consists only of observations that occurred *prior* to the observation that forms the test set. Thus, no future observations can be used in constructing the forecast. Since it is not possible to obtain a reliable forecast based on a small training set, the earliest observations are not considered as test sets." + "This procedure is sometimes known as 'evaluation on a rolling forecasting origin' because the 'origin' at which the forecast is based rolls forward in time." — FPP3 §5.10 [一手]。

### 1.5 实体泄漏 / 跨资产 panel 的额外注意

**(R16) 实体非独立 = 泄漏（逐字）。**
> "[L3.2] Nonindependence between train and test samples. Nonindependence between train and test samples constitutes leakage, unless the scientific claim is about a distribution that has the same dependence structure. In the extreme (but unfortunately common) case, train and test samples come from the same people or units. ... The train-test split should account for the dependencies in the data to ensure correct performance evaluation. Methods such as 'block cross validation' can partition the dataset strategically so that the performance evaluation does not suffer from data leakage and overoptimism (Roberts et al., 2017; Valavi et al., 2021). Handling nonindependence between the training and test sets in general—i.e., without any assumptions about independence in the data—is a hard problem, since we might not know the underlying dependency structure of the task in many cases." — Kapoor & Narayanan [一手]
> "[L1.4] Duplicates in datasets. If a dataset with duplicates is used for the purposes of training and evaluating an ML model, the same data could exist in the training as well as test set." — 同上 [一手]

**(R17) 信息表三论证（预注册模板，逐字）。**
> "[L1] Clean train-test separation. The researcher needs to argue why the test set does not interact with training data during any of the preprocessing, modeling or evaluation steps to ensure a clean train-test separation." / "[L3] Test set is drawn from the distribution of scientific interest... The researcher needs to justify that the test set is drawn from the distribution of scientific interest and there is no selection or sampling bias in the data collection process." — 同上 [一手]；作者声称该模板可检出其综述里 329 篇（arXiv 版）/294 篇（Patterns 版）泄漏论文。
> 配套实践表述："These patterns were not optimized on the test dataset but represent common technical trading concepts from practitioner literature." + "Securities were selected according to pre-specified criteria..." — Deep et al. [一手]。

**(R18) HF→LF 同频跨模态采样的额外结论（本轮证据边界）。**
- 由 (R16)+(R5/R6)：panel 场景下**两个正交方向都要封口**——时间方向 purge+embargo（跨折标签/特征重叠），实体方向 group/block 切分（同一资产同时出现在 train 与 test 的相邻时刻；以及"同一资产同一时刻被 HF/K 线两条路径各引一次"造成的重复，即 L1.4 在高频里的具体形态）。
- 由 (R14)：跨模态时"特征窗口"= 两条模态各自 lookback 的并集 ⇒ embargo 按**最长那条**算（本项目即 TSFM 的 context 长度，见 §3b）。
- 专门的"金融 panel CV"论文（Kozlovskiy, *J. Portfolio Management*）**未能核实**（§4-U2）；HuggingFace 域不可达不影响本节。

### 1.6 基准（HAR-RV 与 1min 标签下的简单基准）

**(R19) RV 与 HAR-RV 精确公式（逐字，Corsi 2009 [一手]）。**
> 式(3)：`RV^(d)_t = sqrt( Σ_{j=0}^{M−1} r²_{t−j·Δ} )`, "where Δ = 1d/M, and r_{t−j·Δ} = p(t−j·Δ) − p(t−(j+1)·Δ) defines continuously compounded Δ-frequency returns, that is, intraday returns sampled at time interval Δ"。
> 式(4)（周成分）：`RV^(w)_t = (1/5)( RV^(d)_t + RV^(d)_{t−1d} + ⋯ + RV^(d)_{t−4d} )`，并注脚说明"a weekly realized volatility at time t is given by the average ... In order to allow direct comparison among quantities defined over various time horizons, these multiperiod volatilities are normalized sums of the one-period realized volatilities (i.e., a simple average of the daily quantities)"；月成分同理 1/22（正文："in our notation ... we will make use of weekly and monthly aggregation periods"，实施中 5 交易日/22 交易日）。
> 式(8)（HAR(3)-RV）：`RV^(d)_{t+1d} = c + β^(d) RV^(d)_t + β^(w) RV^(w)_t + β^(m) RV^(m)_t + ω_{t+1d}`；且"it could then be labeled as HAR(3)-RV. In general, denoting l and h, respectively, the lowest and highest frequency in the cascade, Equation (8) is an AR(l/h) model reparameterized in a parsimonious way by imposing economically meaningful restrictions (which take the form of a step function for the autoregressive weights)"。
> 估计与推断（逐字）："we can consider all the terms in Equation (8) as observed and then easily estimate its parameters β(·) by applying simple linear regression. Standard OLS regression estimators are consistent and normally distributed. In order to account for the possible presence of serial correlation in the data, the Newey–West covariance correction for serial correlation is employed."（表 2 用 Newey–West lag 5）
> **口径**（逐字）："irrespective of their actual frequency, all return and volatility quantities are intended to be annualized to facilitate comparison among different frequencies."
> **样本外协议**（逐字，表 5 注）："The AR(1), AR(3), and HAR(3) are daily reestimated on a moving window of 1000 observations."；评估指标（逐字，式(11)）："RV^(d)_t = b0 + b1 E_{t−1}[ R̂V^(d)_t ] + error, that is, a regression of the ex post realized volatility on a constant and the various model forecasts based on time t−1 information"，多步版式(12) 对 ∑_{j=0}^{h} RV^(d)_{t+j} 评估。
> **基准族**：AR(1)、AR(3)、ARFIMA(5,d,0) 与 HAR(3) 对照（表 4/5）；结论（逐字）"Out-of-sample, it turns out that the parsimonious HAR(3) model steadily outperforms the short-memory models at all the three time horizons considered (one day, one week, and two weeks)"，且失败原因是"the AR(1) and AR(3) models have a memory which is too short compared to the forecasting horizon and hence converge too quickly to their unconditional mean for longer forecasting horizons."

**(R20) 日内/会话边界必须由研究者**外生声明**（逐字先例，Corsi 2009 [一手]）。**
> "In order to avoid explicitly modeling the seasonal behavior of trading activity induced by the weekend, we exclude all the realized volatility taking place from Friday 21:00 GMT to Sunday 22:00 GMT."
> 数据口径（逐字）："we compute daily tick-by-tick realized volatility estimates employing the two scales estimator proposed by Zhang, Aït-Sahalia, and Mykland (2005) with the slower frequency of ten ticks returns."（ZAM 2005 = *JASA* 100:1394–1411，"A tale of two time scales: Determining integrated volatility with noisy high frequency data"，逐字取自 Corsi 参考文献表）
> 噪声侧证据（逐字）："This result may be due to the fact that the time series of the T-Bond realized volatility seems to show a higher level of noise ... due to a lower mean tick arrival frequency and a higher impact of market microstructure. The noisier estimation of the daily realized volatility induces a lack of significance of the daily volatility component, while weekly and monthly realized volatilities, being averages over longer periods, arguably contain less noise and more information on the volatility process"。
> 日内异质性的经典出处（书目核对自 Corsi 参考文献表，逐字）："Andersen, T. G., and T. Bollerslev. 1997. 'Heterogeneous information arrivals and return volatility dynamics: Uncovering the long run in high frequency data.' Journal of Finance 52: 975–1005."
> 更细尺度的同类思想（逐字脚注）："The HARCH process belongs to the wide ARCH family, but differs from all other ARCH-type processes in the unique property of considering squared returns aggregated over different intervals."（Müller et al. 1997 / Dacorogna et al. 1998）

**(R21) 1min 尺度上"局部趋势/流动性成分"是核估计的已知难点（逐字摘要，BHLŠ 2009 [一手]）。**
> "Realized kernels use high-frequency data to estimate daily volatility of individual stock prices. They can be applied to either trade or quote data. ... We identify some features of the high-frequency data, which are challenging for realized kernels. They are when there are local trends in the data, over periods of around 10 minutes, where the prices and quotes are driven up or down. These can be associated with high volumes. One explanation for this is that they are due to non-trivial liquidity effects."
> **项目含义**：TP13 的波动率标签在 1min 上必须声明"用 mid 还是 trade、是否去跳、是否核估计"，否则基准与模型比的不是同一个对象；10 分钟量级的局部趋势正好落在"1min 特征窗 ↔ 1min 标签窗"之间，是标签噪声的主要来源之一。

**(R22) 朴素/持久性基准是报告尺度的分母（逐字，FPP3 [一手]）。**
> "For a non-seasonal time series, a useful way to define a scaled error uses naïve forecasts... A scaled error is less than one if it arises from a better forecast than the average one-step naïve forecast computed on the training data. Conversely, it is greater than one if the forecast is worse than the average one-step naïve forecast computed on the training data."
> **项目含义**：TP13 每个指标都应以 1-bar naïve（上一步值）为分母报 MASE 类量纲；这比"绝对 RMSE"更能跨资产比较。

**(R23) 简单基准清单（1min 标签，逐条给出处）。**
| 基准 | 精确形式 | 出处 |
|---|---|---|
| persistence / 1-bar naïve | R̂V_{t+1}=RV_t（对 log 目标即随机游走） | Corsi 表 4/5 的 AR(1) 即其参数化版 [一手 ★17]；MASE 分母 FPP3 [一手 ★15] |
| 无条件均值 | R̂V = 训练集内该 (asset, 日内位置) 的 RV 均值 | Corsi 关于短记忆模型"converge too quickly to their unconditional mean"的论述 [一手 ★17] |
| EWMA（RiskMetrics 型） | σ²_{t+1}=λσ²_t+(1−λ)r²_t | Portfolio Optimizer 将 EWMA（λ 最优）、SMA、GARCH(1,1)、随机游走列为 HAR 的标准对照组 [二手 ★18] |
| HARCH(滞后阶) | 对 \|r\| 按不同聚合区间平方项回归 | Corsi 脚注逐字（R20）[一手 ★17] |
| HAR-RV（3 成分） | R19 式(8) | Corsi [一手 ★17] |
| 高频 RV 估计的抗噪版 | 双尺度/ZAM、realized kernel | R20、R21 [一手] |

---

## 2. 项目管道审计

审计对象：`scripts/hf_data_pipeline.py`（409 行，HEAD 2026-09-16 19:10）。判定用 **PASS / 偏差 / 风险**。**「实测」= 本轮在本机 pandas 2.3.3 直接执行该模块函数得到的输出。**

### 阶段 A：窗口聚合与 cutoff 定义（`clean_orderbook` / `add_event_ofi` / `aggregate_trades` / `aggregate_orderbook` / `normalise_kline`）

| ID | 标准 | 实际行为 | 判定 |
|---|---|---|---|
| A1 | R11：右闭右标窗口的"窗口 (c−Δ, c]"语义 | `resample('1min', label='right', closed='right')`。**实测**：ts=09:00:00 的快照落入 `cutoff_time=09:00:00` 行（即窗口 (08:59,09:00]）；ts=09:00:30 与 09:01:00 同属 `cutoff_time=09:01:00` 行（snapshot_count=2）。边界归属正确、无未来事件。 | **PASS** |
| A2 | 「特征行只用窗口内事件」的文档承诺（docstring："a feature at cutoff c only uses snapshots with timestamps in the corresponding completed interval ending at c"） | `log_mid_return = np.log(mid).diff()` 在 **resample 之前**于全序列上计算 ⇒ 每窗口首行的收益率起点是**上一窗口末快照**。**实测**：`cutoff=09:02:00` 行 snapshot_count=1，其 `realized_mid_vol` 由 09:01:00→09:01:30 构成（起点落在上一窗口）。⇒ 有效信息集是 (c−Δ−δ, c]，δ≤Δ。同一函数的 `event_ofi` 用 `g['event_ofi'].iloc[1:]` **正确地**剔除了跨窗口那一项，说明作者意识到该问题但只在一处处理。 | **偏差 #1** |
| A3 | 缺失窗口不伪装：`min_snapshots=1` 且 `continue` 跳过空窗（无 reindex/ffill） | 确实跳过，不生成占位行。 | **PASS** |
| A4 | 时间戳必须显式声明来源时区（R11 event vs processing time） | `_utc_times` 拒绝 naive 时间戳（`assume_tz` 必须由调用方给出）并统一到 UTC；`clean_orderbook(..., assume_tz='Asia/Shanghai')` 在 `run_sample` 里硬编码。 | **PASS**（口径声明化）+ **风险 R-A4**：A 股/币安混用时若 `assume_tz` 传错，整条 cutoff 轴平移小时级，管道无任何一致性检查。 |
| A5 | `drop_duplicates(subset=['event_time'], keep='last')` | 对同一时间戳的多条快照**只保留文件中最后出现的一条**，且 `keep='last'` 依赖排序前的输入顺序（`sort_values('event_time')` 在稳定排序下保留原相对序）。 | **风险 R-A5**：非泄漏，但结果对导出文件行序敏感 ⇒ 重跑可复现性前提（"同一秒内第 2 次改单被丢弃"）。OFI 在同时间戳序列上被截断。 |
| A6 | K 线 bar 语义不得由模型猜测 | `normalise_kline` 要求 `timestamp_semantics ∈ {bar_start, bar_end}`，非法值 raise；`bar_start` 时 `cutoff_time = bar_time + 1min`。 | **PASS**（这是本模块最强的设计）+ **风险 R-A6（高）**：无任何"相邻 bar_time 中位数 == bar_frequency"的断言。若把 bar_start 误标为 bar_end，全部 cutoff 前移恰好 1 分钟 = 恰好等于默认 label horizon ⇒ 特征窗与标签窗**无缝相接变成完全重叠**，且管道完全检测不到。建议 §3d 预注册一条"bar 间隔一致性"检查。 |

### 阶段 B：`align_features_to_kline`（asof 对齐）

| ID | 标准 | 实际行为 | 判定 |
|---|---|---|---|
| B1 | R8/R9：backward as-of 且 ≤ | `merge_asof(direction='backward')` ⇒ `feature.cutoff_time <= kline.cutoff_time`；与 pandas 文档逐字语义一致；**缺失保留 NA、不插值不 ffill**（模块 docstring："Past-only as-of alignment; missing features remain missing"）。 | **PASS**（教科书正确；相对 ffill 携带陈旧状态的旧路径是实质性改进） |
| B2 | R12b：不做全样本统计量 | 对齐阶段无任何拟合。 | **PASS** |
| B3 | R10 的 `temporal_join_lookback`（上界 = 不许太旧） | `tolerance=None` 默认 ⇒ 无限回溯。**实测**：一条 `cutoff=09-01 00:00` 的特征被贴到 `cutoff=09-05 00:00` 的 K 线（**陈旧 4 天**），且 `hf_available=True`。 | **偏差 #2**（默认值即 MS Learn 所说的 `default value is infinity`，且可用性标记把陈旧行报成"可用"） |
| B4 | 可审计性：PiT 联结必须保留**被匹配到的特征时间**（才能算 lag、才能在线复现同一行） | 输出列**实测**为 `['asset_id','cutoff_time','close','x','y','hf_available']` —— 右侧的 `cutoff_time` 被 asof 键吞掉，**匹配到的特征时点无法事后恢复**；`hf_available = out[hf_cols].notna().any(axis=1)` 是"任一列非空"的布尔，不含时滞信息。 | **偏差 #3** |
| B5 | R10 的 `source_delay`（下界 = 不许太新） | 无任何"事件发生时刻 → 数据可用时刻"的延迟参数。右标 cutoff=c 隐含"窗口在 c 即刻完备"。 | **偏差 #4**：纯离线研究内部自洽，但**一旦声称可用于实盘/实时预测即失效**；修复只需一个 `source_delay` 偏移（建议默认 = 1 个聚合窗口）。 |
| B6 | panel（多资产）可用性 | 左侧 `sort_values(['asset_id','cutoff_time'])` 使 `cutoff_time` 不再全局单调，而 `merge_asof` 要求 on 键单调（pandas 文档逐字："Both DataFrames must be first sorted by the merge key in ascending order"）。**实测**：2 资产 × 3 bar 的正常 panel 直接 `ValueError: left keys must be sorted`；单资产正常。另：当右侧缺 `asset_id` 且左侧多资产时回退写死 `"asset"`（永不匹配）⇒ 若左侧恰好时间单调，则**静默产出全 NA 特征**。 | **偏差 #5**（TP13 的跨资产面板当前**跑不通**；且退化路径无告警） |
| B7 | 与旧管道的关系 | `scripts/run_pipeline.py:39` 仍配 `"fillna": "ffill"`，`scripts/align_data.py` 提供 `ffill / bfill / interpolate` 三选一（`bfill`=硬未来泄漏，`interpolate`=线性内插即制造不存在观测）。 | **偏差 #6**：新模块的正确性被同仓旧默认路径抵消；TP13 必须显式声明"只允许 `hf_data_pipeline` 产物"，并把 `bfill/interpolate` 从可选值中删除或改名标记为 legacy。 |

### 阶段 C：`make_future_labels`（标签）

| ID | 标准 | 实际行为 | 判定 |
|---|---|---|---|
| C1 | R14：特征区间与标签区间零 overlap | 标签 = `log(close_{i+h}/close_i)`，窗口 (c, c+h]；特征 ⊆ (−∞, c]。**零 overlap 成立**，与文献标准（DeepLOB/Zhang-Zohren 的 m_−含 t、m_+从 t+1 起）同构。 | **PASS**（判定：既非偏保守也非偏松——这就是标准 no-overlap；唯一样本级松弛是 close 同时充当特征基准与标签基准，属标准做法） |
| C2 | 波动率标签在 h=1 时必须非退化 | `rolling(h, min_periods=h).std(ddof=0)`：h=1 时单点标准差恒为 0。**实测**：n=200、h=1 ⇒ `target_realized_vol` 非空 199 行、`nunique = 1`、全 0.0；h=2/h=5 正常（198/195 个不同值）。 | **偏差 #7**（默认参数下 TP13 的波动率任务**目标恒为 0**，任何模型都能"完美"拟合 → 假阳性风险最高的一条） |
| C3 | 标签窗口应以**墙上时钟**定义（否则"horizon=1"含义漂移） | 用 `groupby('asset_id').shift(-horizon)`（索引位移），无时钟校验。**实测**：删除一根 bar 后，`cutoff=09:32` 行的 `target_log_return = 0.5108 = log(5/3)`，实际跨度 09:32→09:34 = **2 分钟**。夜间/停牌/清洗丢弃的 bar 同理把 horizon 撑大。 | **偏差 #8**（同一数据集里 h 不再恒定 ⇒ R4 的 purge 长度 h 无唯一定义；跨资产比较也被污染） |
| C4 | R19 口径："all return and volatility quantities are intended to be annualized to facilitate comparison among different frequencies" | 目标为裸的 1-bar log return 与 `std(ddof=0)`（无 √·年化、无按品种频率归一）。 | **偏差 #9**（类别=可比性/基准公平性，非泄漏：跨资产、跨频率比较时基准与模型不在同一量纲） |
| C5 | `ddof` 与 RV 估计器口径 | `ddof=0`（除以 h）；波动率标签基于 **close-to-close 1-bar log return 的滚动标准差**，既非 §1.6 的 RV（√Σr²，含期内高/低频选择）也非核估计。 | **风险 R-C5**：与 R21 呼应——必须预注册"标签=何种 RV"，否则与 HAR/naïve 基准不同对象。 |
| C6 | 多资产不得串标签 | 逐资产 `groupby` 后 shift，无跨资产污染；末尾 h 行天然 NaN。 | **PASS**（但 NaN 尾部必须在 CV 前显式丢弃：见 R-C6）+ **风险 R-C6**：`pd.concat(future_returns).sort_index()` 依赖调用方 index 唯一，重复 index 会**静默错行**（无断言）。 |

### 阶段 D：数据集级评估协议（全仓）

| ID | 标准 | 实际行为 | 判定 |
|---|---|---|---|
| D1 | R1–R7：purge + embargo 必须存在于切分层 | 全仓 `grep` 无任何 `purge/embargo/TimeSeriesSplit/train_test_split` 实现；泄漏控制目前**100% 依赖单样本级的 asof 对齐**。 | **偏差 #10**（跨折泄漏完全未防护：h=1 时训练块最后 1 根 bar 的标签直接落在验证块第一根 bar 上；模型 context 更长时按 §3b 公式需砍更多） |
| D2 | R16：panel 需实体方向封口 | 无任何 entity/group 维度的切分逻辑（且 B6 使 panel 路径尚不可用）。 | **偏差 #11** |
| D3 | R12b：归一化必须在折内/仅用过去 | 本模块不产出归一化特征（正确）。**但下游 TSFM 通路的窗口归一化是已知事故点**（Kronos issue #227：per-window 归一化把未来纳入；已由 deep_D 核实）；高频侧文献给出现成写法（DeepLOB"用前 5 天统计量"，R12b）。 | **风险 R-D3**（TP13 应把"归一化统计量的时点来源"列为强制申报项） |

**小结**：**偏差 11 条**（#1–#11），PASS 8 条，风险 8 条（R-A4/A5/A6、R-C5、R-C6、R-D3 等）。
其中**会导致错误实验结论**的三条：#7（h=1 波动率标签恒 0）、#8（horizon 随缺 bar 漂移 ⇒ purge 长度无定义）、#10（跨折无 purge/embargo）。#5 阻断 panel 实验，#2/#3 使"陈旧特征"不可见、不可诊断。

---

## 3. TP13 规范草案

> 记号：Δ = 1 min（bar）；h = 标签 horizon（bar 数）；L_feat = 单样本所有输入的**最长** lookback（bar 数）；N = 单资产样本数；A = 资产数。

### 3.a 每个预测时点的 point-in-time 信息集白名单

1. **时点集合先验固定、不得事后挑选**。预测时点集 `T_anchor` = 连续竞价时段内全部 1min bar 右端 `c`，并额外标注三类锚点子集：`open_anchor`（开盘后第 k 根）、`mid_anchor`（日内位置分位数）、`close_anchor`（收盘前第 k 根）。理由：R15 的"information set discipline"要求 cutoff 是被声明的，而非被搜索的；日内波动/活跃度有系统性周期成分（R20 的 Andersen–Bollerslev 1997 与 Corsi 的"周末剔除"先例 ⇒ 边界与锚点属**外生声明**）。
2. **每个 cutoff 的信息集**（写成可断言的规则）：
   `I(c) = { x : available_at(x) ≤ c }`，其中
   - `available_at(HF特征行) = 窗口右端 + source_delay`，`source_delay := 1 个聚合窗口`（默认，需实测覆盖：快照落库延迟 P99）；
   - `available_at(K线行) = cutoff_time`（且 `cutoff_time` 的 bar_start/bar_end 语义必须由 `normalise_kline(timestamp_semantics=...)` 显式声明并**记录进数据集 metadata**）；
   - `available_at(标签) = c + (h+1)·Δ` ⇒ **标签永不在 I(c) 内**（C1 已满足）。
3. **陈旧度上限**（修偏差 #2/#3）：`max_lag := 2·Δ`（超过即该行 HF 特征置 NA），输出必须同时保留 `hf_feature_time` 与 `hf_lag_seconds` 两列，`hf_available := (hf_lag_seconds ≤ max_lag)`。
4. **白名单逐行申报（强制字段）**：`asset_id, cutoff_time, source_name, event_time_upper_bound, source_delay, max_lag, na_policy(=keep_NA, 禁止 ffill/bfill/interpolate), gap_flag, session_state`。
5. **会话/缺口排除规则**：
   - A 股：剔除开盘集合竞价 (09:15–09:25) 与收盘集合竞价 (14:57–15:00) 覆盖的窗口；**开盘后第 1 根 bar 不进锚点集**（其跨窗收益率含隔夜跳空，见 A2/C3 机制）；
   - 跨缺口窗口（`gap_flag=True`，即上一事件与本事件间隔 > 2Δ）**不得**贡献 `realized_mid_vol / mid_return / log_mid_return` 类特征；
   - 币安 7×24：无自然日边界，"日"必须由 `session_boundary_tz := UTC` 显式声明（引 Corsi 逐字先例）；
   - 缺 bar 必须**显式补 NA 行**（不补行、只做时间轴 reindex），使 §3.b 的 purge 长度有唯一含义（修偏差 #8）。
6. **一致性断言（CI 级）**：①`median(diff(bar_time)) == bar_frequency`；②每条 HF 特征行 `ts ≤ cutoff_time` 且 `ts > cutoff_time − Δ`（A1/A2 分离）；③全表 `cutoff_time` 全局单调（防 B6 类退化）；④标签窗口 `(c, c+h·Δ]` 的时钟跨度必须恰为 `h·Δ`（防 #8）。

### 3.b CV 方案：切分粒度 + purge 长度公式

1. **切分粒度**：块 = 时间连续块（禁 shuffle，R12/R15）+ 实体方向封口（R16）。
   - 主方案 **Walk-forward（rolling origin，锚定增长）**：`train_k = [t_0, T0_k − purge)`，`test_k = [T0_k, T1_k]`，步长 Δ_step = 测试块长；参照 Deep et al. 的 Definition 5（W=252/H=63/Δ=63 的比例 4:1）给出高频版：**W = 20 交易日（=28 800 根 1min bar）、H = 5 交易日、Δ_step = H**（A 股 1min 连续竞价 240 bar/日 ⇒ W=4800、H=1200；两值均须在预注册中写死）。
   - 副方案 **Purged K-Fold（K=5，等长块）+ CPCV 仅在需要多条 OOS 路径时启用**；理由（R5–R7 + Arian et al. 经 Deep et al. 转述："finding that Combinatorial Purged Cross-Validation shows superiority in mitigating over-fitting risks" [二手]）。**注意**：随机块 K 折在 1min 数据上会破坏日内季节性可比性 ⇒ 若用 K 折，块必须以"整日"为单位抽样。
   - **实体维度**：跨资产面板实验需三套并列结果——(i) same-asset future（时间封口，主结论）、(ii) leave-N-assets-out（实体封口，检验泛化）、(iii) joint（时间+实体双封口）。每套分开报告，禁混用（R16 的 "The train-test split should account for the dependencies in the data"）。
2. **purge 长度公式（horizon = h 时 e = ?）**
   - **purge_before = h**：从**训练块右端**剔除最后 h 根 bar（等价于 (R2)/(R4)：训练样本标签区间与测试区间断开）。逐字依据：(R6) "Leakage from before the test set travels through forward-looking label windows, and purging has already removed it."
   - **embargo 下界公式（本项目的可审计版本，标注为**推导**）**：
     `e = max(h, L_feat)` （bar）
     其中 `L_feat = max(模型输入 context 长度, 最长滚动特征 lookback, HF 窗口跨界余量)`。
     依据：(R6) "Leakage after the test set travels through backward-looking features, which purging cannot see." ⇒ 测试块后第 t 根训练样本若其输入覆盖 `[t − L_feat, t] ∋ ≤ T1` 即泄漏，故需 `t > T1 + L_feat`。
     **本项目的数值**：仅用 `hf_data_pipeline` 特征时 `L_feat = 1 + 1 = 2`（右标窗口 + A2 实测的跨界收益率）⇒ h=1 时 **e = 2**；一旦接入 TSFM context（Kronos 默认回看以 bar 计，例如 400–512）**e = context 长度**（≈ 7–9 小时 1min 数据）⇒ **这是 TP13 预算的第一约束**： embargo 长度必须写进每折的"损耗后样本数"里。
     文献侧的闭式（"e ≥ h 的精确陈述"、书籍 §7.4.2 原文）**未能核实**（§4-U1），故以"区间重叠判据 (R2) + 非对称性 (R6)"为唯一依据；同时把实现默认 `pct_embargo = 0.01`（financial-ml-core 逐字）作为**下限体检**：若 `e/N < 0.01`，须在报告中解释为何短于"总观测 1%"的经验起点（(R7)）。
   - **面板额外**：`(ii)` 留一资产方案不需时间 purge（实体不相交），但**必须 embargo 归一化统计量**（DeepLOB 式"前 5 天"若跨折复用即回潮，R12b）。
3. **折内所有拟合仅在 train 折内完成**：scaler、α 阈值（R14）、HAR/EWMA 参数、特征选择。任何"全样本算出来的列"必须在 §3.d 申报表中出现并给出处方。
4. **有效样本量（预算用，标注为**算术推导，无外部一手引文**）**：块长 n_bar、标签长 h 时，折内独立块数 ≈ `⌊n_bar / (h + 1)⌋`；跨折合并 OOS 时不得把重叠标签的行当作独立观测计数（R3 的 IID 失效在此的定量后果）。所有功效计算（TP4）以该值而非 `n_bar` 为准。

### 3.c 基准（精确公式）

1. **HAR-RV（Corsi 2009 式(8)，逐字转写）**
   `RV^{(d)}_{t+1} = c + β^{(d)} RV^{(d)}_{t} + β^{(w)} RV^{(w)}_{t} + β^{(m)} RV^{(m)}_{t} + ω_{t+1}`
   `RV^{(d)}_t = ( Σ_{j=0}^{M−1} r^2_{t−jΔ} )^{1/2}`（式(3)），`RV^{(w)}_t = (1/5)(RV^{(d)}_t + ⋯ + RV^{(d)}_{t−4})`（式(4)），月 = 1/22。
   协议照抄：OLS + Newey–West(lag 5)；**滚动窗再估**（原文 1000 观测 ⇒ 高频版取 `W_HAR = 28 800` 根 1min bar，或日频成分用 1000 日）；评估用 Mincer–Zarnowitz 式(11)（多步用式(12) 的聚合目标）；**所有量年化**（R19 逐字）。
2. **分钟尺度的同构扩展（标注为项目扩展，非文献逐字）**：把"日/周/月"替换为多尺度成分，例如
   `RV^{(m1)}_{t+1} = c + β_1 RV^{(1)}_t + β_5 RV^{(5)}_t + β_{15} RV^{(15)}_t + β_{60} RV^{(60)}_t + β_{240} RV^{(240)}_t`，其中 `RV^{(k)}_t = (1/k)Σ_{i=0}^{k−1} RV^{(1)}_{t−i}` 完全沿用 Corsi 式(4) 的"normalized sums of the one-period realized volatilities"定义。依据：R19 的"HAR(3)-RV 是 AR(l/h) 的阶梯权重再参数化"与 R20 的 HARCH"按不同聚合区间取平方收益"。这条**必须在预注册中声明是外推**，且要同时报告原始 3 成分版以便对齐文献。
3. **必备简单基准（全部在同一 purge/embargo 折内拟合）**
   | 名称 | 公式 | 出处 |
   |---|---|---|
   | `naive_persist` | σ̂²_{t+1} = RV²_t（= 随机游走预测） | Corsi 表 4/5 的 AR(1) 退化形 [★17]；MASE 分母 FPP3 [★15] |
   | `hist_mean` | σ̂²_{t+1} = 折内训练集无条件均值（可选按"日内位置"分层） | Corsi 关于短记忆模型收敛到 unconditional mean 的论述 [★17] |
   | `ewma` | σ²_{t+1} = λσ²_t + (1−λ)r²_t，λ ∈ {0.94, 0.97}（RiskMetrics 日常/月内惯例）与折内最优 λ | Portfolio Optimizer 对照清单 [★18 二手]（λ 常数惯例**未一手核实**，见 §4-U4） |
   | `harch` | \|r_t\| 对各聚合区间前向平方收益回归 | Corsi 脚注逐字 [★17] |
   | `garch11` | 作为波动率侧经典对照（可选） | [★18 二手] |
4. **收益方向/幅度侧基准**：`sign(close_{t+1} − close_t) ≡ +1` 与 `pred = 0`（即"下一 bar 无信息"）双基准；报告**相对 naive 的 MASE/对数损失**（R22）与 R14 的 α 阈值配平后 F1/AUC；HF 侧可比锚点：Tsantekidis 报告 CNN-LSTM 的 F1 从 k=10 的 0.44 升到 k=200 的 0.49 [★13 一手] ⇒ 1min 单 bar 任务落在"精度仅略高于随机"的区间，**任何显著性宣称都要以该带为参照**。
5. **标签对象必须先定义再比**（R21）：声明 `RV` 用 mid、trade 还是 realized kernel；TP13 主指标建议 `mid-based RV + 5 分钟以上聚合的去噪版`双轨，避免 1min 局部趋势/流动性成分（BHLŠ 逐字："local trends in the data, over periods of around 10 minutes"）主导排名。

### 3.d 预注册项清单（跑任何模型之前填完并冻结）

模板 = Kapoor & Narayanan 的"三论证"信息表（R17，逐字 [L1]/[L2]/[L3]）+ Deep et al. 的"not optimized on the test dataset / pre-specified criteria" [★16]。

1. **任务对象**：预测变量、损失函数、评估窗（时钟跨度，不是索引跨度）、目标年化/量纲口径（C4）。
2. **h 与 Δ 表**：h ∈ {1, 5, 15, 60}（bar）；`target_realized_vol` 在 h=1 时的定义修正方案（改 `|r_{t+1}|` 或强制 h≥2）——**对应偏差 #7 的关闭条件**。
3. **`T_anchor` 白名单**（§3.a-1、§3.a-5）与被排除的窗口类型及理由。
4. **信息集与特征清单**：每特征 `available_at`、`source_delay`、`max_lag`、NA 策略（只允许 keep_NA）；禁止 ffill/bfill/interpolate 的书面声明（对应 B7）。
5. **切分方案**：粒度、块长、折数、是否锚定；三套实体方案 (i)(ii)(iii) 各自的主/副指标（对应偏差 #10/#11）。
6. **purge/embargo 数值**：`purge_before = h`、`e = max(h, L_feat)`，并逐项列出 `L_feat` 的来源（模型 context 长度、每个滚动特征窗、A2 的跨界余量）；若 `e/N < 1%` 给理由（(R7)）。
7. **折内拟合边界**：scaler/α/λ/HAR 参数/特征选择/早停所用的验证子块，全部注明"仅用该折 train"。
8. **有效样本量与预算**：`n_eff ≈ ⌊n_bar/(h+1)⌋`（标注为推导）、每折损耗后行数、总计算量、以及"允许被查看测试块的次数"（多重比较预算，与 TP4 对接）。
9. **基准清单与冻结值**：§3.c 全部基准 + 其拟合窗；先声明"若模型未在 `naive_persist` 与 `hist_mean` 双基准上胜出则不解读为发现"。
10. **指标与显著性**：MASE、MZ 回归的 (b0,b1) 及检验、Newey–West 阶数（Corsi 用 lag 5，逐字采用并注明）、QLF/DM 类检验与自助法（本条留给 TP4）。
11. **数据质量断言**（§3.a-6 四条 CI 检查）+ `CleaningReport` 的落盘（丢弃计数不得反向成为筛选阈值，防 L1.2 回潮）。
12. **可复现性**：`pandas==2.3.3`、代码 commit、`hf_data_pipeline.py` 哈希、随机种子、`assume_tz` 与 `timestamp_semantics` 的实际取值（A4/A6 风险申报）。
13. **偏差登记与关闭条件**：本文件 §2 的 11 条偏差，逐条给"修复 PR + 通过的断言"。未关闭前，受影响实验标记 `delta=0`。
14. **失败声明**：预先写出"若结果落在 R22/3.c-4 的无信息带内，则结论为不存在可预测性"，避免事后合理化。

---

## 4. 未能核实的点

- **U1（最重要）· López de Prado 原著逐字与 embargo 闭式**。可达源均为**转述**：`hudsonthames.org` 的 purge/embargo 专页 404；Wiley/ciando 样章 PDF 连接超时；SSRN 全文 403；SlideShare 讲义超时。因此：(a) 书籍 Ch.7 §7.4 的原句；(b) "**e ≥ 标签 horizon**" 这类精确闭式；(c) "1% 起点"是否真出自原书而非讲义/社区——**全部只到 [二手] 级**。本轮以可验证的区间重叠判据 (R2) 与非对称性 (R6) 为依据推出 §3.b 的 `e = max(h, L_feat)`，并在规范中明确标注为**推导**而非引文。若后续能拿到原书 §7.4/§12，应回填替换。
- **U2 · 金融 panel CV 论文**（Kozlovskiy, *Robust Cross-Validation Procedure for Panel Datasets*, JPM）在 OpenAlex / Semantic Scholar（429）/ pm-research 检索/SSRN/arXiv 全站检索中**未取得任何书目级证据**；不得作为依据引用。§1.5 的实体封口改用可核实的 Kapoor & Narayanan L3.2/L1.4 + block CV 引注（Roberts et al. 2017; Valavi et al. 2021，均转引自该一手论文，**其原文本身未读**）。
- **U3 · Alexander–Dufour–Engle (2002, *Economic Journal*) 与"slowest first-passage time"作为 horizon 选择规则**：本轮两次检索均未取得该书目记录，且搜索代理明确警告该组合可能是**拼接/不存在的引用**；同时 JF 55(6):2467–2498 的 Dufour & Engle (2000) "Time and the Price Impact of a Trade" 虽经 RePEc 核实存在，但其摘要**不含** horizon 选择规则。⇒ **"标签 horizon 应取最慢首达时间/均值回复半衰期"这一实践本轮无法给出可核实出处**，§1.4 改用高频 LOB 文献的实测网格（R13/R14）作为 horizon 量纲依据。
- **U4 · RiskMetrics λ=0.94/0.97**、GARCH(1,1) 对照、Hansen & Lunde (2005) 的"naïve 基准"原句：未取得一手，仅出现在 [二手] 讲义式页面（Portfolio Optimizer）；§3.c 表中标注为二手。
- **U5 · Corsi–Zumbach–Müller–D'Accordi「HARning OBV」**（1 分钟尺度 OBV 的 HAR 与 UVIX 去季节性、以及分钟尺度的持久性基准）与 **Zumbach et al. (2008) "The price of time"**：OpenAlex/Scholar/SSRN/arXiv 检索全部空命中，**未取得任何可引用文本**。⇒ §3.a 的"日内位置分层 / 去季节性"仅依据可核实的 R19（年年化与聚合定义）+ R20（Andersen–Bollerslev 1997 书目、Corsi 周末剔除先例），**不引入 UVIX 术语**。
- **U6 · BHLŠ (2009) "推荐 5 分钟采样"**：只取得 Econometrics Journal 12(3):C1–C32 的**摘要**（含"around 10 minutes"的局部趋势表述，逐字已引），全文中关于采样频率/带宽的建议**未核实**，故 §3.c-5 只要求"声明 RV 口径"，不给具体频率数字。
- **U7 · 跨模态（HF 1min → LF 1min bar）CV 的专门规范**：文献侧无一手命中；§3.b 的做法是把 (R5/R6) 的 backward-feature 论证**代入本管道的实测 lookback（L_feat=2）**并显式外推到模型 context，属推导 + 工程判断，标 `[推导]`。
- **U8 · 一次性方法论教训**：两次凭记忆给 arXiv id 抓取到完全不相干的论文（1909.10125 = 细胞自动机、2503.07704 = 白矮星、2003.01184 = 循环网络物理仿真），已作废其全部"结论"。今后所有 arXiv id 必须先经检索命中再引用；本文件中的每个 arXiv id（1808.03668 / 1810.09965 / 2105.10430 / 2207.07048 / 2512.12924）均来自**检索结果页且已实际打开正文**。
