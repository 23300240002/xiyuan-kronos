# Deep Research D · TSFM/Kronos 下游使用标准与空白性验证（2026-09-17）

## 0. 方法（抓了哪些源）

**Web（web_fetch 可用；GitHub / arXiv 可达，HuggingFace 不可达，见 §6）：**
- `github.com/shiyu-coder/Kronos` README（2026-09-17 抓取，200 OK）
- GitHub Search API：`repo:shiyu-coder/Kronos` 下对 `hidden` / `finetune` / `custom head` / `hidden state` / `internal representation` / `probing` / `representation|embedding|latent` / `LoRA|adapter` 共 8 组关键词的 issues+PR 检索；单条 issue 全量 JSON：#227、#297、#307（含评论）、#355；PR #263、#391、#400 经搜索列表获得标题/日期/状态
- GitHub Repo Search API：`Kronos fine-tune time series` / `Kronos trading OHLCV` / `lag-llama`（第三方仓库盘点）
- 官方仓库 README：`google-research/timesfm`、`amazon-science/chronos-forecasting`、`SalesforceAIResearch/uni2ts`（Moirai）、`time-series-foundation-models/lag-llama`（1.6k★）
- 第三方仓库 README：`intelligolabs/ChronosAD`
- arXiv API / abs 页：2511.15324、2604.16428、2509.05801（time2time）、2510.26777、2606.01300（ChronosAD）、2102.12452（Belinkov）、1905.06316（Tenney）；以及 5 组空白性检索（见 §4）
- OpenReview（#ryghZp097o 被浏览器验证墙拦截，未用其结论）

**本地代码核对（一手）：**
- `KronosLocal/deps/Kronos`（grafted clone，HEAD 67b630e，2026-04-13，与已知"最后推送"一致）：`model/kronos.py`（KronosTokenizer.encode/decode、Kronos.forward/decode_s1/decode_s2、auto_regressive_inference、KronosPredictor.predict/predict_batch）、`finetune/dataset.py:110-117`（#227 修复后的 lookback-only 归一化）、`finetune_csv/finetune_base_model.py:125`（#263 之前的 full-window 归一化）、`finetune/train_predictor.py`（全参 DDP 训练，无 LoRA/adapter）、`kronos_small/weights/config.json`（d_model=512, n_layers=8, s1/s2_bits=10, token_dropout_p=0.1）
- `课题/research/scripts/kronos_context_adapter.py`（项目 adapter，只读核对）
- 全库 grep `.eval()`：确认 `KronosPredictor` 从不调用 `model.eval()`

## 1. Kronos 下游接口现状（API/issues/第三方 fine-tune，逐条带链接）

### 1.1 官方 README 暴露的 API

| 项 | 内容 | 证据 |
|---|---|---|
| 零样本接口 | `KronosPredictor.predict(df, x_timestamp, y_timestamp, pred_len, T=1.0, top_k=0, top_p=0.9, sample_count=1, verbose)` 与 `predict_batch(...)`；输入 OHLC（必需）+ volume/amount（可选，缺失时 impute），输出未来 OHLCVA DataFrame | [一手] 本地 `model/kronos.py` predict 源码 + README（github.com/shiyu-coder/Kronos）："You can control the sampling process with parameters like `T`, `top_p`, and `sample_count` for probabilistic forecasting." |
| fine-tune | README 专节 + `finetune/`（Qlib 数据、DDP 全参训练 tokenizer→predictor 两阶段）与 `finetune_csv/` 两条流水线 | [一手] README："The finetuning process consists of two stages: finetuning the tokenizer and then the predictor." 本地 `finetune/train_predictor.py` 用 `AdamW(model.parameters())` 全参更新，无 LoRA/adapter 实现 |
| hidden states | README **无任何** hidden states / custom head / 表征提取说明。但代码层 `Kronos.decode_s1` 的 docstring 明确返回 context：[一手] 本地 `model/kronos.py`："context: Context representation from the Transformer. Shape: [batch_size, seq_len, d_model]" | docstring 存在但非公共文档面 |

**项目含义**：项目 adapter 调用的 `decode_s1` 是代码中已文档化（docstring 级）的返回物，不是逆向工程；但上游没有承诺其语义，README 面不承认该用法——与 C-X10-001 的"接口已定位但无对齐接口"判定一致。

### 1.2 issues/PR：有没有人要 hidden states / custom head

| # | 日期 | 标题（逐字） | 相关性 |
|---|---|---|---|
| [#297](https://github.com/shiyu-coder/Kronos/issues/297) | 2026-05-21 | "Question: How to handle discontinuous markets for regime detection using Kronos embeddings?" | **最相关**：第三方已在用 Kronos tokenizer embeddings 做 regime detection（聚类），问 A 股不连续市场下表征失稳怎么处理。0 评论，无维护者回复 |
| [#355](https://github.com/shiyu-coder/Kronos/issues/355) | 2026-07-26 | "I tested Kronos-mini on split-adjusted, regular-session 30-minute US OHLCV from eight liquid symbols" | 用户微调后 token loss 降但交易无优势，直接索要 custom head："do you recommend a task-aligned fine-tuning objective for direction/return/ranking, rather than token prediction loss alone? A calibrated confidence or direct alpha head would be especially useful for intraday users." |
| [#307](https://github.com/shiyu-coder/Kronos/issues/307) | 2026-05-29 | "Were the pretrained HF checkpoints retrained after the per-window normalization leakage fix (#227)?" | 关键悬置问题（见 §5/§6）。正文："the leakage would effectively be baked into the checkpoints even though the current dataset code is correct." 2 条评论均非维护者；社区猜测（[二手]）："they did NOT release the retrained models, nor they release the kronos-large model." |
| [#227](https://github.com/shiyu-coder/Kronos/issues/227) | 2026-03-17（closed） | "the dataset leaks future information" | 注意：**是 issue 不是 PR**。原文："the dataset leaks future information into every sample via per-window normalization. In finetune_base_model.py (line 127) and (line 132), x_mean/x_std are computed from the full window, which already includes the nominal forecast horizon." 泄漏在 **finetune 数据集路径**，推理路径本就 lookback-only |
| [PR #263](https://github.com/shiyu-coder/Kronos/pull/263) | 2026-04-15（open） | "fix(finetune): prevent data leakage in CustomKlineDataset normalization" | 同类泄漏在 `finetune_csv` 路径的修复（"restricting it to lookback only"）。**本地 HEAD(2026-04-13) 早于它，本地 finetune_csv 未含此修复**（已核对 `finetune_csv/finetune_base_model.py:125` 仍是 full-window） |
| [PR #391](https://github.com/shiyu-coder/Kronos/pull/391) | 2026-08-15（open） | "Make walk-forward eval honest vs random walk (#387)" | 描述提到 "fixes dropout inference issues"——印证 §5 的 eval-mode 差异 |
| [PR #400](https://github.com/shiyu-coder/Kronos/pull/400) | 2026-09-08（open） | "Add Kronos-Macro data and forecasting foundations" | 第三方在加 "a safe Kronos adapter"（代码 adapter，非特征 adapter）；说明"adapter"一词在 Kronos 社区指代码封装 |
| [#347](https://github.com/shiyu-coder/Kronos/issues/347) | 2026-07-15 | "Request for Academic Access to Kronos-Large (499.2M)" | Kronos-Large 为 gated，学术访问需申请——项目用 small 不受影响，但对比实验拿不到官方 large |
| [#375](https://github.com/shiyu-coder/Kronos/issues/375) | 2026-07-29 | "Cross-sectional ranking test: Kronos-small on 182 US equities, 85 post-cutoff dates — IC +0.022 (t=1.39), fails after costs" | 第三方对 Kronos-small 零样本横排能力的负面结果，支持"形状通过 ≠ 有预测信息"（C-X10-001 §5 已声明） |

**8 组关键词检索均未发现"请求官方暴露 hidden states API"的 issue**；唯一实际取用内部表征的是 #297（tokenizer 层、非官方、无回复）。

**项目含义**：(a) "从 Kronos 取内部表征当特征"不是造轮子——#297 证明社区已有先例，但属非官方用法；(b) #355 证明"下游想要 alpha 头/校准置信度"是社区共性需求且无官方方案，项目的低频 context + 高频特征双路头正是对这一空白的工程回应，但**不能声称是首创接口**；(c) 上游 PR 积压未合并（#263/#391/#400 均 open），项目应继续钉死本地版本 67b630e。

### 1.3 第三方 fine-tune 教程/仓库（GitHub repo search，均为 0★ 小仓库）

| 仓库 | 创建 | 描述（逐字） |
|---|---|---|
| [x1sauce/stockpicker-kronos](https://github.com/x1sauce/stockpicker-kronos) | 2026-05-21 | "ETF prediction project using Kronos for time-series forecasting, fine-tuning, ranking signals, and backtesting across different ETFs." |
| [thotbreakerr/kronos-gauntlet](https://github.com/thotbreakerr/kronos-gauntlet) | 2026-08-03 | "Paper-trading bot and quantitative research platform built on the Kronos OHLCV foundation model: 11 pre-registered probes for a retail trading edge..."（probes=预注册假设，非线性探针） |
| [armaanfarshori/dhan_algo](https://github.com/armaanfarshori/dhan_algo) | 2026-05-06 | "...rule-based Opening Range Breakout strategy filtered through Kronos, an OHLCV foundation model (AAAI 2026)..." |
| [ToXMon/signal30](https://github.com/ToXMon/signal30) | 2026-04-18 | "Social-signal-powered trading intelligence... feeds as covariates into TimesFM 2.5 for price forecasting with Kronos OHLCV validation."（佐证 TimesFM 2.5 协变量接口在第三方实践中被使用） |

**项目含义**：第三方生态全部是"零样本/全参微调 + 规则/回测"路线，**没有任何公开仓库做"取 Kronos hidden context 喂下游高频模型"**——项目 adapter 这条路在公开层面仍无先例实现（与 §4 空白性结论互证）。

## 2. TSFM 家族下游实践对照表

| 维度 | TimesFM（Google） | Chronos / Chronos-Bolt / Chronos-2（Amazon） | Moirai（Salesforce, uni2ts） | Lag-Llama（Salesforce） |
|---|---|---|---|---|
| 零样本接口 | `predict`/`predict_batch`（`TimesFM3Forecaster`/`TimesFM3Evaluator`），点预测+9 分位数 | `Chronos2Pipeline.from_pretrained("amazon/chronos-2").predict_df(context_df, future_df=...)`，分位数输出 | GluonTS predictor 对象 `predictor.predict(test_data.input)` | 零样本、任意频率任意预测长度；输出每步概率分布 |
| 官方证据 | [一手] github.com/google-research/timesfm README："It mirrors the PyTorch `TimesFM3Forecaster` interface (`predict` / `predict_batch`, univariate or multivariate, with past-only and past-future covariates)" | [一手] github.com/amazon-science/chronos-forecasting README："It offers *zero-shot* support for univariate, multivariate, and covariate-informed forecasting tasks." | [一手] github.com/SalesforceAIResearch/uni2ts README："Let's see a simple example on how to use Uni2TS to make zero-shot forecasts from a pre-trained model." | [一手] github.com/time-series-foundation-models/lag-llama README（1601★）："Zero-shot forecasting on a dataset of any frequency for any prediction length" |
| fine-tune 程度 | **LoRA**（HF Transformers + PEFT 官方示例）："Added fine-tuning example using HuggingFace Transformers + PEFT (LoRA)" | README **未提** fine-tune（论文定位零样本）；生态内无官方 adapter/LoRA | CLI/Hydra 脚本："We provide several scripts which act as a command line interface to easily run fine-tuning, evaluation, and even pre-training jobs"（README 未声明 LoRA/adapter/全参范围，未深入代码核实） | fine-tune 脚本（"16-Apr-2024: Released pretraining and finetuning scripts to replicate the experiments in the paper"），README 未声明 adapter/LoRA，未深入 `scripts/finetune.sh` 核实 |
| 协变量接口 | **有**：TimesFM 3.0 原生 past-only + past-future covariates；2.5 经 XReg："Added back the covariate support through XReg for TimesFM 2.5." | **有**（Chronos-2）：`predict_df` 的 `future_df` 参数接收协变量未来值 | **有**：模型构造参数 `feat_dynamic_real_dim` / `past_feat_dynamic_real_dim` | README **未提**（论文用 lag-features 输入构造，非协变量接口） |
| **hidden states 暴露？** | **否**（README/文档面） | **否**（README 面）；但第三方 ChronosAD 从源码取 embedding 当特征（§3） | **否**（README 面） | **否**（README 面） |

**四家结论（一句话）**：TimesFM / Chronos / Moirai / Lag-Llama 的官方文档面（README + 官方接口）**均不暴露 hidden states 供下游当特征**，fine-tune 路线以"LoRA（TimesFM 3.0）/全参脚本"为主；Kronos 反而是四家+Kronos 中**代码层唯一在 docstring 里声明返回 token-level context 的**（`decode_s1`），而实际取用 hidden 的下游工作（ChronosAD、Kronos #297）都走源码层钩子，不走官方 API。

**项目含义**：项目"从 Kronos 取 [B,512] context 当低频特征"的做法与整个 TSFM 生态的**公共 API 惯例一致地"越界"**——没有任何一家官方提供该接口，但 Kronos 的 `decode_s1` 是四家中最接近的正规出口；项目的 adapter 封装（只读、带配对元数据）正是生态缺失的那层"official-but-missing"胶水，定位合理。

## 3. "hidden states 当特征"的标准做法

### 3.1 NLP probing / linear evaluation 传统（代表 2 篇）

1. **Tenney et al., 2019, "What do you learn from context? Probing for sentence structure in contextualized word representations"**（arXiv:1905.06316）
   > "Building on recent token-level probing work, we introduce a novel edge probing task design and construct a broad suite of sub-sentence tasks derived from the traditional structured NLP pipeline."
   [一手·摘要] 项目含义：probing 的标准形态是"冻结表征 + 训练线性/小型分类头 + 成体系的探针任务"，项目用 context 喂下游预测头正是该形态的时序版。
2. **Belinkov, 2021, "Probing Classifiers: Promises, Shortcomings, and Advances"**（arXiv:2102.12452）
   > "Probing classifiers have emerged as one of the prominent methodologies for interpreting and analyzing deep neural network models of natural language processing. The basic idea is simple -- a classifier is trained to predict some linguistic property from a model's representations"
   [一手·摘要] 项目含义：该综述同时列出 probing 的短处（探针设计选择会改变结论）——项目做"hidden 是否比模型输出更有信息"时，探针/下游头的设计本身必须写进预注册，不能只报一个数字。

### 3.2 时序域 analogue（已发表的 hidden-states-当-特征工作，3 篇 + 1 篇因果版）

1. **Auer, Klotz, Böck, Hochreiter, 2025, "Pre-trained Forecasting Models: Strong Zero-Shot Feature Extractors for Time Series Classification"**（arXiv:2510.26777）
   > "we examine whether frozen pre-trained forecasting models can provide effective representations for classification... the best forecasting models achieve classification accuracy that matches or even surpasses that of state-of-the-art models pre-trained specifically for classification. Moreover, we observe a positive correlation between forecasting and classification performance."
   [一手·摘要] 方法：冻结模型 + 对比多种表征提取策略 + 两个 model-agnostic embedding 增强。**结论方向：hidden 表征对下游任务有独立价值（可达分类 SOTA），且预测能力与表征质量正相关。** 项目含义：这是"TSFM hidden 当特征"最直接的已发表支撑，项目的 delta>0 假设与此一致；注意其对照是分类 SOTA 而非模型自身输出。
2. **Khan et al., 2026, "ChronosAD: Leveraging Time Series Foundation Models for Accurate Anomaly Detection"**（arXiv:2606.01300；代码 github.com/intelligolabs/ChronosAD）
   > "it uses the foundation model to extract embeddings for each time series in a zero-shot manner. Then, a custom-developed Temporal Block, composed of Bidirectional Long Short-Term Memory (BiLSTM) and Multi-Head Attention, refines these embeddings to capture temporal dependencies"
   [一手·摘要+README] 项目含义：标准两段式 = **零样本 frozen embedding + 任务专用轻量模块**，与项目"Kronos context → 高频编码器 → 预测头"同构；但 ChronosAD 做异常检测、未涉及多频/订单流。
3. **Choi, Shook, Dubrawski, 2026, "Non-Stationarity in the Embedding Space of Time Series Foundation Models"**（arXiv:2604.16428）
   > "Time series foundation models (TSFMs) are widely used as generic feature extractors, yet the notion of non-stationarity in their embedding spaces remains poorly understood... we find that embedding-space detectability of non-stationarity degrades smoothly and that different models exhibit distinct, model-specific failure modes."
   [一手·摘要] 项目含义：明确把 TSFM 定位为"generic feature extractors"（生态共识表述），同时警告 hidden 的线性可探测性**随分布漂移平滑退化、且因模型而异**——项目在 regime 切换期必须把"context 有效性"本身纳入监控。
4. **Pandey, Neog, Jajoo, 2025, "On the Internal Semantics of Time-Series Foundation Models"**（arXiv:2511.15324）
   > "we systematically probe these questions using layer-wise analyses, linear recoverability tests, and representation similarity measures... early layers mainly capture local, time-domain patterns (e.g., AR(1), level shifts, trends), while deeper layers encode dispersion and change-time signals"
   [一手·摘要] 项目含义：层选择是有讲究的（线性可恢复性随深度变化），项目固定取"最后一层的最后 token"是合理起点但**层/位置选择应作为消融项**；组合概念下探针性能退化（"probe performance degrades, revealing interference between concepts"）。
5. （因果强化版）**Sanyal et al., 2025, "time2time: Causal Intervention in Hidden States to Simulate Rare Events in TSFMs"**（arXiv:2509.05801）
   > "we introduce activation transplantation, a causal intervention that manipulates hidden states by imposing the statistical moments of one event (e.g., a historical crash) onto another... Validated across two architecturally distinct TSFMs, Toto (decoder only) and Chronos (encoder-decoder)... steerable, semantically grounded representations are a robust property of large time series transformers."
   [一手·摘要] 项目含义：hidden 对预测有**因果**作用（不只是相关）是已发表结论，且在 Chronos 上成立——为"context 携带预测信息"提供了因果级别的证据范式（干预 hidden 改变预测）。

### 3.3 "hidden 相对模型输出还有没有增量信息" + 价值验证的标准实验设计

文献没有一篇在时序域用"hidden vs 模型自身输出"做主对照（Auer 2025 的对照是分类 SOTA；Belinkov 2021 讨论过探针对照选择的重要性），综合 NLP 惯例 + 上述时序工作，标准设计为：

1. **线性探针三臂对照**：同一冻结特征管道下，(a) hidden context 上线性头，(b) **模型自身输出**（预测路径/分位数）上线性头，(c) 原始输入特征上线性头 —— (a)−(b) 即 hidden 相对输出的增量，(a)−(c) 即相对裸输入的增量。
2. **端到端双臂**：ChronosAD 式 frozen embedding + 轻量下游模块 vs 同规模下游模块吃模型输出（控制参数量）。
3. **置换/打乱对照**：时间错位、跨资产置换、噪声化 context，确认下游增益来自表征内容而非泄漏或捷径（Belinkov 2021 的 shortcoming 对策）。
4. **固定时间切分 + 冻结评估集 + 置信区间**，回退规则（缺高频时怎么办）一并预注册 —— 与 C-X10-001 §5 的最小实验路线一致，不造新轮子。
5. （可选，因果级）time2time 式 hidden 干预实验，用于声明"context 因果上驱动预测"。

**项目含义**：项目 C-X10-001 §5 已规划"delta=0 基线 vs 双路 vs 对齐"三组，补上 (b) 臂（模型输出作对照特征）和 (3) 臂（置换对照）即达到文献标准，无需自创方法学。

## 4. 空白性验证结论（2026-09-12 声明："'干净低频条件化噪声高频'的显式架构无先例"）

### 4.1 搜索的关键词（arXiv API，2024–2026 检索范围）

| # | 查询 | 结果 |
|---|---|---|
| 1 | `"time series foundation model" AND ("order flow" OR "order book" OR "market microstructure")` | 2 篇，均不匹配（ProbFM 2601.10591 = 不确定性分解；Zhu & Cai 2609.04917 = AI 投资综述） |
| 2 | `"Kronos" AND "time series" AND ("high-frequency" OR "order flow" OR "order book")` | **0 篇** |
| 3 | `("multi-frequency" OR "low-frequency" OR "high-frequency") AND "time series foundation model"` | 11 篇，最近邻见 4.2 |
| 4 | `("low-frequency" AND "high-frequency") AND "foundation model" AND ("finance" OR "trading" OR "stock")` | 1 篇（msData） |
| 5 | `"Kronos" AND ("finance" OR "trading" OR "stock" OR "equity")` | 2 篇：Kronos 论文本身 + Mesfin 2026（见下） |

GitHub repo search（`Kronos fine-tune time series` / `Kronos trading OHLCV`）：见 §1.3，4 个 0★ 仓库，无 hidden+高频融合实现。GitHub 代码搜索需认证，未覆盖（§6）。

### 4.2 最近的 2–3 篇最近邻与差距分析

1. **Dewage, De Silva, Mondal, 2026, "Hybrid Neural-Classical Correction for Frozen Time Series Foundation Models: A Comprehensive Ablation Study on High-Frequency Stock Prediction"**（arXiv:2608.08825）
   > "We present a comprehensive study of hybrid neural-classical correction for adapting frozen TimesFM (200M parameters) to stock return prediction during the volatile opening trading hour."
   **差距**：操作对象是 TimesFM 的**输出**（预测值纠偏），不是 hidden states；无订单流/微观结构特征；无双路对齐/配对时点设计；纠偏模块是"冻结 TSFM + 神经-经典混合残差"，不是"低频模型条件化高频噪声"的生成式/特征式架构。→ 与项目架构**不同层**：它改输出，项目改输入侧特征。
2. **Khanal et al., 2026, "msData: A Millisecond-Resolution Network Dataset for Advancing Time Series Foundation Models"**（arXiv:2603.16497）
   > "current large-scale datasets predominantly focus on low-frequency time series... hindering their ability to capture the nuances of high-frequency time series data."
   **差距**：是**数据贡献**（让 TSFM 能训到毫秒级），非架构；无低频/高频双路；无订单流；方向是"单模型吞高频"，与项目"低频 TSFM 表征 + 高频私有特征双路"正交。
3. **Mesfin, 2026, "Sequential Structure in Intraday Futures Data: LSTM vs Gradient Boosting on MNQ"**（arXiv:2605.17724）
   > "Motivated by recent foundation-model research on financial candlestick data, including the Kronos architecture, we test whether five-minute OHLCV bar sequences contain exploitable sequential predictive structure at the scale of a single instrument dataset."
   **差距**：仅把 Kronos 当**动机引用**，实验用 LSTM vs GBT，未用 Kronos 模型、未取 hidden、无融合。→ 说明"Kronos + 高频"在 2026 年中仍只有动机级引用，无方法级跟进。（注意：这轻微修正已吸收的"arXiv 检索范围内无引用 Kronos 的后续论文"表述——存在动机级引用，但不构成方法先例。）

其他相关但不同类：time2time（2509.05801）是 hidden 的**因果干预/可解释性**研究；ChronosAD/Auer 是 hidden **当特征**但任务为异常检测/分类，均无高频订单流维度。

### 4.3 结论

在 arXiv 2024–2026 检索范围内（5 组关键词，见 4.1），**未发现**"TSFM/低频模型 hidden states + 高频订单流/微观结构特征显式融合"的已发表架构；2026-09-12 的空白性声明**维持成立**，但表述应精确为：*"（a）TSFM hidden + 高频订单流融合：无先例；（b）'干净低频条件化噪声高频'的显式双路架构：无先例（最近邻 Dewage 2026 是输出侧纠偏，非特征侧条件化）"*。保留 §6 的两个搜索盲区（GitHub 代码搜索未覆盖、HF 不可达）。

## 5. 项目 adapter 设计核对（对照官方 `KronosPredictor.predict` 流程逐点）

官方流程（[一手] 本地 `model/kronos.py`，版本 67b630e/2026-04-13）：列序 `open,high,low,close,volume,amount`（缺 amount→`volume*mean(price)`，缺 volume→0）→ 窗口 `np.mean/np.std`（ddof=0，`+1e-5`）→ `clip(±5)`（两处）→ stamp 5 字段 `minute,hour,weekday,day,month` → `tokenizer.encode(x, half=True)` → AR 循环中 `decode_s1` 每次只喂**最后 ≤ max_context(512) 个 token**，采样 s1（T/top_p）→ `decode_s2` → 多路径平均（`sample_count`）→ 反归一化 `*std+mean`。

| 点 | 官方 predict | 项目 adapter | 判定 |
|---|---|---|---|
| 列序/输入维度 | 6 列，amount/volume 缺失时 impute | 6 列（`KDATA`），缺失或 NaN **直接 raise** | **差异 D3**：adapter 更严格、不 impute（安全，但部署时缺列行为与官方不同，需在数据字典中固化"6 列必须齐"） |
| 归一化统计 | 仅 lookback 窗口 mean/std（#227 后 finetune 亦如此：本地 `finetune/dataset.py:110-113` `past_x = x[:past_len]`） | 仅观测窗口 mean/std（`values.mean/std(axis=0)`，ddof=0，`+1e-5`） | **一致**；且 adapter 有 `_validate_frame` 强校验"时间戳严格递增 + 末位==cutoff"，官方 predict 无此校验 |
| clip | ±5（默认） | ±5.0（默认） | **一致** |
| stamp | 同 5 字段 | 同 5 字段 | **一致** |
| 编码 | `encode(x, half=True)` | `encode(x, half=True)` | **一致** |
| context 读取 | AR 第 0 步 `decode_s1` 喂**最后 ≤512 token** | `decode_s1` 喂**整个窗口**，无 512 截断 | **差异 D1（实质）**：窗口 ≤512 时两者 context 完全相同；**窗口 >512 时 adapter 的 context 是在模型推理期从未见过的序列长度上算出来的**（分布外 + 注意力成本 O(T²) 失控）。建议 adapter 加 `assert len(window) <= max_context` 或显式截断到最后 512（截断需进预注册） |
| 生成 | 自回归采样未来 token（随机，`sample_count` 路径平均） | 不生成，单次 forward 读观测 token context | **差异 D2（实质，刻意）**：context 只由观测 token 决定、无生成 token 混入——这正是"干净低频条件"想要的性质，但与"模型在生成时实际看到的状态"不同；写论文时须声明 adapter context 是 pre-generation context |
| eval 模式 | `KronosPredictor` **从不调用 `.eval()`**（grep 证实）；kronos_small 配置 `token_dropout_p=0.1`（另有 attn 0.1/ffn 0.25/resid 0.25）→ README 用法下推理期 dropout 开启，context/预测本身随机（上游 PR #391 正修"dropout inference issues"） | `load_local_small` 显式 `.eval()`，重复计算 context 最大差 0（C-X10-001 §2 实测） | **差异 D4（实质，adapter 更安全）**：adapter 的 context 是确定性的；**反过来用官方 predict 输出做 §3.3 的 (b) 对照臂时必须先 `.eval()`**，否则对照臂含随机噪声 |
| 输出 | 反归一化未来 OHLCVA 路径 | 原始 `context[:, -1, :]` [B,512] + `means/stds` + 配对元数据 | **差异 D5（形式/设计）**：adapter 把反归一化统计量随 context 一并返回，供下游做尺度锚定——官方无此接口 |

### 泄漏状态（#227 相关）

1. **#227 的泄漏在 finetune 数据集路径**（full-window 含预测 horizon 的归一化），**推理路径（predict）本来就是 lookback-only**（本地代码核对 + #307 正文确认："Inference path looks clean. `KronosPredictor.predict()` computes the z-score mean/std on the lookback window only"）。
2. **项目 adapter 的 #227 类泄漏天然不存在**：归一化只用 cutoff 及之前的观测窗口，`_validate_frame` 从构造上禁止 cutoff 之后的任何数据进入。
3. **残留风险（非推理泄漏，是 train/serve 失配）**：若发布的 HF 权重是在 #227 修复**前**用 full-window 统计量预训练的（#307 无维护者回复；[二手] 社区猜测未重训），则模型内部假设的归一化统计量与部署时"仅 lookback"的统计量存在分布失配。该风险对官方 predict 路径同样存在，**不因 adapter 而新增**，但项目的"窗口自归一化"选择与官方一致，方向正确。
4. **本地 finetune_csv 路径仍有 full-window 归一化**（`finetune_csv/finetune_base_model.py:125`，#263 未及本地 HEAD）：只影响"若项目未来走 finetune_csv 微调"，不影响当前只读 adapter。

**差异点数量：实质流程差异 4 个（D1 无 512 截断、D2 无自回归采样、D3 无 impute、D4 eval-mode 显式化）+ 输出形式差异 1 个（D5）；归一化/clip/stamp/编码/泄漏状态与官方一致。**

## 6. 未能核实的点

1. **HuggingFace 从本机不可达**（`huggingface.co` 与 API 均 ECONNRESET）→ `NeoQuasar/Kronos-base` model card 原文未核实（下载量等沿用已吸收知识）；#307 的"官方是否确认重训"因此也只能以 GitHub issue 为限。
2. **#307 无维护者回复**：released 权重是否 #227 后重训，官方未确认；现有证据为社区猜测（[二手]）"they did NOT release the retrained models"。项目应在实验记录中把"权重训练期归一化口径"列为**未决变量**。
3. **GitHub 代码搜索需认证**，未覆盖：小型/私有仓库、非 arXiv 渠道（博客/私有 lab）的"Kronos hidden + 高频"实现无法排除——§4 空白性结论的覆盖范围是 arXiv + 公开 repo 名搜索。
4. **TimesFM 源码级**：`timesfm-forecasting` 包内是否存在未文档化的 hidden-state hook 未核实（仅 README/文档面为证）。
5. **Moirai/uni2ts fine-tune 程度**：README 未声明 LoRA/adapter/全参，未深入其 CLI 代码核实；Lag-Llama `scripts/finetune.sh` 亦未核实。
6. **arXiv 2510.26777 正文**：摘要未列具体用了哪些 TSFM 与哪种提取策略为最优，全文未读；引用时只用摘要级结论。
7. **Kronos 论文（arXiv-2508.02739v1）** 已按任务要求视为本地已精读，本轮未重复核对其中对 `decode_s1`/context 的任何声明。
8. **PR #227 的精确合并时间**：本地为 grafted shallow clone（仅 1 条可见 commit），2026-04-11 的修复落地时间沿用项目 claim 卡记录，未能从本地 git 历史独立验证；但本地代码状态（finetune/dataset.py 已修、finetune_csv 未修）与"#227 已合、#263 未合"的时序自洽。
