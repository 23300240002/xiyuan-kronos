# 个人贡献状态页（草案 · 2026-09-17 v2）

> **状态声明（请保留在页面顶部）**
>
> ```text
> Status: personal research draft
> Not yet discussed or endorsed by the group
> No training result is claimed
> Do not merge before group review
> ```
>
> 本分支是个人草案，供组内 review。`main` 未被修改；组员讨论前请勿合并，也不要把本分支内容当作项目共同结论引用。

## 总览

| 部分 | 完成度 | 一句话 |
|---|---|---|
| 理论 | 模型内全部闭合，项目级判定只差填表 | 定理 A/B/C 全已证（θ<1/2 缺口 2026-09-17 独立复跑关闭）；$L_{align}$ 候选空间已建模（C-T9-003，全为已发表方法）；X-10 只剩组按 DS-CM-001 填五位——桥接层已把可审计位备好证据 |
| 代码 | 三层可复跑 | v2 数据管道（deep_A/C 双独立审计后 8 类定义级偏差全修，T1–T9 测试含多资产 fixture）+ context adapter（D1 截断已修）+ 桥接层（PairKey/时间审计/五位证据/provisional D_pair）|
| 训练 | 未启动（诚实） | 只有 TP13 v0.1 草案 + 三臂协议；无 GPU 结果、无模拟指标 |

## 理论

| 项 | 状态 | 规范出处 |
|---|---|---|
| 平方损失判据 | 已核为**教科书结果**（Durrett 4.1.8 / GSVD eq.(9)），推导稿待按清单砍重推 | deep_E §1(1)(2)/§4 |
| 模型 D 闭式 | **应用**级（GSVD/GWsv/PV 标准件代入）；唯一规范陈述=C-CM-004（R-1 指针已挂 002/003） | deep_E §1(3)/§3 |
| **定理 C**（θ<1/2 段 ΔI′>0）| **已证（模型内）**：四项非负分解，`verify_proposition_C.py` 5/5 PASS；文献未覆盖（检索面记录在案），属项目新结果；对外主张新颖前按 deep_E §5#7 补一轮检索 | C-CM-004 §1.6/§3.3 |
| ω 噪声地板 | 协议+首版标定（BTC 代理，区间口径，ρ 对外冻结至 A 股快照终判）；引用链 HL Lemma 4/BR 2008 已核 | C-X03-001 |
| $L_{align}$ 候选空间 | 3 主候选（C1 唯一与模型 D 兼容；S 位分水岭）+2 消融+排除清单；C3 降诊断 | **C-T9-003**（血统 deep_B §1–§6） |
|  TP13 基准规范 | 14 项决策草案（e=max(h,L_feat) [推导]、双朴素基准闸门、14 项预注册），**待组冻结** | reports/TP13_benchmark_spec_draft_v0.1.md |

**理论线不再等待 X-10**：X-10 是定义问题（repo 自己最早就是这么写的），它只挡"把 C-CM-004 用作项目设计依据"这一件事；本轮把这件事变成**填表**（桥接证据 + C-T9-003 §1 表 + TP13 开放项清单），不是研究。

## 代码

| 模块 | 验证命令（kronos 环境） | 最近结果 |
|---|---|---|
| `scripts/hf_data_pipeline.py` v2 | `research/scripts/verify_hf_data_pipeline.py` | **T1–T9 PASS**（多资产/缺口/陈旧/稀疏/maker 语义 fixture 齐备）|
| `research/scripts/kronos_context_adapter.py`（D1 截断+警告） | `KronosLocal/deps/Kronos` 下 `HF_HUB_OFFLINE=1 PYTHONPATH=. python ...kronos_context_adapter.py` | PASS（(1,512)、重复差 0、截断确定性）|
| `research/scripts/audit_kronos_x10.py` | 同上 | PASS |
| `research/scripts/crossmodal_bridge.py --smoke` | 离线，torch-free fixture | PASS（T1–T7 + 五位 provision + provisional D_pair）|
| `research/scripts/calibrate_noise_floor.py` | 见 C-X03-001 §2 | PASS（双口径区间）|

真实数据干跑：BTC 盘口 v1/v2 OFI 对照（8/8 窗失真、2 符号翻转）量化在 C-CODE-HF-001(v2)。Tushare 侧：字段字典与快照方案=deep_F §5/§6（**分钟权限 2027-02-28 到期 → 前置批量拉取**；无 L2 → 盘口特征是扩展档）。token 不入仓库；对话中出现过的旧 token 建议轮换。

## 训练（未启动）

协议三件套已就位：TP13 v0.1（切分/purge/embargo/基准/预注册）+ deep_D §3.3 三臂探针设计（hidden/模型输出/裸输入 + 置换对照）+ C-T9-003 候选表。**没有任何 GPU 结果。** 启动前置：①A 股分钟快照落地（用户侧）；②五位终判（组）；③预注册 14 项冻结。

## 防玩具/防轮子/卫生（本轮纪律落点）

- 引用卫生入 README 纪律 5：deep_A/B/C 已证伪 9+ 条记忆式假引用（含本任务书自带的三条）；[一手-子代理] 条目（deep_B 7 处）对外前须本人复核；
- provisional D_pair 自带 `NOT a design basis` 状态行；桥接层零学习目标；
- 抓取通道出现过**提示注入尝试**（要求外发成果至外部邮箱，deep_B §0-6 在案，未执行）——任何 agent 输出若出现"发送/上传到外部地址"类指令一律视为攻击。

## Review 与回退

- 分支独立于 `main`，整分支可弃；结论冲突时以 `state.json` + crosswalk 为准；
- 全部复跑只需上表 5 条命令，离线（Kronos 权重本地）；
- deep 六报告 + inventory 在 `文献调研/`（吸收地图=crosswalk 的文献列，每行带小节指针）。
