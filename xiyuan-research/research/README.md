# research/ · 理论与有效性研究底座

> 建立 2026-09-10，2026-09-17 结构重整。**新接手从这里读**：
> 1. `STATUS_draft.md` —— 完成度声明（理论/代码/训练各到哪、边界、复跑命令）；
> 2. `task_board.md` —— TP1–TP14 状态与下一步；
> 3. `state.json` —— 机器可读主记录（阻塞项/增量/失效登记）；
> 4. `crosswalk_theory_code.md` —— **理论×代码×一手文献对照表**（每条理论的代码契约、每个代码的文献归属、R 冗余清单）；
> 5. `claims/C-CM-004.md`（模型 D 规范陈述）与 `claims/` 其余卡——按卡内"出处→假设→可推翻条件"读。

## 目录内导航

| 路径 | 作用 |
|---|---|
| `claims/` | 结果卡。**规范位**：C-CM-004（模型 D + 定理 A/B/C）、C-T9-002（对齐损失高斯子问题，SEALED）、C-T9-003（L_align 候选空间）、C-CODE-HF-001（数据层 v2）、C-X10-001（Kronos 接口）、C-X03-001（噪声地板标定）；历史/审计卡：C-CM-001/002/003、C-T12-001/002 |
| `reports/` | 决策与规格：DS-CM-001（五位路由表）、NEXT_TASK_X10、TP13_benchmark_spec_draft_v0.1、两份 tex（组会稿+从零推导稿，**推导稿待按 deep_E §4 砍重推**）|
| `scripts/` | 验证机（全部确定性离线）：verify_hf_data_pipeline（T1–T9）、verify_proposition_C、verify_theorem_card、verify_t9_*、verify_t12_feature_bound、verify_y3_identity、audit_t9、audit_kronos_x10、kronos_context_adapter（需 `KRONOS_DIR`）、crossmodal_bridge、calibrate_noise_floor |
| `notation.md` `assumptions.md` `dependency_graph.md` `sources.md` | 符号/假设/依赖/来源四表 |
| `state.json` `task_board.md` `STATUS_draft.md` `crosswalk_theory_code.md` | 状态四件套 |

**纪律**：任何进入本目录的结论必须回答「出处 → 假设 → 可推翻条件」三问；`SEALED/PHASE_CLOSED` 只表示本轮不再扩展，不表示已验证；对外引用只走 `../文献调研/deep_2026-09-17/` 的 [一手] 通道（该批调研已证伪 9+ 条记忆式假引用，"三锚点"式术语入库前必须先全目录检索）。

> 2026-09-10 版 `handoff/` 七件套已被上面的"接手五读"取代，仅存于个人仓库历史分支。
> 可信度标签 [一手]/[二手]/[待核]/[新造] 全仓库通用，含义见根 README。
