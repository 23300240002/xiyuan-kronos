# v1 — 曦源-Kronos 初版全流程

> 目标：在**冻结的 Kronos 主干**外接微观结构分支，用 A 股数据跑出与论文同构的三张表
> （价格 IC/RankIC、波动率 MAE/R²、生成保真度 + TSTR），三臂消融 + 3 个重跑基线。
> 详细方案见 `../review_2026-10-23/` 与 `.workbuddy-ai/plans/`。

## 目录

```
v1/
  xy/paths.py            路径与凭据（唯一入口，不写死绝对路径）
  xy/data/ts_pull.py     tushare 拉取（ref / daily / daily_basic / limit / suspend / adj / index）
  xy/data/daily.py       cn_tick 3s → 日频 OHLCVA（DuckDB）
  xy/data/minute.py      cn_tick 3s → 1min / 5min（500 票冻结票池）
  xy/data/pool.py        票池白名单 + 后复权 + 收益标签
  xy/data/splits.py      walk-forward + purge + embargo
  xy/data/dataset.py     长表 → [code, time, 6] 张量 + 窗口索引
  xy/eval/ic.py          pooled IC/RankIC + block bootstrap + NW t + 零分布门槛
  raw/                   tushare 原始落盘（不进 git）
  runs/panel/            面板产物
  runs/tensor/           张量产物
  reports/               数据卡、协议冻结、结果表
```

## 运行顺序

```bash
cd v1
PY=/Users/luolingli/miniforge3/envs/vibe-trading/bin/python3.12   # 本地：有 tushare/pandas/duckdb

$PY -m xy.data.ts_pull ref                 # 交易日历 / 股票列表 / 更名
$PY -m xy.data.ts_pull daily --start 20240102 --end 20261015
$PY -m xy.data.ts_pull daily_basic
$PY -m xy.data.ts_pull limit
$PY -m xy.data.ts_pull adj
$PY -m xy.data.daily                       # 日频面板
$PY -m xy.data.pool --horizon 5            # 复权 + 白名单 + 标签
$PY -m xy.data.minute --freq 5 --topn 500  # 5min 面板
$PY -m xy.data.dataset --freq daily
$PY -m xy.eval.ic --selftest               # 门槛自检
$PY -m xy.data.splits --from-panel
```

## 纪律

- **不改** `claims/`、`handoff/`、`KronosLocal/deps/`、已汇报文件。新代码只在本目录。
- **凭据**：tushare token 在 `../.secrets/tushare_token`；GPU 连接信息在 `../gpu/secret.md`。
  **不写进代码、不打印、不进 git。**
- **GPU 机器禁止任何挖矿任务**（服务商红线，检测到不退款）。
- **不引用未核实数字**；每个结论要能指到 `runs/` 下的 json 或一条命令。
- **单日数据不做判定**：任何 IC 必须带 `n_days`；`n_days=1` 只能写"管线通了"。

## 已知坑

| 坑 | 说明 |
|---|---|
| `cn_tick` 是 3 秒聚合，不是逐笔 | 命名一律写「成交流」，不写「订单流」 |
| `cn_tick` 每天 5,642 个 code，含 B 股/ETF/转债 | 必须用 `stock_basic` 白名单过滤（`xy.data.pool`） |
| `build_minute_panel.py` 的 `--drop-gap` 不存在 | 复权走 `xy.data.pool` 的后复权，不依赖它 |
| 论文 IC 是 **pooled**，不是按日截面 | `xy.eval.ic` 按 pooled 实现，同时给逐日 NW t 作补充 |
| 重叠 horizon 会让朴素 t 虚高 | 必须用 block bootstrap 或 NW |
| L2 只有 2024-02-05 一天 | M2（盘口）只做探针，不进主表 |
| `qdc-cli` 是 macOS arm64 二进制 | **服务器（Linux）跑不了**，只能本地下再传；要服务器直下须问 QDC 要 Linux 版/直链 |
| 服务器**没有 rsync** | 上传用 `scp -r` 或 `tar czf - \| ssh 'tar xzf -'`；断点续传用 `wget -c` |
| 服务器 `/root` 只读 | 一切写入落在 `/share/home/tm884089579940000/a891264510/work1024` |
| GPU 机器不需要原始 3s 数据 | 只传面板+张量+权重（≈0.9GB），不要传 25.6GB 的 cn_tick |
