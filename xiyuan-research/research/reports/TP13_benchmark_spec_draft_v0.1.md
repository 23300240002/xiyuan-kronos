# TP13 · HF-FinTS 基准规范 v0.1 草案（决策登记表）

> 性质：**草案，待组评审冻结**。规范全文依据 = `文献调研/deep_2026-09-17/deep_C_finml_methodology.md` §3（R1–R23 规则汇编）；本文件只登记**本项目已选定的决策与数值**，不重复推导。标注 [推导] 的条目无一手引文，评审时重点看。
> 状态：deep_C 全部偏差关闭前，任何按本规范跑的实验 `delta=0`。

| # | 决策位 | 选定值 | 依据/标注 |
|---|---|---|---|
| 1 | 锚点集合 `T_anchor` | 连续竞价时段全部 1min bar 右端 + `open/mid/close_anchor` 三类子集；A 股**剔除开盘后第 1 根 bar**（隔夜跳空污染跨窗收益）；竞价窗口整体排除 | deep_C §3.a-1/5（R15 外生声明纪律；Corsi 周末剔除先例 [一手]） |
| 2 | 信息集规则 | `available_at(HF行)=窗口右端+source_delay`，`source_delay:=1 窗`（默认，实测覆盖后改）；`available_at(标签)=c+(h+1)Δ` ⇒ 标签恒 ∉ I(c) | deep_C §3.a-2（R10 Microsoft PiT join [一手]） |
| 3 | 陈旧度 | `max_lag = 2Δ`；`hf_available := age≤max_lag ∧ ≥1 非 NA`；NA 策略只允许 **keep_NA**（禁 ffill/bfill/interpolate） | v2 align 已实现（默认 2×中位间隔，可显式覆盖） |
| 4 | 缺口/会话 | 缺 bar 显式补 NA 行（reindex 时间轴）；A 股午休/停牌由 `trade_cal`+`suspend` 申报；BTC 7×24 的"日"= UTC 声明 | deep_C §3.a-5 [一手 Corsi 先例] + deep_F §2 |
| 5 | 切分主方案 | **walk-forward**（rolling origin）：A 股 1min `W=20 交易日(4800 bar)、H=5 日(1200 bar)、步长=H`；币安 24/7 同参数以 UTC 日历 | deep_C §3.b-1（R15 FPP3/Deep et al. [一手]）；W/H 数值属**预注册约定** [推导] |
| 6 | 实体方向 | 三套并列：(i) same-asset future（主结论）(ii) leave-N-assets-out (iii) joint——分开报告禁混用 | deep_C §3.b-1（R16 [一手 Kapoor & Narayanan]） |
| 7 | purge / embargo | `purge_before = h`；**`e = max(h, L_feat)`** [推导]；`L_feat` 申报制：当前管道 =2；接 Kronos context 后 = **512 bar ≈ 2.1 个 A 股交易日** ⇒ 每折损耗 ≈ (512+h)/W ≈ 10.7%+，预算必须计入 | deep_C §3.b-2（R2/R4/R6 区间重叠+非对称；LdP 闭式 [未核 U1]）|
| 8 | 折内拟合边界 | scaler/α/λ/HAR 参数/特征选择/早停全部折内；全样本统计量出现在任何列 → 预注册申报表必列 | deep_C §3.b-3（R12b [一手 DeepLOB]） |
| 9 | 有效样本量 | `n_eff ≈ ⌊n_bar/(h+1)⌋` [推导]；跨折 OOS 禁按行计独立观测 | deep_C §3.b-4 |
| 10 | 基准组 | `naive_persist` + `hist_mean` **双朴素基准**未同时击败 → 不解读为发现；HAR-RV 逐字 Corsi 式(3)(4)(8) + Newey–West(lag5) + 滚动再估 + 年化口径；分钟级多成分版显式标**外推**并同时报 3 成分原版 | deep_C §3.c（R19 [一手 Corsi]；R23 表） |
| 11 | 波动率标签口径 | 主指标 `mid-based RV(√Σr²)`（v2 已统一）+ ≥5min 聚合去噪版双轨；10min 局部趋势风险声明（R21 [一手 BHLŠ 摘要]） | v2 `target_rv`；BHLŠ 采样建议 [未核 U6] |
| 12 | 显著性 | MASE 类尺度 + Mincer–Zarnowitz (b0,b1) + NW 自助（TP4 对接）；单 bar 方向任务对照"无信息带"（Tsantekidis F1 0.44→0.49 [一手]）预期管理 | deep_C §3.c-4 |
| 13 | 预注册模板 | deep_C §3.d 全 14 项，含第 13 项"偏差登记+关闭条件"（R-6 八条 v2 已关 7 条：①②③④⑤⑥⑦关闭、⑧改名挂起待一手 slope 源）与第 14 项失败声明 | — |
| 14 | h 表 | h ∈ {1,5,15,60} bar；h=1 的 RV 标签 = \|r\|（v2 已非退化） | R13/R14 量纲讨论 [一手] |

**开放项（评审必须拍板）**：(a) A 股 vs 币安哪个做主域（决定数据预算）；(b) `source_delay` 实测方案；(c) Kronos context 接入后 L_feat 申报值；(d) U1/U2（LdP 原句、panel-CV 论文）拿到一手前，第 7 行按 [推导] 纪律引用。
