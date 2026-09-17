# 理论研究任务板

> 更新时间：2026-09-17。状态以 `state.json` 为机器可读主记录；本表用于人工检查依赖和下一步。文献回填见 `crosswalk_theory_code.md`。

| 任务 | 状态 | 当前可靠产出 | 下一最小动作 |
|---|---|---|---|
| TP1 跨频联合表征 | UNSCOPED | C-CM-001 判据 + deep_B 候选空间可映射 | 与 X-10 共用 PairKey 结构（桥接已给出契约，组填值）后定义信息集 |
| TP2 三范式比较 | BLOCKED | 三范式定义已定位 | 明确 Diffusion/Flow 接入 token 还是连续潜空间（X-04） |
| TP3 因果识别 | UNSCOPED | 无 | 等项目定义处理、结果和 estimand |
| TP4 显著性与功效 | UNSCOPED | deep_C 给了 n_eff/MASE/NW 框架 | 在 TP13 冻结后预注册检验 |
| TP5 融合有效性 | UNSCOPED | 理想 Bayes 风险判据可复用 | 定义样本外风险（挂 TP13）与成本后效用基线 |
| TP6 交易成本 | UNSCOPED | 无 | 等执行规则与持有周期 |
| TP7 Scaling Law | UNSCOPED | 无 | 定义损失、规模和有效样本量 |
| TP8 因果落地 | UNSCOPED | 无 | 依赖 TP3 |
| TP9 L_align | PARTIAL↑ | C-T9-002 高斯子问题；C-CM-004（定理 A/B/C 全已证）；C-X10-001 接口审计+adapter（D1 已修）；**C-T9-003 候选空间（3 主+2 消融）**；桥接 v0.1（PairKey/T1–T7/五位证据） | 组按 DS-CM-001 在 {C1|C2} 拍板五位（S 位=分水岭）；r、尺度锚、D_hat 定义进预注册 |
| TP10 预处理/正则化 | UNSCOPED | 无 | 仍可用 3sigma/时序 Dropout 做最小反例（不依赖 X-10） |
| TP11 冻结与遗忘 | UNSCOPED | 无 | 先核实实际可训练模块 |
| TP12 范式转换 | CONJECTURED | C-T12-002 命题 1–3 内部复核 | 把 tokenizer 保真度命题映射为真实可执行实验 |
| TP13 HF-FinTS 基准 | **DRAFTED**（待组冻结） | `reports/TP13_benchmark_spec_draft_v0.1.md`（14 项决策登记；deep_C R1–R23 依据表） | 组评审 4 个开放项（主域/source_delay/L_feat 申报/U1 类引用回填） |
| TP14 论文理论章节 | UNSCOPED | 素材变薄是好事：deep_E §4 砍/留/改清单可压掉推导稿 ~45% 教科书重推 | TP1/TP13 有实料后启动 |

## 当前主任务（2026-09-17 改写）

**X-10 不再占据"主任务"位置**：它是定义问题，理论侧可做的已做完（定理 C 关闭、候选空间建模、桥接证据机器就绪）。当前推进序列：

1. **数据快照**（用户侧）：Tushare 分钟线前置批量拉取（权限 2027-02-28 到期；deep_F §6 方案）→ ω/ρ 终判（C-X03-001 §5）→ 特征族 A 股复验；
2. **组内拍板**：TP13 冻结 + 五位终判（桥接报告可作 §2 证据栏粘贴件）；
3. 其后才是 δ=0 三臂实验（低频 / 双路无对齐 / 共享投影对齐，deep_D §3.3 标准设计）——训练线，非本板主线。

## 当前可靠增量（截至本轮）

C-X10-001 真实接口审计 + adapter（含 D1 截断修复）；**定理 C**（θ<1/2 段四项分解解析证明，`verify_proposition_C.py` 独立 5/5 PASS）；**C-X03-001** ω 首版标定（A 侧倾向、区间口径、引用链已核）；**hf_data_pipeline v2**（8 类定义级偏差全修、T1–T9 多资产 fixture、真实盘口对照量化）；**C-T9-003** 候选空间；**TP13 v0.1** 草案；`crossmodal_bridge` v0.1；deep_A–F 六报告 + inventory（吸收地图 = crosswalk）。
