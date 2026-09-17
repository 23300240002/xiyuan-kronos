# 仓库盘点 inventory — 2026-09-17

> 用途：新一轮 deep literature research 前的防重复清单 + "理论×文献" / "代码×文献" 对照审计底稿。
> 方法：通读 文献调研/ 全部 6 个 .md、Kronos 精读、交叉前沿笔记、理论先行 4 篇、推导骨架、research/claims 全部 10 张卡（用户口径 9 张，实际 10 张）、research/ 5 个元文件、docs/数据管线使用手册.md、第一阶段 3 篇、学术准备与阅读路线.md、会前 4 篇（快速扫过），并逐函数读了 scripts/hf_data_pipeline.py 与 research/scripts/*.py。
> 行号为撰写时文件的近似行号，供快速定位。

---

## 1. 已吸收文献清单

格式：`主题 | 文献(作者/年份/arXiv号,若文中给出) | 从它取了什么 | 出处文件`

### 1.1 时序基础模型 / 金融 TSFM（文献调研/raw/01 已逐一 fetch 核验）

| # | 主题 | 文献 | 从它取了什么 | 出处 |
|---|---|---|---|---|
| 1 | K线LM基座 | Kronos (Shi et al./2025-08/arXiv:2508.02739, AAAI-2026接收[媒体证实]) | BSQ 20bit 粗细分词、层次AR、12B+ K线/45交易所/7粒度、+93% RankIC；已知归一化窗口数据泄漏(PR #227, 2026-04-11修复)→基线须注代码版本+权重hash | raw/01、raw/02、Kronos论文逐章精读、综述§7 |
| 2 | token化先行者 | Chronos (Ansari et al./2024/arXiv:2403.07815, Amazon) | "K线→token→LM"非孤立思路；分位数token化对异常值鲁棒，可借鉴进Tick Encoder；词表4096、KernelSynth/TSMix合成数据 | raw/01、交叉前沿§2.1、论文清单、初稿§3.2、学术准备A.1 |
| 3 | decoder-only范式 | TimesFM (Google/2023-10/arXiv:2310.10688) | decoder-only 零样本强基线锚点；Kronos +93% 的主要对照对象之一 | raw/01 |
| 4 | 长上下文统一预测 | Timer-XL (2024-10/arXiv:2410.04803) | 单模型长窗口路线，与"显式双尺度融合"对照（主张③） | raw/01 |
| 5 | FM回本分析 | When Do Foundation Models Pay Off? (2026-07/arXiv:2607.04919) | 必要质询：HS300小数据域上FM开销能否被微调收益覆盖 | raw/01 |
| 6 | 零样本可信度 | A Later Test Set Is Not a New Domain (2026-09/arXiv:2609.10357) | 预训练熟悉度虚高零样本宣称；引用Kronos数字须加批判注脚 | raw/01、raw/03辩证清单 |
| 7 | 因果×TSFM | Causal Analysis for TSFM (2026-08/arXiv:2608.24303) | "反事实推理降为展望"项升级时的方法参考 | raw/01 |
| 8 | 合成数据蒸馏 | Distillation of Synthetic Data for TSFM (2026-09/arXiv:2609.09586) | HS300数据量小时域内增强的潜在技术路线 | raw/01 |
| 9 | 预测形式论 | Foundation Model Forecasts: Form and Function (2025-10/arXiv:2510.19345) | 预测的"形式"(点/分位数/参数/轨迹)决定实用价值→分布头正当性（主张④范式依据，Top5必读） | raw/01、综述§4 |
| 10 | 竞争基座 | EXAONE Finance 1.0 (LG AI/2026-09/arXiv:2609.04239) | attention-free 金融TSFM；"金融FM该长什么样"无定论的活证据；related work必引 | raw/01、综述§5 |
| 11 | 竞争基座 | FinCast (2025-08/arXiv:2508.19609) | 与Kronos同期的通用金融TSFM（非K线专用） | raw/01 |
| 12 | 生成式桥接 | RefineBridge (2025-12/arXiv:2512.21572) | "FM出初稿+生成式桥接精化"与本项目架构哲学同构；Schrödinger bridge 进TimeFlow工具箱/展望 | raw/01、综述§4-5 |
| 13 | 批判性重审 | Re(Visiting) TSFM in Finance (2025-11/arXiv:2511.18578) | 数据侧质疑FM金融适用性；ρ(Δ)是从信息论侧接住质疑的量化机制（Top5必读） | raw/01、综述§1 |
| 14 | 金融benchmark | FinVerse (2026-08/arXiv:2608.03259) | 评估/消融必须对齐其口径，避免"自建指标"公信力问题（Top5必读） | raw/01、综述§4 |
| 15 | 质量感知分词 | QA-Token (2026-02/arXiv:2602.06394) | "token预算被噪声浪费"的分词器侧独立佐证；"按质量分配比特"路线（Top5必读） | raw/01、综述§1/§3 |
| 16 | 金融FM综述 | Advancing Financial Engineering with FMs (2025-07/arXiv:2507.18577) | 综述/申请书 related work 骨架来源 | raw/01 |
| 17 | TS scaling law | Scaling Law for Chaotic TS & Financial Predictability (2025-09/arXiv:2509.04921) | 主张⑥"噪声地板给幂律下界"的最近同类尝试，需对照界定贡献 | raw/01 |
| 18 | 同域波动率 | Volatility Forecasting under Market Regimes: HF Chinese Equity (2026-06/arXiv:2606.09478) | 目标域几乎重合（HS300高频+regime波动率）；regime划分方法可借鉴 | raw/01、综述§4 |
| 19 | 简单基准警示 | Predicting Realized Variance Out of Sample (2025-06/arXiv:2506.07928) | 波动率预测简单基准难超越→评估必须对照简单基准（审稿人第一刀） | raw/01、综述§4、raw/03 |
| 20 | 图波动率 | Graph-Based Modeling of Financial Volatility Dynamics (2026-08/arXiv:2608.26127) | 多资产波动率预测对照方法 | raw/01 |
| 21 | 流动性风险 | Illiquidity at Risk (2026-09/arXiv:2609.00943) | "流动性枯竭预警"目标项的直接文献锚点 | raw/01、综述§4 |
| 22 | OFI可预测性 | Hybrid VAR and NN Model for OFI Prediction in HFT (2024-11/arXiv:2411.08382) | OFI可预测性是成熟结论；微观特征清单里OFI地位由此确立 | raw/01 |
| 23 | 微观结构统一框架 | Square-root Impact / Order Imbalance / Volatility Unifying Framework (2025-06/arXiv:2506.07711) | ρ(Δ)记号应对齐此框架并说明增量（"可预测信息占比"这一特定量） | raw/01、综述§1 |
| 24 | 盘口隐态预警 | Early Detection of Latent Microstructure Regimes in LOBs (2026-04/arXiv:2604.20949) | "OFI等标准信号先天滞后(reactive)"；主张②最强外部弹药+微观编码器候选组件（Top5必读） | raw/01、综述§2 |
| 25 | 加密盘口模式 | Explainable Patterns in Cryptocurrency Microstructure (2026-02/arXiv:2602.00776) | 盘口特征跨资产稳定；本地Binance数据可先行验证 | raw/01、综述§6 |
| 26 | 经典锚点(非arXiv) | Roll 1984 / Hasbrouck 1991 / Andersen & Bollerslev 1997 / Cont-Kukanov-Stoikov 2014 | 2ω²地板与Roll bounce方差下界同族；有效价格分解；OFI Joss公式；正式写作必须引（页码待补） | raw/01、综述§1 |
| 27 | 无套利曲面FM | Latent Flow Matching for Arbitrage-Aware IV Surface Generation (2026-08/arXiv:2608.00616) | Flow Matching已在"金融+波动率+约束生成"落地；"潜空间+约束"设计是风险生成头现成参考 | raw/01、综述§4 |
| 28 | Flow最优执行 | FlowOE (2025-06/arXiv:2506.05755) | Flow策略用于Heston波动率最优执行（FM高频执行又一例证） | raw/01 |
| 29 | LOB反事实生成 | DiffLOB (2026-02/arXiv:2602.03776) | 扩散模型做LOB反事实生成；"反事实推理"展望项升级首选方法 | raw/01、综述§5 |
| 30 | 生成信号vs噪声 | Signal or Noise? Generative Models for Sensor TS (2026-07/arXiv:2607.04245) | 与噪声地板论证同题（生成视角）；分析框架可迁移到K线生成 | raw/01 |
| 31 | 文本→时序对齐 | GALA (2026-08/arXiv:2608.13741) | 跨模态条件生成趋势；术语撞车警示（文献cross-modal=文本/图像↔时序，本项目应称cross-source） | raw/01、综述§2 |
| 32 | 医疗FM生成集群 | MedFlow (arXiv:2609.04804) / PHINN (2606.15452) / fMRI频谱FM (2605.30387) | 背景趋势：Flow Matching时序生成医疗已热、金融刚起步→主张⑤时间窗(12–18月)判断依据 | raw/01 |
| 33 | 动态窗口 | Dynamic Windowing in Transformers via Regime (2026-09/arXiv:2609.05460) | "单模型自适应尺度"轻量路线；主张③的对照方法（"为什么不用动态窗口"要备好信息论反驳） | raw/01、综述§6 |
| 34 | K线视觉表征 | Visual Chart Representations for Crypto Regime Prediction (2026-05/arXiv:2605.00875) | K线的另一种编码（像素vs数值token）；regime预测设定可对话 | raw/01 |
| 35 | 金融多模态 | Deep Learning Models Meet Financial Data Modalities (2025-04/arXiv:2504.13521) | 多模态中订单流贡献的实证基础（主张②） | raw/01 |
| 36 | LLM agent交易 | MountainLion (2025-07/arXiv:2507.20474) | "LLM多模态（展望）"的现成系统对照 | raw/01 |
| 37 | 空白确认(否定性) | "干净低频条件化噪声高频"的金融TSFM架构：检索范围内未检索到 | 主张③先例缺口确认（空白=机会） | raw/01、raw/02 |
| 38 | 待核ID | Moirai (Salesforce, NeurIPS 2024) / Lag-Llama (ICML 2024) | 仅检索列表出现，arXiv ID未核验[待核]——新research别重复检索，直接补ID即可 | raw/01待办、综述§10 |

### 1.2 GitHub 生态（raw/02，gh api 一手抓取 2026-09-12）

| # | 主题 | 文献/对象 | 从它取了什么 | 出处 |
|---|---|---|---|---|
| 39 | 基座仓库 | github.com/shiyu-coder/Kronos (⭐38,694, 275 open issues, last push 2026-04-13) | 上游停滞5个月风险；PR #227泄漏修复/#243 batch修复→基线数字必须注明代码版本 | raw/02 |
| 40 | HF权重 | NeoQuasar/Kronos-base (0.1B, 下载118万+) | 采用面广；微调/评估应固定权重hash；组织名与GitHub账号关系[待核] | raw/02 |
| 41 | 衍生生态 | 10个衍生repo（RayCodes_Kronos 30★最高 / Kronos-Studio / kronostrader / kronos-market-lab 等） | 应用层天花板30★、研究层真空带；对外与营销式宣称区分 | raw/02 |
| 42 | 金融LLM生态 | FinGPT (AI4Finance-Foundation) | 金融LLM最活跃生态[本次未抓数据，待核] | raw/02、raw/01交叉 |
| 43 | 生态空白(否定性) | vnpy/joinquant/quantlib周边无TSFM集成；金融K线离散分词检索范围内仅Kronos；DeepLOB系开源未逐一核验 | 中文量化生态FM采用滞后→公开即先行者 | raw/02 |

### 1.3 媒体/社区（raw/03，二手-搜索摘要，未逐篇fetch原文）

| # | 主题 | 文献/对象 | 从它取了什么 | 出处 |
|---|---|---|---|---|
| 44 | AAAI状态 | AI Product Hub (2026-08-04) 等中文媒体 | AAAI-2026"已接收"（此前"投稿"）→所有材料须改状态[正式引用前回官方页面核] | raw/03、综述§7 |
| 45 | 团队背景 | 知乎"清华大学"标题[二手] / shiyu-coder身份未检索到 | 勿引用，先核实"清华"关联 | raw/03、raw/02 |
| 46 | 舆论落差 | CSDN"三条命令预测"(2026-08-31) / HN检索0条直接讨论 | 公众预期管理；英文preprint窗口6–12个月；公开舆论场无系统性批评→噪声地板论证差异化位置 | raw/03、综述§8-9 |

### 1.4 核心7篇+可选（论文清单与获取链接.md / 初稿 / 执行报告，已精读并吸收）

| # | 主题 | 文献 | 从它取了什么 | 出处 |
|---|---|---|---|---|
| 47 | 订单簿随机模型 | Cont, Stoikov & Talreja (2010), Operations Research 58(3):549-563 | 订单簿马尔科夫模型；市价单/限价单/撤单三事件分类；价格冲击度量；tick特征重要性 | 论文清单、初稿§1.1、执行报告 |
| 48 | 有效价格分解 | Hasbrouck (1991), J. Finance 46(1):179-207 | P=P_eff+η分解；信息份额；Var(r_Δ)=σ²Δ+2ω² 与 ρ(Δ) 的实证来源（"1min约40%噪声"说法出处） | 论文清单、初稿§1.2、执行报告§4.1、开会准备Q2 |
| 49 | 知情交易 | Easley & O'Hara (1987), JFE 19(1):69-90 | 交易量作信息代理；大单信息含量；PIN模型；"大单占比/买卖不平衡"特征构造 | 论文清单、初稿§1.3 |
| 50 | LOB卷积编码 | DeepLOB (Zhang, Zohren & Roberts 2019, IEEE TSP 67(11); arXiv:1808.03668) | 2D张量[T,2D]表示；1×2/1×D/T×1卷积；方向分类任务(k步中间价变动)；z-score归一化；Tick Encoder架构参考+消融"仅微观"对照 | 论文清单、初稿§2.1、执行报告、会前准备§七 |
| 51 | 跨市场普适性 | Sirignano & Cont (2019), Quantitative Finance 19(9); arXiv:1803.02269 | 100只股票LOB的LSTM特征跨市场可迁移→"加密上训练→A股"路线依据；OFI/深度比/价差时序为普适特征 | 论文清单、初稿§2.2、开会准备Q4 |
| 52 | 金融LLM | FinGPT (Yang et al. 2023, arXiv:2306.06031) | 金融数据特殊预处理；LoRA微调；文本→BERT→拼接到时序嵌入（未来加新闻/公告的参考） | 论文清单、初稿§3.3 |
| 53 | 可选经典 | Glosten & Milgrom 1985 / Kyle 1985 / Avellaneda & Stoikov 2008 / TimeGPT / Moirai(多频率预训练) | 补充阅读清单（未读） | 论文清单 |

### 1.5 交叉前沿笔记（高频量化与时序基础模型交叉前沿….md，2026-05-29 Gemini导出，二手但已系统吸收）

| # | 主题 | 文献 | 从它取了什么 | 出处 |
|---|---|---|---|---|
| 54 | 线性基线 | Li, Qi, Li & Xu (2023) Revisiting Long-term TS Forecasting (arXiv:2305.10721) | 单层线性+RevIN+Channel Independent匹敌Transformer→"先做对预处理/平稳化"；消融必比baseline | 交叉前沿§3.1、学术准备A.5 |
| 55 | 联邦时序FM | Time-FFM (Liu et al., NeurIPS 2024) | 时序特征→文本token模态复用LLM；动态提示适配；全局编码器+局部预测头个性化联邦 | 交叉前沿§3.2 |
| 56 | 稀疏MoE时序 | Time-MoE (Shi et al., ICLR 2025) | 2.4B参数稀疏专家；动态路由；多分辨率预测头→显存/算力墙解法 | 交叉前沿§3.3 |
| 57 | 时空扩散 | UrbanDiT (NeurIPS 2025) | DiT+统一提示学习做开放世界时空生成 | 交叉前沿§3.4 |
| 58 | 嵌套时空预测 | Nested Spatio-Temporal Forecasting (Ai et al. 2026, arXiv:2605.16447) | 谱聚类宏观区域+coarse-to-fine渐进预测→与Kronos粗细分词精神一致 | 交叉前沿§3.4 |
| 59 | 跨频基础模型 | Moirai (Woo et al., ICML 2024; LOTSA 270亿观测) | 任意变量注意力+多斑块投影实现跨频迁移；变长上下文讨论作旁证 | 交叉前沿§4.1、清单:假设4 |
| 60 | 频域注意力 | FreEformer (IJCAI) | vanilla注意力矩阵低秩缺陷→叠加可学习全秩结构矩阵+行归一化修复 | 交叉前沿§4.2 |
| 61 | 谱循环 | SpecRec (IEEE) | 频域线性时间循环=带跨频耦合的自适应谱滤波；Sobolev保真度+极点正则化损失 | 交叉前沿§4.2 |
| 62 | 多尺度解耦 | HopFormer (ICLR/OpenReview) | 多尺度频段隔离+跨频Transformer块正交融合+Metropolis-Hastings协变量寻优 | 交叉前沿§4.2 |
| 63 | 文本-时序融合 | TTF框架 (Emergent Mind 2025综述条目) | 双流网络：时序Patching(PatchTST/MOMENT)+文本(BERT/GPT-2)，时序作Query、文本作K/V | 交叉前沿§4.3 |
| 64 | 扩散综述 | Yang et al. (2024) A Survey on Diffusion Models for TS and Spatio-Temporal Data (ACM CSUR) | 扩散范式理论根基：前向SDE加噪+score matching反向去噪 | 交叉前沿§5.2 |
| 65 | Rectified Flow时序 | FM-TS (arXiv:2411.07506) | 矫正流直线传输；无条件/条件生成FID SOTA+数量级提速 | 交叉前沿§5.3 |
| 66 | 频域FM | SpectFlow (Moghadas & Munteanu 2025, NeurIPS OpenReview) | 89k参数单层复值线性层做频域流匹配（振幅/相位偏移） | 交叉前沿§5.3 |
| 67 | 反事实时序解释 | CFWoT (Sun et al. 2024) / CounTS (Yan et al. 2023) | RL动态生成解释 / Pearl框架评估外生协变量（传统Doubly Robust的高频局限） | 交叉前沿§6.3 |
| 68 | 因果扩散生成 | DiffPO / CaTSG (arXiv:2509.20846) | 溯因-干预-预测三阶段+因果score函数嵌入扩散SDE/流匹配ODE | 交叉前沿§6.3 |
| 69 | 因果推理阶梯 | Pearl's Ladder of Causation + Morgan & Winship (2014) | 关联/干预/反事实三阶梯映射到HFT（压盘单干预、闪崩反事实） | 交叉前沿§6.2、学术准备E |
| 70 | LOB因果定价 | Causal inference in LOB & Optimal Pricing (arXiv:2506.18147) | 订单簿因果干预与最优报价 | 交叉前沿§8 |
| 71 | NLP语料背景 | WikiText-103 (Merity 2016) / C4 (Raffel 2020) / The Pile (Gao 2020) | Chronos引用：时序数据规模-质量与NLP差距→数据天花板 | 交叉前沿§2.1 |
| 72 | 合成数据方法 | KernelSynth / TSMix (Chronos原论文内) | 高斯过程合成+mixup增强突破数据天花板 | 交叉前沿§2.1、学术准备A.1 |
| 73 | Chronos迭代 | Chronos-2 / Chronos-Bolt (Amazon Science Blog 2024) | ICL机制+高效注意力→零样本多元/协变量联合预测 | 交叉前沿§2.1 |

### 1.6 学术准备与阅读路线.md（模块A–F精读清单，均为"缺口=尚未精读"，已登记待读）

| # | 主题 | 文献 | 从它取了什么（计划取） | 出处 |
|---|---|---|---|---|
| 74 | token化嵌入 | ToTEM (Talukder et al. 2024, arXiv:2402.16412) | 编码器-量化器-预测器三段结构与GPT-2词表类比 | 学术准备A.2 |
| 75 | BSQ原文 | Image and video tokenization with BSQ (arXiv:2406.07548) | Kronos粗/细拆分后词表规模变化、codebook collapse避免 | 学术准备A.3 |
| 76 | 离散化实证 | Choo et al. (2021) Effectiveness of Discretization in Forecasting | 离散化何时优于实值回归→融合消融理论依据 | 学术准备A.4 |
| 77 | 微观结构教材 | O'Hara, Market Microstructure Theory (Wiley 1998, 本地) | 信息不对称/做市/订单类型；ch1-3,8,9精读 | 学术准备B |
| 78 | HFT实践书 | High-frequency trading: a practical guide (Wiley 2013, 本地) | 数据字段与执行细节（浏览） | 学术准备B |
| 79 | 逐笔冲击度量 | Cont, Kukanov & Stoikov (2014) The price impact of order book events | 逐笔事件对中间价冲击度量；tick特征token化前定义直接借鉴（与#26同一篇） | 学术准备B.2 |
| 80 | 未成交订单信息 | O'Hara & Yuan (2013, J. Finance) Widening the Net | 未成交订单信息量 | 学术准备B.4 |
| 81 | DeepLOB另一署名 | Jaiswal & Zohren (2019) DeepLOB | 五档LOB CNN+LSTM基线（与#50同一篇的合著署名） | 学术准备B.5 |
| 82 | 本地研报×5 | 海通20200223逐笔高频因子 / 兴业20221109微观结构剖析 / 兴业20250508订单簿资金流因子簇 / 华泰20231016 GPU加速高频因子 / 华泰金工因果推断初探 | 特征清单工程参考+国内语境因果因子 | 学术准备B.6/E.4 |
| 83 | DDPM | Ho et al. (arXiv:2006.11239) | 前向加噪/反向去噪/简化损失（范式C原始定义） | 学术准备C.1 |
| 84 | Score-SDE | Song et al. (arXiv:2011.13456) | score函数、probability flow ODE、离散/连续统一视图 | 学术准备C.2 |
| 85 | Flow Matching | Lipman et al. (ICLR 2023 best paper, arXiv:2210.02747) | 条件向量场与直线化路径；训练比DDPM便宜 | 学术准备C.3 |
| 86 | Rectified Flow配方 | Esser et al. Scaling Rectified Flow Transformers (arXiv:2403.03206) | 大规模训练配方；三范式对比中"流匹配"配置实现依据 | 学术准备C.4 |
| 87 | 金融生成基线 | Diffusion-TS (2024) / TimeGrad (JMLR 2021) / TimeVAE (AAAI 2022) / TimeGAN (NeurIPS 2019) | 金融侧生成对照（只需读方法节） | 学术准备C.5 |
| 88 | 回测方法论 | López de Prado, AFML (Wiley 2018, 本地) | 分数阶差分/12-32%规则/purged+embargoed CV/元标注/组合净化——回测节与HF-FinTS切分直接依据 | 学术准备D |
| 89 | 去膨胀夏普 | Bailey & López de Prado (2015, J. Risk) Deflated Sharpe Ratio | 策略数量对Sharpe阈值校正；消融显著性判断 | 学术准备D.1 |
| 90 | ML资产定价 | Gu, Kelly & Xiu (2020, J. Finance) | 交叉验证泄漏与多重测试的资产定价版本 | 学术准备D.2 |
| 91 | GARCH族 | Engle (1982) GARCH / Glosten (1993) EGARCH | 传统风险预警基线（风险AUC对照） | 学术准备D.3 |
| 92 | 回测框架 | Qlib (arXiv:2009.11189) | 回测框架工程参考 | 学术准备D.4 |
| 93 | 因果教科书 | Hernán & Robins (2020) Causal Inference: What If | 交换性/无未测混杂假设表述→identifiability节措辞来源 | 学术准备E.1 |
| 94 | Pearl原著 | Pearl, Causality (Cambridge 2009, 3rd ed.) | SCM/do演算/反事实定义选读 | 学术准备E.2 |
| 95 | 双重ML | Chernozhukov et al. (2018, Econometrics J) DML | 高维协变量下因果效应估计（"干预后收益分布变化"可选方法） | 学术准备E.3 |
| 96 | LLM scaling law | Kaplan et al. (2020, arXiv:2001.08361) | 幂律拟合三项分解（主张6锚点） | 学术准备F.1 |
| 97 | TSFM scaling实证 | Towards Neural Scaling Laws for TSFM (arXiv:2410.12360) | HF-FinTS scaling节方法学直接对标 | 学术准备F.2 |
| 98 | 对比基座 | Sundial家族 (arXiv:2502.00816) / GIFT-Eval | 申请书承诺的对比对象（GIFT-Eval需自行检索最新版） | 学术准备F.3-4 |
| 99 | benchmark组织 | Monash archive / M5竞赛 | HF-FinTS文档结构参照 | 学术准备F.5 |
| 100 | TS模型综述基准 | Deep time series models: survey and benchmark (arXiv:2407.13278) | baseline清单核查 | 学术准备F.6 |

### 1.7 理论文件中引用/待核对的经典（未落卡、多数未核对原文）

| # | 主题 | 文献 | 从它取了什么 | 出处 |
|---|---|---|---|---|
| 101 | 高分辨率量化 | Zador (1963) / Gersho (1979) | 引理2（D≈R²/(12M^{2/d})）的严格陈述来源（严格性缺口1：需引用原文） | 推导骨架§5/§9 |
| 102 | 微观噪声一般形式 | Aït-Sahalia / Mykland & Zhang (2005) | A2(iid噪声)超高频失效时的一般形式（缺口2） | 推导骨架§9、学习过程Q&A |
| 103 | ω估计量 | Bandi-Russell 双尺度估计 | ω的正规估计方法（缺口2） | 推导骨架§9 |
| 104 | 方差比检验 | Lo-MacKinlay (1988/1989) | 拒绝纯RW的检验（Lemma1"方差∝期限"的实证对偶） | 学习过程Q7 |
| 105 | 联合假设问题 | Roll (1978) | 检验RW=同时检验有效市场+预期收益模型→RW无法单独证明 | 学习过程Q7 |
| 106 | I-MMSE关系 | Guo, Shamai & Verdú (2005) | dI/dr=mmse(r)/2（定理3的核心工具；[既有结果，出处未联网核对]） | C-T9-002§10.3 |
| 107 | 信息预算恒等式 | B=A+I（变分推断/率失真标准分解） | C-T9-002定理1；[既有结果，出处待核] | C-T9-002§2、C-CM-004§2 |
| 108 | 正则化路径单调性 | 多目标优化/正则化路径标准结论 | 命题O（C-CM-001 §1；[既有结果，文献未检索]） | C-CM-001/002/004 |
| 109 | 条件DPI | 互信息链式法则/条件数据处理不等式（标准信息论） | C-T12-002命题1/3（[既有工具]，不作新颖性主张） | C-T12-002 |
| 110 | 波动率签名图 | 高频波动率文献通识（RV偏误∝1/Δ） | 推论1.1（校准ω与σ的无模型方法） | 推导骨架§4、学习过程§7勘误2 |

---

## 2. 理论对象清单

### 2.1 research/claims/ 卡片（10 张）

| ID | 一句话结论 | 状态 | 关键公式/命题 |
|---|---|---|---|
| C-CM-001 | 跨模态一致性最小问题：平方一致性作用在未归一化表示上存在缩放逃逸；无噪声模型最优点互信息发散（ΔI度量退化）；私有成分与目标无关时一致性"免费"（反例边界） | 命题O已证(既有,文献未检索)；命题CM-1(a)(b) CONJECTURED（数值支持、未加噪）；§4待做 | 命题O：δ₂>δ₁⟹D(θ̂δ₂)≤D(θ̂δ₁)且R(θ̂δ₂)≥R(θ̂δ₁)；ΔI=I(T;Z_H,Z_L)−I(T;Z_H)；δ路径数值表 |
| C-CM-002 | 含噪控制模型（κ=0）全部量由协方差矩阵闭式导出；任意γ≥0最优θ*=0，ΔI沿路径恒定（"不增"以退化形式成立）；T5边缘分布不决定配对结构；T6 ΔI含去噪增益≠私有信号贡献 | 全部闭式INTERNALLY_CHECKED；6项回归PASS(0.13s) | D=2(θ+ν)；R_H=(ν+θ)/(1+ν)；R=(ν+θ)/(2+ν−θ)；ΔI=½ln((2+ν−θ)/(1+ν))；R*=ν/(2+ν) |
| C-CM-003 | 统一高斯族（T_κ目标相关开关）：κ=0时ΔI单调性已证；κ=1数值(9个ν)沿δ路径单调不增、无反例 | κ=0已证(解析+差分1.71e-10)；κ=1 CONJECTURED；新颖性未检索 | u²=(√(1−θ)+κ√θ)²/(1+2κ²)；R=1−2u²/(2+ν−θ)；ΔI=½ln(R_H/R)；R_min(ν)有限性界 |
| C-CM-004 | 阶段性收口：定理A(κ=0,ΔI沿δ路径恒定)已证；定理B(正则化全局最优必在[0,θ₀]内,不依赖凸性)已证；命题C(κ=1,ΔI沿路径不增)CONJECTURED（θ≥½段已证、θ<½段仅数值）；ν→0发散依赖θ路径；项目接口5条件未确认 | 定理A/B已证；命题C CONJECTURED；文献新颖性待核验(未联网)；🔶阶段性收口(不再扩展玩具模型) | dΔI/dθ=½(R_H'/R_H−R'/R)；(u²)'=(κ(1−2θ)/√(θ(1−θ))+κ²−1)/(1+2κ²)；§7项目接口问题 |
| C-CODE-HF-001 | 无前视清洗/窗口统计/过去式对齐可独立于理论与GPU训练完成；旧extract_features.py(窗口起点标签+均值OFI)与align_data.py(精确merge+ffill/bfill)存在前视/语义问题，记录在案 | [代码实现]INTERNALLY_CHECKED；离线确定性测试PASS；未接Tushare、未训练 | 6函数API：clean_orderbook/add_event_ofi/aggregate_orderbook/normalise_kline/align_features_to_kline/make_future_labels |
| C-T12-001 | 四条"从X到Y"范式转换主张：Y1多频并列→低频条件化高频；Y2固定比特→按ρ(Δ)分配比特；Y3堆特征→按信息增量筛特征；Y4事后回测排名→事前可证伪边界命题 | 全部CONJECTURED；Y3原依据(I(x;技指\|完整OHLCV)=0)被自身反例推翻(条件集应为Ỹ)，已重述为C-T12-002；Y1/Y2/Y4未做 | 每条绑定可证伪问题+推翻条件；1年IR标准误≈1.0(24期bootstrap,CI±1.9) |
| C-T12-002 | 特征信息增量两机制：支撑内确定性特征(技术指标)增量≤量化损失上界、随保真度趋于0；支撑外特征(微观结构)与比特预算无关(无损下构造仍1bit) | 命题1–3[推导结果]有证明+精确数值ALL PASS(11/11,分数枚举)；新颖性未检索、不作主张 | 命题1: I(x;g(Y)\|Ỹ)≤I(x;Y\|Ỹ)≤H(Y\|Ỹ)；推论1(无损⟹0)/推论2(渐近无损⟹0)；命题2构造(Y⊕X_M)；命题3两项分解 |
| C-T9-001 | 原命题P₀(边缘对齐必然坍塌)被数值反例REFUTED；真正判据=编码器噪声尺度σ与先验尺度之比；L_align(分支C)与Y1"要求互补"可能目标冲突(猜想) | P₀ REFUTED保留；P₁降级CONJECTURED；本卡被C-T9-002取代、保留为审计对象 | σ扫描两段结构(σ≪1无害/0.3≤σ≤0.7 Δμ反向增大/σ≳1坍塌)；勘误:保留率97.27%(原94.85%口径错) |
| C-T9-002 | 对齐损失两个目标性质截然不同：B(条件KL平均)在纯对齐下本族内必坍塌(严格二次,任意σ)；A(边缘KL)存在阈值σ=τ(σ≥τ坍塌,σ<τ最优r*由mmse(r*)=σ²/τ²定)；小SNR系数I=m²/(8σ²) | 定理1/2/2'/3 INTERNALLY_CHECKED(证明+数值)；命题4数值；定理1与I-MMSE为[既有结果,出处未联网核对]；🔒SEALED(高斯子问题) | B=A+I；B=(½)(σ²/τ²−1−ln(σ²/τ²))+c²/(2τ²)+m²/(8τ²)；c*=1/(2+δ/τ²),m*=1/(1+δ/(2τ²))；∂A/∂r=(σ²/τ²−mmse(r))/2 |
| C-X10-001 | 真实Kronos decode_s1可返回token级context[B,T,512](kronos-small d_model=512)，Z_L工程候选可构造；但KronosPredictor只输出预测路径、项目L_align未定义→跨模态对齐尚不能落地 | FORMALIZED(接口已定位)+BLOCKED(对齐定义未定)；未做训练实验 | context形状(1,8,512)；重复计算max diff=0；§7完成判据3条 |

### 2.2 推导骨架/理论先行系列中的定理与恒等式（未落卡者标注"未落卡"；A1–A5/H1–H6 已登记于 research/assumptions.md 为 A001–A005/H1–H6）

| 对象 | 内容 | 状态/出处 |
|---|---|---|
| A1 (A001) | 潜在对数价格 dP_t=σ_t dW_t（半鞅/随机游走），E[σ_t²]=σ² | 未落卡[二手建模假设]；推导骨架§1、assumptions.md |
| A2 (A002) | 观测 P̃=P+η，η iid、Eη=0、Var(η)=ω²、ω与Δ无关 | 未落卡；超高频下失效(需Aït-Sahalia/Mykland-Zhang一般形式) |
| A3 (A003) | K线OHLC=区间观测价首/末/最大/最小；amount≈VWAP×volume | 未落卡(定义) |
| A4 (A004) | 输入按窗口自身z-score截断±5 | 未落卡；已核S-11代码→升级[一手] |
| A5 (A005) | tokenizer压6维→k=20bit；有效维数d∈[4,5] | 未落卡；k=20已核[一手]，d未核(计数依据在学习过程§5) |
| 引理1 | Var(r_Δ)=σ²Δ+2ω²（信号线性衰减+噪声常数地板） | 未落卡(推导骨架§2有证明)；同式见学习过程§5、初稿§1.2、执行报告§4.1 |
| 命题1(骨架) | ρ(Δ)=σ²Δ/(σ²Δ+2ω²) 严格单调增，ρ(0+)=0，ρ(∞)=1，临界尺度Δ*=2ω²/σ²处ρ=½ | 未落卡(有证明)；数值表:日线0.998/5min0.931/1min0.730/10s0.310(ω=0.05%,σ=1.8%,占位待标定) |
| 推论1.1 | RV(Δ)≈σ²T+2(T/Δ)ω² 随1/Δ线性发散；波动率签名图斜率给2ω²、截距给σ²T；两频率即可无模型标定 | 未落卡 |
| 推论1.2 | E[H−L]≈1.60σ√Δ+cω（高低价膨胀）；无量纲比随Δ减小上升(日线≈1.65,1min≈2.5)；把H-L当波动率代理的高频因子都在吃偏差 | 未落卡 |
| 推论1.3 | ρ(Δ)是仅用历史价格信息时任意模型的R²上界；1min上R²>0.73应先怀疑泄漏 | 未落卡 |
| 引理2 | 固定码率量化失真下界 D≈R²/(12M^{2/d})（Zador均匀特例）；每维档位2^{20/d}(d=4→32档,d=5→16档) | 未落卡(严格形式需引Zador1963/Gersho1979) |
| 命题2(骨架) | 窗口std/单根新息=√((N²−1)/(12N))≈√(N/12)=6.53(N=512,与Δ无关)；量化噪声/单根新息≈36·√D/R∈{0.32,0.65,1.03}(d=4,5,6)且与频率无关 | 未落卡(推导骨架§6)；证否"1min结构更平滑"(修正清单:H2①)；残留:d可能随频率变+BSQ非最优量化器(比值是乐观下界) |
| 命题3(骨架) | 512上下文缺的不是数据量是波动率分位定位(窗口局部波动率估计相对误差√(2/N)=6.2%两频率相同；日线窗口含7–15个波动周期,1min不足1个) | 未落卡(推导骨架§7)；τ与"分位信息"需形式化(缺口4)；给出不依赖tick数据的跨频融合动机 |
| 命题O | 正则化路径单调性（见C-CM-001） | 已落卡C-CM-001；[既有结果,文献未检索] |
| H1 | ΔI(f)随频率上升且1min处达"值得单独建编码器"量级 | 未落卡；assumptions.md H1；未做(数据依赖) |
| H2 | ①粗码解释方差占比随频率上升②采样粗码监督在1min收益符号可能翻转 | 未落卡；①机制已被骨架§6修正为ρ(Δ)驱动；官方use_teacher_forcing开关使②降为小时级 |
| H3 | 三范式优劣方向可预先推导(尾部AR最差/推理流匹配占优/逐点AR最优) | 未落卡；assumptions.md H3；**未做(主菜)**；被X-04(接入空间未定)阻塞 |
| H4 | 512跨频跨度失配；阶段一微调应从5min起(10.7天最接近预训练典型跨度) | 未落卡；推导已完成(命题3给机制)；部分 |
| H5 | 内容四因果声明必须收窄为反事实模拟(≠do-演算干预效应) | 未落卡；1天纯写作；未做 |
| H6 | 高频scaling law参数化单位应是信息量(熵率归一化)而非K线根数 | 未落卡；未做(大网格,后期)；噪声地板给不可约误差下界=真理论贡献点 |
| A006–A008 | 波动率均值回复时间τ / 低频含σ_t信息 / 技术指标是OHLCV确定性函数 | 未登记(assumptions.md"尚未登记"表,待补) |

### 2.3 信息预算/预训练目标（一页推导脚手架§1 + 会前材料A，未落卡）

| 对象 | 内容 | 出处 |
|---|---|---|
| 预训练目标 | L_ar=−E[Σ(log p(b_t^c\|b_<t)+log p(b_t^f\|b_<t,b_t^c))]；tokenizer三项损失L_coarse+L_fine+λL_quant(λ=1,连续空间L2重建非交叉熵)；细头用采样的粗码(非teacher forcing) | 脚手架§1.2-1.3、会前材料A§2-3、Kronos精读§4 |
| 信息预算 | 一根K线20bit装4个价格水平需~50-70bit→压缩3倍以上(丢分辨率)；512根=10,240bit历史；有效自由度≈4(2个OHLC不等式+amount≈p×V) | 脚手架§1.5、会前材料A§4 |
| 512跨频跨度 | 日线≈2.05年 / 5min≈10.7天 / 1min≈2.13天(三个数量级失配) | 脚手架§1.5、学习过程§5、骨架§7、会前材料A§4、C-T12-001 Y1 |

---

## 3. 代码对象清单

### 3.1 scripts/hf_data_pipeline.py（12 个定义，逐函数）

| 文件::函数 | 功能 |
|---|---|
| hf_data_pipeline.py::CleaningReport | 清洗审计计数dataclass（重复时间/坏时间戳/非有限/坏价格/负量） |
| hf_data_pipeline.py::_utc_times | 解析时间戳为UTC-aware；naive必须给assume_tz，拒绝静默把Tushare中国时间当UTC |
| hf_data_pipeline.py::_require_columns | 必需列缺失检查 |
| hf_data_pipeline.py::clean_orderbook | 清洗盘口：显式时区、去重(keep last)、剔非有限/非正价格/交叉盘口/负量；不填充缺失快照；返回审计计数 |
| hf_data_pipeline.py::add_event_ofi | top-of-book事件OFI（Cont式相邻盘口变化公式）；首快照置0并标ofi_valid |
| hf_data_pipeline.py::clean_trades | 清洗逐笔成交：保留同时间戳多笔、side归一buy/sell、不按价格猜方向 |
| hf_data_pipeline.py::aggregate_trades | 右闭右标窗口聚合成交：trade_count/volume_sum/notional/vwap/price_first/last/signed_volume_imbalance |
| hf_data_pipeline.py::aggregate_orderbook | 右闭右标窗口聚合盘口：event_ofi(±abs)/spread_bps(mean,std)/mid_price_last/mid_return/realized_mid_vol/depth_imbalance/book_slope/snapshot_rate；无前向后向填充 |
| hf_data_pipeline.py::normalise_kline | Tushare K线标准化：调用者必须显式声明bar_start/bar_end(不猜)、OHLC约束检查、产出cutoff_time+asset_id |
| hf_data_pipeline.py::align_features_to_kline | merge_asof(direction='backward')过去式对齐：仅feature.cutoff_time≤kline.cutoff_time；缺失保留缺失+hf_available列 |
| hf_data_pipeline.py::make_future_labels | 按资产分组生成未来log return与未来实现波动标签（末行NaN） |
| hf_data_pipeline.py::run_sample | CLI入口：读parquet盘口→clean(Asia/Shanghai)→aggregate(1min)→可选输出 |

### 3.2 research/scripts/*.py（12 个文件，逐函数/逐模块）

| 文件::函数 | 功能 |
|---|---|
| audit_kronos_x10.py::main | X-10只读冒烟：真实KronosLocal tokenizer.encode+decode_s1，断言context形状(1,8,512)/logits(1,8,1024)/重复计算差=0 |
| kronos_context_adapter.py::ContextBatch | 部署级context数据类：[B,512]最后一观测token context + asset_ids/cutoff_times/means/stds元数据 |
| kronos_context_adapter.py::_stamp_frame | 时间戳→5维时间特征矩阵（minute/hour/weekday/day/month，对齐Kronos TemporalEmbedding） |
| kronos_context_adapter.py::_validate_frame | 窗口校验：OHLCVA列齐全、时间戳严格递增无重复、最后观测=cutoff_time、值有限 |
| kronos_context_adapter.py::extract_context | 每窗口独立z-score(±5,对齐KronosPredictor约定)→encode(half=True)→decode_s1→只返回最后观测token的context；不调自回归生成、不读未来/标签 |
| kronos_context_adapter.py::load_local_small | 加载本地tokenizer_base+kronos-small权重（HF_HUB_OFFLINE=1） |
| kronos_context_adapter.py::_smoke | adapter自测（输出KRONOS_CONTEXT_ADAPTER_SMOKE: PASS，context_last=(1,512)） |
| audit_t9.py::_mi_at_t / build_mi_table / mi | I(Y;Z)的1D自适应积分+2201点预计算查表(插值)，利用标度不变性只依赖t=m/σ |
| audit_t9.py::b_closed / a_fast | B闭式(高斯KL)；A=B−I恒等式免积分 |
| audit_t9.py::task_loss / grid_min | L_task=E(Z−Y)²；2D网格全局搜索argmin |
| audit_t9.py::cycle1 | 审计C-T9-001：恒等式B=A+I核验(最大偏差3.3e-14)、"保留率94.85%"口径更正(正确97.27%)、中心c被对齐免费吃掉 |
| audit_t9.py::_mi_direct / _a_direct_integral | 直接积分交叉核验(不经查表) |
| audit_t9.py::cycle2 | 纯对齐B必坍塌(闭式)、A阈值σ=τ扫描、B加任务损失闭式解(c*,m*)、A联合目标2D网格 |
| crossmodal_covariance.py::quantities | C-CM-002含噪控制模型：2×2协方差直接算D/R/R_H/条件方差/互信息/ΔI，无积分 |
| crossmodal_covariance.py::lam | λ(θ,ν)=(ν+θ)/(2(1+ν)) |
| crossmodal_covariance.py::main | C-CM-002验证：关系式最大偏差1.1e-16、γ=0解析最优θ*=0、ΔI闭式与单调、回归T1–T6全PASS |
| unified_family.py::quantities | C-CM-003统一高斯族(κ,θ,ν)全部闭式量（u/u²、D、R、R_H、I、ΔI） |
| unified_family.py::d_dI_dtheta / cov3 | ΔI中心差分(核验解析式)；(T,Z_H,Z_L)3×3协方差矩阵 |
| unified_family.py::theta_star | argmin_θ[R+δD]：2001点粗扫+二次插值精化（全闭式，无积分） |
| unified_family.py::main | 闭式vs2×2线性求解交叉(2.2e-16)、κ=0复现控制模型、R_min(ν)有限性表、T5族归属判定、T=S时R=θ/(2−θ)更正 |
| unified_family.py::cycle3 | κ=0解析导数vs差分(1.71e-10)、κ=1 δ路径(3ν×10δ)单调性、9个ν扫描找非单调区间(无) |
| regress_and_crossmodal.py::I_bpsk / mmse_bpsk | BPSK高斯信道互信息与MMSE的直接自适应积分 |
| regress_and_crossmodal.py::kl_gauss / B_closed / B_direct | 高斯KL闭式；条件KL平均B闭式+直接积分校验 |
| regress_and_crossmodal.py::regression_tests | C-T9-002第4次运行解析回归R1–R5（I(0)=0、I/r→½即小SNR系数m²/(8σ²)、mmse(0)=1、参数换算、KL闭式系数4.4e-16） |
| regress_and_crossmodal.py::crossmodal_closed / crossmodal_analysis | C-CM-001单位方差模型闭式量+δ路径+反例边界(T=S时R与θ无关) |
| verify_hf_data_pipeline.py::book_rows / main | hf_data_pipeline确定性测试：重复审计、UTC输出、cutoff单调、事件OFI非空、过去式对齐、标签末行缺失（HF_DATA_PIPELINE: PASS，无网络） |
| verify_t12_feature_bound.py::_h_bits/_marg/_mi_bits/_cmi_bits/_h_cond_bits/make_joint/check | 精确离散熵/互信息/条件互信息/条件熵（Fraction精确概率，无随机数） |
| verify_t12_feature_bound.py::(主流程Test A1/A2/A3/B/C) | C-T12-002命题1上界+等号、噪声目标、推论2保真度族衰减到0、命题2无损1bit构造；ALL PASS(11/11)；含两处实现bug已修记录 |
| verify_t9_alignment_collapse.py::mixture_kl_to_prior / mutual_information / objective / main | C-T9-001原始数值验证（保留备查）：混合KL数值积分、I(Z;Y)积分、Nelder-Mead最小化、σ扫描；已知缺陷(积分区间随参移动/单点初始化)已记录 |
| verify_t9_threshold.py::mmse / I_bpsk / A_direct / amin | C-T9-002定理3数值机器：MMSE/I直接自适应积分(替代Gauss-Hermite)、A直接积分、A的m极小(粗扫+极小) |
| verify_t9_threshold.py::main | I-MMSE有限差分核验(3.5e-10)、mmse单调性/端点、阈值求根vs直接极小(10σ,相对差0.00%)、σ=0.05归属判定、加任务损失一阶条件、m偶对称性 |
| verify_theorem_card.py::u2/du2/R_RH_D/dI/dI_analytic/dI_fd | C-CM-004独立复推基元；含第一版bug修正记录（ν误当κ传入u²致误报反例） |
| verify_theorem_card.py::theta0 / path | argmin R细扫(2e5点)+二次插值；δ路径(9个δ) |
| verify_theorem_card.py::cycle1 | 参数化核对(2.2e-16)、θ0双算法交叉、定理B越界点数=0、导数公式、κ=1时ΔI'>0核对(θ≥½解析段)、极小点唯一性 |
| verify_theorem_card.py::cycle2 | 多步长差分收敛、θ0粗细扫交叉(≤5e-8)、沿δ路径R不减/D不增/ΔI不增（独立实现,2.7s） |
| verify_y3_identity.py::joint_from_fn / _ent / _cond_ent / cmi / check | 离散联合分布(4D)的熵/条件熵/条件互信息枚举工具 |
| verify_y3_identity.py::main | Y3链式法则恒等式I(T;F\|S)=I(T;F\|H)+I(T;H\|S)−I(T;H\|F,S)五情形核验(最大1e-12)+三类F区分（F=h(S)时I=0；F用S外历史时I>0且不蕴含I(T;F\|H)=0） |

### 3.3 其他代码对象（class级，供审计索引）

| 文件::对象 | 功能/备注 |
|---|---|
| scripts/download_binance_kline.py::BinanceKlineDownloader/main | 币安K线下载（ccxt断点续传+限速+质量检查）【旧管线】 |
| scripts/download_binance_orderbook.py::OrderbookCollector/main | 订单簿实时快照采集（定期保存/Ctrl+C优雅退出/5-10-20档）【旧管线】 |
| scripts/extract_features.py::MicrostructureFeatureExtractor/main | 10个微观特征提取【有前视/OFI定义问题，C-CODE-HF-001记录，保留为历史产物】 |
| scripts/align_data.py::DataAligner/main | 精确时间戳merge+ffill/bfill/interpolate【前视风险已记录】 |
| scripts/run_pipeline.py::PipelineRunner/main | 一键串联（--test=1天数据）【旧管线】 |
| kronos_zero_shot_baseline.py::pick_device/main | 日线zero-shot RankIC基线脚本（理论先行_00要求会前跑；数据quant/data/daily_hs300,2801个parquet；预测长度须16倍数+设KRONOS_DIR） |

### 3.4 data/ 目录实际数据文件（ls 实测，未读parquet内容）

| 文件 | 大小 | 备注 |
|---|---|---|
| data/binance/kline/BTC_USDT_1m_2024.parquet | 57,917 B | 1天1m K线（1440根，2024-09-01~02） |
| data/binance/kline/BTC_USDT_1m_matched.parquet | 3,018 B | S-13登记为0行（matched为空文件，仅元数据） |
| data/binance/kline/BTC_USDT_1m_recent.parquet | 6,525 B | 近期1m K线 |
| data/binance/orderbook/BTC_USDT_orderbook_20260908.parquet | 30,179 B | 约9分钟盘口（200快照，2026-09-08 14:56-15:04） |
| data/features/BTC_USDT_microstructure_1min_20260908.parquet | 7,316 B | 9个1min窗口特征 |
| data/features/BTC_USDT_microstructure_1min_latest.parquet | 7,775 B | 最新特征文件 |
| （data/aligned/ 目录不存在） | — | 手册与交付清单声称的对齐数据目录实际缺失 |

### 3.5 docs/数据管线使用手册.md 描述的管线阶段

1. K线下载（download_binance_kline.py：ccxt、多symbol/时间周期、断点续传）
2. 订单簿采集（download_binance_orderbook.py：实时1秒间隔、5档、nohup后台）
3. 特征提取（extract_features.py：10特征 ofi/spread/mid_price/depth_imbalance/spread_vol/mid_vol/vol_concentration/slope/update_freq/large_order_ratio + 3σ质量检查）
4. 数据对齐（align_data.py：inner/left/outer + ffill/bfill/interpolate）
5. 一键运行（run_pipeline.py：测试模式=1天K线+1小时盘口+10特征+对齐+质量报告；完整模式=1周）
（注：新泄漏安全管线 hf_data_pipeline.py 未写入该手册v1.0，两者并存——旧管线有前视问题，新管线是C-CODE-HF-001产物）

---

## 4. 文档自认缺口（显式"未完成/待核验/阻塞/未检索/未联网/仅数值支持"等）

| # | 缺口表述 | 出处（文件+行号附近） |
|---|---|---|
| 1 | 严格性缺口5条：引理2需引Zador1963/Gersho1979严格陈述；A2的iid超高频不成立需Aït-Sahalia/Mykland-Zhang+Bandi-Russell估计量；极差/std比5.5需实测不引用；命题3的τ与"分位信息"需形式化(I(σ_t;窗口历史))；全部数值(σ=1.8%,ω=0.05%)是量级占位、标定前不得对外 | 理论_推导骨架.md §9（约154-160行） |
| 2 | 冲突1未决：ω取值两份文档差一倍(0.05%→ρ(1min)=0.730 vs 0.1%→ρ=0.43)；标定前任何依赖ρ具体数值的结论暂停引用 | research/notation.md（约31行）、dependency_graph.md X-03 |
| 3 | 待定义不得擅自补：L_align对齐对象(三分支结论完全不同)、三范式Diffusion/Flow接入空间(token空间or连续潜空间，**阻塞TP2**)、"方向"定义(单资产时序vs截面排序)、T12的X/Y | research/notation.md §5（约60-68行） |
| 4 | H1/H2/H5/H6未做；H3未做(主菜)；H4部分(推导完成) | research/assumptions.md（约21-26行） |
| 5 | A006/A007/A008三条隐式假设"没有任何文件把它们写出来过"，待补 | research/assumptions.md"尚未登记"表（约46-54行） |
| 6 | 命题4阈值σ=τ无证明(CONJECTURED)；定理1文献出处未核对(未联网)；二阶矩匹配为何不是KL最小化未解释；全部结论限一维二元Y高斯族；分支C(跨模态一致性)未建模——"项目最关心的分支仍空白" | research/claims/C-T9-002.md §9（约266-273行） |
| 7 | 命题C(κ=1)无解析证明、θ<½段仅数值支持；θ_δ全局最优性未证拟凸；既有工具O/G1/G2文献出处未核验；模型族限线性高斯一维目标 | research/claims/C-CM-004.md §4（约140-147行）、C-CM-003.md §5 |
| 8 | L_align项目接口问题未答：是否配对平方一致性/尺度锚定/Bayes头/两路都部署/标量目标——未答前C-CM结论只保留为诊断基准、不再建玩具模型 | research/claims/C-CM-004.md §7（约170-193行） |
| 9 | Y1/Y2/Y4现状"未做"；Y3"已重述、未经实证检验"；20→40-bit重量化可行性未验证(未读Kronos tokenizer一手代码) | research/claims/C-T12-001.md Y1(约39行)/Y2(约51行)/C-T12-002.md(约119行) |
| 10 | X-10状态FORMALIZED+BLOCKED：L_align对象/预测时点配对规则/同尺度/头使用/部署可得性均未回答；不能启用δ>0 | research/claims/C-X10-001.md §3（约40-42行） |
| 11 | C-CODE-HF-001：未接Tushare网络、未训练模型、数据供应商时间字段语义未核验、高频特征预测增量未证 | research/claims/C-CODE-HF-001.md"不能据此声称"（约38-44行） |
| 12 | 文献调研待办：Moirai/Lag-Llama arXiv ID未核验；经典微观结构4篇补期刊卷页；FinVerse/EXAONE会议归属与复现代码可用性 | 文献调研/raw/01（约160-165行待办区） |
| 13 | raw/02：HF组织NeoQuasar与shiyu-coder关系待核；FinCast/EXAONE/RefineBridge开源状态未逐一核验；FinGPT本次未抓数据；DeepLOB系开源未逐一核验 | 文献调研/raw/02 §1/§3/§4 |
| 14 | raw/03：微信/知乎原文受登录墙限制未逐篇fetch(全[二手-搜索摘要])；"清华"关联待核；shiyu-coder身份未检索到；TimesFM/Chronos中文报道量未系统检索 | 文献调研/raw/03（3行、62-70行） |
| 15 | 综述行动清单：修三处事实(AAAI状态/代码版本/权重hash)未完成；补经典文献页码；评估章节加两条硬约束(简单基准对照+FinVerse对齐)；X-10决策未变(定义问题非文献问题) | 文献调研/综述_辩证整理 §7/§10 |
| 16 | Kronos精读自认未读：Appendix.tex 141KB(仅读Implementation Details段)、迭代/下docx/xlsx正文、研究笔记0-10KB与20-43KB段；§4.1"交叉熵→L2重建"勘误待动手改 | Kronos论文逐章精读与项目结合.md（10-15行、165-170行）、理论先行_一页推导脚手架§3 |
| 17 | 学术准备：模块A-F精读清单全部是"背景之外、论文正文与实验节直接依赖的缺口"（未读）；Kronos Appendix 141KB尚未读(3-5月验收项) | 学术准备与阅读路线.md §0-§2、§5 |
| 18 | 会前一页纸：ρ(Δ)实测标定未完成(本地仅daily_hs300日线，缺分钟线与盘口)；kronos_zero_shot_baseline环境冒烟未跑；微观特征清单+数据来源(Wind/TAQ)未定稿 | 会前一页纸_最小可辩护核心.md §7（约72-76行） |
| 19 | 第一阶段执行：数据积累⚠️部分完成(仅1周K线+1天对齐；完整1周订单簿需连续168h后台采集)；K线(2024)与订单簿(2026)时间戳不匹配问题靠"下载匹配时间段"绕过 | 第一阶段_执行报告.md（约130行、180行）、第一阶段_交付清单.md §4.1 |
| 20 | sources.md自认未读：S-09立项信息表未读；S-14阶段一交付(文献报告初稿+数据手册)当时"未读正文"待核；S-27 KronosEnhanced含大量未验证数字(mae/sharpe硬编码、theorem3 verified:false 13/20违反) | research/sources.md（17行、22行、35行） |
| 21 | research/STATUS：跨模态项目级定理阻塞于X-10(项目组尚未定义高频pair schema/L_align/部署预测头)；外部文献新颖性核验离线未联网 | research/STATUS_draft.md（18-43行） |
| 22 | handoff审计#12：文献查询实际只做到本地工作区指定文件类型字符串检索，**未联网、未检索任何数据库**→所有"新颖性"状态=待核验，不得写"文献中不存在" | research/handoff/AUDIT_AND_OPEN_ISSUES.md（约26行） |
| 23 | 阻塞项X-04(三范式接入空间,阻塞TP2)、X-10(对齐定义,阻塞TP9/TP1)；X-06与X-09语义重叠未合并 | research/handoff/AUDIT_AND_OPEN_ISSUES.md §二、START_HERE.md §4 |
| 24 | 学习过程交接待办：ρ(Δ)真实数据标定曲线(当时只读模式做不了)、d=4-5严格推导(布朗桥极值)、T1/T2"仍未动工"(2026-09-07时点) | 理论先行_学习过程全记录与交接.md §9（约320-330行） |
| 25 | 可检验假设清单风险注记：假设1/2若两周后数据未通，只能表述"方法已设计、等待首个实验"；Moirai变长上下文/BSQ原文命题需动笔前核对原文不凭记忆 | 理论先行_可检验假设清单.md §4（约80-83行） |
| 26 | C-T9-001(被取代卡)遗留：分支B/C/D未分析；P₁一般性证明未完成(rate-distortion/information preference需核对原文)；§5.2 L_align与Y1冲突"仍为猜想且未分析"、检验未执行 | research/claims/C-T9-001.md §6/§7（约146-161行） |
| 27 | C-CM-001遗留：§4(加噪声重做三检验)待做；项目8项规格中7项未定义(S-03只写功能描述)；命题CM-1整体CONJECTURED(未加噪) | research/claims/C-CM-001.md §2/§4/§5 |
| 28 | 数据手册自认：《第二阶段_模型训练方案.md》"待编写"；新泄漏安全管线(hf_data_pipeline)未纳入手册v1.0 | docs/数据管线使用手册.md"下一步"（约440行） |
| 29 | 推导骨架§6残留：d可能随频率变化(唯一残留频率依赖)待标定；BSQ非最优量化器→量化噪声比是乐观下界 | 理论_推导骨架.md §6（约128-131行） |
| 30 | 理论先行_00：DependencyAwareLayer交叉注意力是否加因果掩码"克隆仓库后一条grep可定"(未定)；A股1min数据通道未定(Plan B=加密货) | 理论先行_00_上手路线与会议准备.md §3.1/§6（约75-125行） |

---

## 5. 重复/冗余候选（同一公式/定义在 3 个以上文件重复出现）

| # | 重复对象 | 出现位置（文件） | 冗余度与建议 |
|---|---|---|---|
| 1 | 模型D闭式 R=(ν+θ)/(2+ν−θ)、R_H=(ν+θ)/(1+ν)、ΔI=½ln((2+ν−θ)/(1+ν))（及统一族推广R=1−2u²/(2+ν−θ)） | claims/C-CM-002.md、claims/C-CM-003.md、claims/C-CM-004.md、research/scripts/crossmodal_covariance.py、research/scripts/unified_family.py、research/scripts/verify_theorem_card.py、research/handoff/MODEL_AND_RESULTS.md、research/reports/crossmodal_derivation_from_scratch.tex | 8个载体，闭式至少全文重复6处。建议：卡片保留陈述+指向单一"模型D规范文件"(MODEL_AND_RESULTS)，脚本注释删推导复述 |
| 2 | ρ(Δ)=σ²Δ/(σ²Δ+2ω²) + 2ω²噪声地板 + "1min约40%噪声" | 文献调研报告_初稿§1.2、理论_推导骨架§2-3、理论先行_学习过程§5、会前一页纸§2、第一阶段_执行报告§4.1、开会准备_Slide3/Q2、research/notation.md、research/assumptions.md、C-T12-001(Y1/Y2依据) | ≥9处。注意ω取值两处不一致(0.05%/0.1%)——冗余已造成口径漂移，建议统一引用推导骨架§3并标"待标定" |
| 3 | 512跨频跨度数字 2.05年/10.7天/2.13天（+10,240bit） | 理论先行_00、理论先行_可检验假设清单(假设4)、理论先行_学习过程§5、理论_推导骨架§7、理论先行_一页推导脚手架§1.5、会前材料_A§4/5、C-T12-001(Y1)、会前一页纸(隐含) | ≥7处，数字完全相同。建议收敛到推导骨架§7/脚手架§1.5两个规范处 |
| 4 | Kronos架构事实包（k=20、n=2子token、词表2^10=1024、λ=1、上下文512、BSQ、层次AR、12B K线/45交易所/7粒度、+93%/+87%/−9%/+22%、小/基/大=24.7M/102.3M/499.2M、5时间特征、PR#227） | Kronos论文逐章精读、交叉前沿§2.2、理论先行_一页推导脚手架§1、会前材料_A、research/notation.md§3、research/sources.md(S-10)、综述§7、初稿§3.1、理论_推导骨架A5 | ≥9处。数字高度一致(已交叉核验过)但"§4.1交叉熵→L2"勘误只在1处待改——冗余文件间同步风险，建议以精读笔记§7数字清单为单一事实源 |
| 5 | 10个微观结构特征清单（ofi/spread/mid_price/depth_imbalance/spread_vol/mid_vol/vol_concentration/slope/update_freq/large_order_ratio） | 初稿§5.1、docs/数据管线使用手册、第一阶段_文献调研与数据管线§4.1、第一阶段_交付清单§2.3、第一阶段_执行报告、开会准备_Slide7、会前准备_融合架构方案§2.3 | 7处同清单。注意：实际新管线aggregate_orderbook产出的是另一组列(event_ofi/spread_bps/book_slope/realized_mid_vol等)，与10特征清单并存两套特征定义，审计时须区分 |
| 6 | 5条融合设计原则（分离表征/降噪优先/低频条件化高频/分阶段训练/任务导向验证） | 初稿§4.2、第一阶段_执行报告§一.1、第一阶段_交付清单§1.3、开会准备_Slide4 | 4处同文本。建议保留初稿§4.2为规范出处 |
| 7 | 恒等式族 B=A+I、I-MMSE(dI/dr=mmse/2)、KL高斯闭式(½)[s²/t²+μ²/t²−1−ln(s²/t²)]、B的严格二次闭式 | claims/C-T9-002(定理1/3)、claims/C-T9-001、claims/C-CM-004§2、scripts/audit_t9.py、scripts/regress_and_crossmodal.py、scripts/verify_t9_threshold.py、handoff/MODEL_AND_RESULTS.md | ≥7处。三张T9/CM卡+三个脚本各自复述证明，建议证明只存卡+脚本留"复算"不存"证明" |
| 8 | tokenizer三项损失+L_ar分层NLL+采样粗码(非teacher forcing)+时间嵌入5特征 | 一页推导脚手架§1.2-1.3、会前材料_A§2-3/5、Kronos精读§4、理论先行_00§3.1(追问点)、初稿§3.1 | ≥5处同公式。与#4同源，合并收敛 |
| 9 | Var(r_Δ)=σ²Δ+2ω²（引理1）单条公式 | 初稿§1.2、推导骨架§2、学习过程§5(引理1)、执行报告§4.1、会前一页纸§2(展开式) | 5处。与#2同批收敛 |
| 10 | "方向不可学、分布可学⇒主打风险/波动率"战略结论+回测扣2×半价差 | 学习过程§8、会前一页纸§4、理论先行_00§4(陈述骨架)、综述§8(三板斧3) | 4处同论述。会前材料是面向会议的展开版，属有意的重复，可保留但标注同源 |

---

*盘点完。本轮未修改任何既有文件；唯一新增文件即本 inventory。*
