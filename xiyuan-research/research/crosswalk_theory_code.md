# 理论 × 代码对照表（crosswalk · 2026-09-17）

> 本表是"理论支持代码、代码实现理论"的机械联结点，规则：
> 1. **每条理论行必须填"代码契约"**——该结果对某个模块施加的可检查约束；填不出 → 该理论按冗余处理（砍成引用或降级）。
> 2. **每个代码函数必须能在本表找到归属**——实现 [标准/卡号] 或标注 [纯工程]；找不到归属的函数 = 孤儿代码候选（处理见 R-3）。
> 3. 文献标准列只接受 deep 报告 [一手] 通道回填的引用；未回填的行不得对外声称"标准一致"。
>
> 状态图例：✅ 已实现且已验证 · 🟡 部分实现 · ❌ 缺失 · 📦 已声明退役

## 1. 对照表

| # | 理论对象 | 卡/文档 | 代码实现 | 状态 | 代码契约（理论对代码的约束） | 文献标准 |
|---|---|---|---|---|---|---|
| T-1 | 平方损失理想风险判据 | C-CM-001 | `verify_theorem_card.py`（复算）| ✅ | 融合有效性验收只用平方风险族指标；多目标需先按 DS-CM-001 S 位改口径 | E 判定=**砍**（教科书定理：Durrett 2019 §4.1 Thm 4.1.8 + GSVD 2005 eq.(9)）；推导稿第 2/4 层改引用（deep_E §4） |
| T-2 | 模型 D 四闭式 (κ,θ,ν) | C-CM-002/003/004 | `crossmodal_covariance.py`、`unified_family.py`、`verify_theorem_card.py` | ✅ 三份复算 | 报告 ΔI/R_H/R 前必须过 P/A/H/B/S 判据；κ 记号禁与 ν 混代（已有作废先例）| E 判定=**应用**（GSVD 2005 eq.(11)-(13)、GWsv 2010 Prop 1–3、PV 2006；保留 6 行代入+勘误红线）；**定理 C 为项目新结果（deep_E §1(4)+§2；文献未覆盖，正式主张新颖前按 §5#7 补检索）**；R-1 收敛仍执行 |
| T-3 | ρ(Δ) 噪声地板与 ω | 推导骨架 §2-4 + **C-X03-001** | `calibrate_noise_floor.py`（签名图，WLS+OLS，双 PASS）| ✅ 首版（终判待 A 股快照）| ① ρ 数值冻结至 Tushare 终判；② Tushare 1min 字段须可声明 bar_start/bar_end（deep_F：实际为 bar_end）；③ K 线 close 只给"有效噪声"口径 | Hansen–Lunde 2006 Lemma 4 + Bandi–Russell 2008 ReStud + ABDL 2000 命名 + Fang/Zhou 优先权；Lo–MacKinlay 仅诊断（deep_E §3b）|
| T-4 | 真实 Kronos context 接口 | C-X10-001 | `kronos_context_adapter.py`、`audit_kronos_x10.py` | ✅ | ① context 是 **pre-generation**（论文须声明）；② 窗口 >512 token 分布外——adapter 加截断/断言（D1，待修）；③ 对照臂用官方 predict 输出时先 `.eval()`（token_dropout=0.1 已本地核实）| deep_D §1/§5（README/issues #227/#297/#307/#355 一手）；空白性=检索范围内无先例 |
| T-5 | L_align 候选空间（分支 C"最关心仍空白"）| **C-T9-003 已建**（3 主候选+2 消融，全带 [一手] 血统）| `crossmodal_bridge.py` 消费其可判条件 | ✅ 空间建模完成；实验待五位终判 | 候选全为已发表方法（禁玩具）；**S 位=分水岭**：C1 向量残差→F-S；C2 标量→`D_hat` 须重定义 | deep_B §2/§4/§6（Donnat–Tuzhilina、Wang–Isola、KD/IRM/CDAN、Bykhovskaya–Gorin、Lopez-Paz 等）|
| T-6 | DS-CM-001 五位判据 | DS-CM-001 + C-T9-003 §3 | `crossmodal_bridge.py`（PairKey 契约+T1–T7 审计+五位证据+provisional D_pair），--smoke PASS | ✅ v0.1 | 桥输出即填表证据：P/A/B/S 数据层 provisional、H 如实"?"；PairKey=pair schema 的结构契约（组只填值）| deep_C R8–R11 [一手]（Databricks/Hopsworks/MSFT/Flink）；deep_A R7（等值 join 优先）|
| T-7 | 特征信息增量机制 | C-T12-001/002 | `verify_t12_feature_bound.py` ✅、`verify_y3_identity.py` ✅ | ✅ 理论+核验；Y2 实证未做 | 特征筛选按增量上界；堆特征进 tokenizer 前须过比特预算检查 | 条件 DPI=教科书工具；I–MMSE 出处已一手核（deep_E §1(A)）；DPI 的 CT2 编号 [待核 §5#1] |
| T-8 | 对齐损失高斯子问题 | C-T9-002（SEALED）| `audit_t9.py`、`verify_t9_threshold.py`、`regress_and_crossmodal.py` | ✅ 封存 | B（纯对齐）必坍塌 → 任何实现不得把纯对齐损失当可用目标；A 有阈值 σ=τ 判据 | 小 SNR 系数 = GSVD 2005 Lemma 1(29)+eq.(86) 代入 [一手]；B=A+I = KL 链式法则（编号 [待核 §5#3]）|
| T-9 | TP13 HF-FinTS 基准规范 | **TP13_benchmark_spec_draft_v0.1.md**（14 项决策登记表，待组冻结）| 被规范约束的对象 = align/make_future_labels（v2 已实现 max_lag/keep_NA/contiguity 部分）| 🟡 草案 | `e=max(h,L_feat)` [推导]；双朴素基准未同胜不解读；`n_eff=⌊n/(h+1)⌋` | deep_C §1/§3 全表（R1–R23；U1–U8 如实挂起；Corsi/DeepLOB/FPP3/Kapoor 等多处 [一手]）|
| T-10 | 无前视数据层 | C-CODE-HF-001（**v2**） | `scripts/hf_data_pipeline.py`（8 函数）+ `verify_hf_data_pipeline.py`（T1–T9） | ✅ v2（修复层 2026-09-17 落地，真实数据干跑在案） | 卡片"不能据此声称"清单即代码测试边界；Tushare 适配只走 `normalise_kline` 声明式接口 | deep_A §1/§2（CKS §2.1 逐字、S6 VOLARE §4.4/§5.1.4、S7 VWAP/imbalance、S8 Binance `m` 语义）；deep_C §2 |

## 2. 冗余与孤儿处置（R 清单）

| ID | 对象 | 处置 | 依据 |
|---|---|---|---|
| R-1 | 模型 D 闭式散布 8 个载体（3 卡+3 脚本+handoff+tex）| **执行中**：C-CM-004 为唯一规范陈述（含定理 A/B/C 与红线），C-CM-002/003 顶部加"规范陈述见 C-CM-004"指针（历史内容不删=审计对象）；脚本只留复算不留证明复述 | inventory §5-1；deep_E §4 砍/留/改清单 |
| R-2 | ρ(Δ) 表述散布 ≥9 处、ω 曾口径漂移一倍 | 统一引用推导骨架 §3 + C-X03-001；数字冻结条款以卡为准 | inventory §5-2、§4-2 |
| R-3 | 旧管线（`extract_features.py` 10 特征、`align_data.py` ffill/bfill、`run_pipeline.py`）与新管线并存两套特征定义 | 脚本头加 📦 退役声明；数据手册 v1.1 只收录 `hf_data_pipeline` v2 一套列定义 | C-CODE-HF-001"有效排除"、inventory §3.5 |
| R-4 | "PR #227"表述（实为 issue #227；泄漏在 finetune 路径，推理路径本 lookback-only；本地 finetune_csv 未含 #263）| **已执行**：README 纪律 3 与综述 §7/§10 已更正；基线数字钉 `67b630e` + 权重 hash（hash 计算列入数据快照步骤）| deep_D §1.2/§5 |
| R-5 | 依赖 ρ 数值的对外结论（H1、幂律下界数字等）| 维持冻结至 A 股快照终判（notation.md 已登记）| C-X03-001 §4 |
| R-6 | hf_data_pipeline v1 的 8 类定义级偏差 | **已关闭（2026-09-17）**：v2 全修+9/9 测试+真实数据对照（OFI 8/8 窗失真、2 符号翻转量化在案）；⑧ book_slope 一手公式源挂起待实现 | deep_A §2/§4、deep_C §2、C-CODE-HF-001 v2 |
| R-7 | 引用卫生：假 arXiv ID/定理名（deep_A §5 三条+deep_B U8/U9 四条+「Joss」+deep_C U2/U3/U5）| **已执行**：README 纪律 5 立规；综述 Joss/PR#227 已更正；被证伪条目从一切对外引用位剔除；[一手-子代理] 条目（deep_B 7 处）对外前须本人复核 | deep_A §5、deep_B §5、deep_C §4 |

## 3. 防玩具/防轮子三闸

1. **L_align 候选必须带发表出处**（deep_B 硬性要求），无出处目标不进卡；
2. **方法学一律取文献既有标准**：标定=签名图（推论 1.1 + HL Lemma 4）、实验设计=三臂探针+置换对照（deep_D §3.3）、CV=purged/embargo 框架（deep_C）、OFI=CKS 定义（deep_A）、PiT=工程标准四件套（deep_C R8–R11）；
3. **桥接层只产证据不产新目标**：PairKey/T1–T7/五位 provision 全部是"验证已定义对象"的代码；provisional D_pair 自带 `NOT a design basis` 状态行。

*本表由 deep 报告回填；每行引用必须给报告内小节指针，禁止只写"文献支持"。*
