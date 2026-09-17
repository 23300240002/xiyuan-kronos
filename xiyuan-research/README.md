# ⚠️ 个人研究草案 · 待组内 review

```text
Status: personal research draft (theory cards + v2 data pipeline + evidence machine)
Not yet discussed or endorsed by the group
No training result is claimed
Do not merge before group review
```

本目录整体新增，未触碰上游任何文件（`model/`、`finetune/`、`examples/` 等原样）；基线上游 commit `67b630e`。内容已去除个人身份与本机绝对路径（脚本用 `__file__` 相对定位 / `KRONOS_DIR` 环境变量）。评审请从 `research/STATUS_draft.md` 与 `research/crosswalk_theory_code.md` 入手；不采纳则整分支可删，零残留。

---

# 曦园项目 · 课题 — 基于 Kronos 的跨源研究（理论线 + 数据代码线）

> **一句话定位**：高频单独建模存在可量化的信息天花板（噪声地板 ρ(Δ)）；因此引入微观结构特征 + 跨源融合（Kronos 低频 context ↔ 高频特征），并把主目标定为**风险/波动率预测**而非收益方向。
>
> 基座：[Kronos](https://github.com/shiyu-coder/Kronos)（AAAI-2026 接收；本地代码锚 commit `67b630e`）。本仓库是其**研究层**工作。

## 结构（main = 核心内容）

| 路径 | 内容 |
|---|---|
| `research/README.md` | 理论底座入口（接手先读）|
| `research/claims/` | 结果卡：**C-CM-004（模型 D 规范，定理 A/B/C 全已证）**、C-CM-001、C-T9-002/003、C-T12-001/002、C-X10-001、C-X03-001、C-CODE-HF-001(v2) |
| `research/state.json` + `task_board.md` + `crosswalk_theory_code.md` | 机器状态 / 任务板 / **理论×代码×文献对照表（吸收地图）** |
| `research/STATUS_draft.md` | 完成度声明页（理论/代码/训练各到哪，四行草案横幅）|
| `research/reports/` | DS-CM-001 五位决策路由、NEXT_TASK_X10、TP13_benchmark_spec_draft_v0.1、两份 tex 报告 |
| `scripts/hf_data_pipeline.py` | **v2 无前视数据管道**（deep_A/C 审计修复版；退役件不在 main）|
| `research/scripts/` | 验证机：verify_* ×4、audit_kronos_x10、kronos_context_adapter、crossmodal_bridge、calibrate_noise_floor |
| `data/binance/` | 测试样本（盘口+K线；v1 特征产物已作废移除）|
| `文献调研/deep_2026-09-17/` | 六份 deep 报告（一切对外引用的 [一手] 通道）+ `inventory_2026-09-17.md` |

**分支地图**：`main`=核心；个人仓库另设全量备份分支（不在此公开）。本分支即共同仓库评审分支：`research/theory-code-draft`。

## 快速验证（conda env `kronos`；`KRONOS_DIR`=KronosLocal 检出根，无默认值）

```bash
python research/scripts/verify_hf_data_pipeline.py   # T1–T9 数据层
python research/scripts/verify_proposition_C.py      # 定理 C 独立复跑
python research/scripts/crossmodal_bridge.py         # 桥接冒烟
python research/scripts/calibrate_noise_floor.py data/binance/kline/BTC_USDT_1m_2024.parquet
# adapter/audit（需本地权重）：cd "$KRONOS_DIR/deps/Kronos" && HF_HUB_OFFLINE=1 PYTHONPATH=. python <script>
```

## 可信度标签体系（全仓库通用）

**[一手]**（论文原文/官方代码/数据产物，可作事实依据）· **[二手]**（历史会话产物，只作线索）· **[待核]** · **[新造]**（必须显式标注）。claims 卡另有 `INTERNALLY_CHECKED / CONJECTURED / SEALED` 与"不能据此声称"清单。

## 纪律

1. 进入 `research/` 的结论必须回答「出处 → 假设 → 可推翻条件」三问；
2. SEALED/PHASE_CLOSED ≠ 已验证，只表示本轮不再扩展；
3. Kronos 基线数字注明代码版本（`67b630e`；#227 为 issue 非 PR，细节见状态页）+ 权重 hash；
4. 历史会话术语入库前先全目录检索；
5. **引用卫生**：对外引用只走 `文献调研/deep_2026-09-17/*` 的 [一手] 通道——该批调研已证伪 9+ 条记忆式假引用（含"OFI Joss 公式"一类假定理名）；
6. 仓库内不得出现个人绝对路径/身份信息（脚本一律 `__file__` 相对或环境变量；曾入仓的以 `chore(portability)` 清除）。

## 当前开放项

- **X-10 五位终判**（组按 DS-CM-001 填 P/A/H/B/S；桥接层已备好数据层证据，`C-T9-003` 给候选空间）——是定义问题，不再阻塞理论；
- **A 股分钟快照**（用户侧，Tushare 权限 2027-02-28 到期前前置拉全）→ ω 终判 + 特征 A 股复验；**盘口/L2 无 Tushare 供给**，源待定；
- 之后才是训练线（δ=0 三臂实验）。

> 本仓库含项目一手资产，公开前需走项目方发表规则。维护：理论+数据代码线，最近更新 2026-09-17。
