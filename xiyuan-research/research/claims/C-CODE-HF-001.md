# C-CODE-HF-001 · 高频数据层的无前视清洗与对齐（v2）

| 字段 | 内容 |
|---|---|
| 结果类型 | [代码实现] + [定义澄清] + [有效排除] |
| 验证状态 | INTERNALLY_CHECKED；v2 确定性离线测试 9 组全 PASS + 真实 BTC 数据干跑；未接 Tushare、未训练模型 |
| 一句话结论 | v1 数据层经 deep_A/deep_C 双独立审计发现 8 类定义级偏差（最严重者在真实盘口上使 **全部 8 个可测窗口的 OFI 失真、2 窗符号翻转**），v2 已逐项修复并以 CKS 2014 窗口求和、RV 口径、有界陈旧度与必填语义参数重建契约。 |

## v1 → v2 变更（破坏性，依据 deep_A §2/§4、deep_C §2，双独立实测吻合）

| # | v1 问题 | v2 行为 |
|---|---|---|
| 1 | `aggregate_orderbook` 每窗 `iloc[1:]` 丢第一条有效事件，违反 CKS 2014（arXiv:1011.6402 §2.1）$OFI_k=\sum e_n$；真实 BTC 盘口 8/8 窗失真、2 窗符号翻转、max Δ=11.4 | 全窗求和，仅排除全局首条与缺口后首条（`ofi_valid=False`→NaN），新增 `ofi_contributing` 计数 |
| 2 | 空/稀疏窗输出 `0.0`（真实数据 15:00 窗 mid_return=RV=0 实锤）；缺窗整行消失 | **全 bin 网格**：空格子保留行、特征 NaN；`min_snapshots` 默认 4（文献门槛精神，可调） |
| 3 | `mid_return` 用窗内首尾差，与 RV 的跨窗对收益边界处理互相矛盾 | bar 口径链：本窗末 mid ÷ 上一窗末 mid；RV 改 previous-tick 等间隔子网格（默认 5s，`rv`+`rv_sqrt` 两列，≥4 点否则 NaN） |
| 4 | `align_features_to_kline` 多资产 100% 抛 `left keys must be sorted`；`tolerance=None` 允许任意陈旧特征冒充当期 | 全局排序 + per-asset merge；默认陈旧上限 = 2× 中位特征间隔（可显式覆盖）；输出 `feature_age_ms`/`n_features_present`；多资产缺 `asset_id` 直接报错 |
| 5 | `clean_trades` 无方向语义参数——Binance `m` 字段是 *buyer-is-market-maker*，与 aggressor **反号**，误用会整列静默反号 | 必填 `side_semantics ∈ {aggressor, maker, absent}`，maker 自动翻号，absent 不产 signed 列；imbalance 分母改**已判定量**，新增 `classified_volume_share` |
| 6 | `make_future_labels` 默认 `horizon=1` 时 `target_realized_vol` 恒 0（ddof=0 单元退化）；std 口径与特征端 RV 差 √h+去均值；`shift(-h)` 遇缺 bar 静默拉长标签窗（deep_C 实测跨 2 分钟） | `horizon` 必填；标签统一 RV 口径 `Σr²`（h=1 = \|r\|，非零）；时间网格校验：端点不精确等于 t+hΔ 则 NaN，`label_ok_contiguity` 标记窗内连续性 |
| 7 | `clean_orderbook` 要求 5 层全 >0：vendor 空层 0 填充会**整行误删**（潜在全库毁灭，本样本未触发）；locked 与 crossed 混计 | 按行截断深度（0 填充层=缺失非脏数据）；`dropped_locked`/`dropped_crossed` 分列计数；可选 `max_gap` 打 `gap_flag` 联动 OFI |
| 8 | `assume_tz` 各函数默认值不一致（kline=Asia/Shanghai，其余=UTC）——漏传即 8 小时静默错位；`book_slope` 名不副实（纯价格跨度、零深度信息）；`snapshot_rate` 与 count 完全共线；死列 `log_mid` | `assume_tz`、`timestamp_semantics`、`side_semantics`、`horizon` 全部必填（never-guess 一致化）；改名 `book_span_spreads_mean`（等 deep 源到位后再实现真 slope，deep_A §1.7 四个标准式全 [二手]）；删冗余列 |

**测试方法论教训（登记）**：v1 的"离线测试 PASS"没拦住以上任何一条，因为 fixture 全部**单资产、无缺口、时间充足**——验收面没覆盖设计意图路径。v2 的 9 组测试（T1–T9）强制含：多资产面板、数据缺口、陈旧特征、稀疏/空格子、maker 语义翻号、classified 分母、缺 bar 标签、边界 bin。

## 现 API（`scripts/hf_data_pipeline.py`）

`clean_orderbook(book, assume_tz=…, levels=5, max_gap=None)` → 截断深度清洗+审计计数+gap_flag
`add_event_ofi(book)` → CKS 事件级 e_n（NaN=不可测，非 0）
`clean_trades(trades, side_col=…, side_semantics=…, assume_tz=…, id_col=None)` → `aggressor_side` 规范化
`aggregate_trades(trades, window)` → 全网格成交窗（VWAP/imbalance 按 S7 口径）
`aggregate_orderbook(book, window, min_snapshots=4, rv_grid="5s", min_rv_points=4)` → 全网格特征，统一边界口径
`normalise_kline(kline, assume_tz=…, timestamp_semantics=…, bar_frequency, asset_id/asset_col)` → 声明式 bar 标准化 + `attrs` 缺口统计
`align_features_to_kline(kline, features, max_staleness=None)` → 有界过去式对齐
`make_future_labels(kline, horizon=…)` → 时间网格校验的 forward log-return + RV 标签

## 实际验证

```text
python        # conda env: kronos \
  research/scripts/verify_hf_data_pipeline.py        # → HF_DATA_PIPELINE_V2: PASS (T1–T9)
python        # conda env: kronos \
  research/scripts/calibrate_noise_floor.py data/binance/kline/BTC_USDT_1m_2024.parquet
```

真实数据干跑（2026-09-17）：200 快照盘口 200/200 保留、1 个 gap_flag、9 窗全网格（1 窗 3 快照→NaN）；1440 根 2024 K 线 0 缺失、h=5 标签 1435/1440 全非零且连续。未触网、无 token。

## 旧脚本问题记录（保留）

- `extract_features.py`（窗口起点标签+均值 OFI）与 `align_data.py`（精确 merge+ffill/bfill）的前视/语义问题见 v1 卡记录，维持"历史产物、不得作训练输入"的排除结论；
- **v1 版 `hf_data_pipeline` 自身输出同样作废**：`data/features/*.parquet` 为旧管线产物，保留仅作对照，重新生成一律走 v2。

## 不能据此声称

- 高频特征对目标有预测增量；OFI 等特征应当进模型；`L_align` 已确定；
- 供应商字段语义已全核：Tushare 侧结论来自 deep_F（[一手] 文档页），**A 股盘口/L2 无 Tushare 供给**（C-X03-001 §5），事件级 OFI 特征在 A 股上暂不可得，需另源；
- 性能已验证（bin 循环实现，A 股规模前置优化为向量化/分块——列入数据到位后的验收）；
- RV 子网格 5s 是唯一正确口径（它是可配置的标准选择，非定理）。

## 下一步

① 用 v2 重新生成 `data/` 特征与对齐文件并归档 v1 产物；② 桥接层（pair 契约+时间审计+五位证据）直接消费本模块；③ Tushare 分钟快照到位后跑 A 股复验（价格族特征版先行）；④ 真 `book_slope` 待 deep_A §1.7 的一手公式源核到后实现。
