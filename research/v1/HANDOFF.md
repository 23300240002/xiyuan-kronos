# v1 · 交接文档（HANDOFF）

> 目的：**任何一个新 agent 读完这一份就能上手**，不需要翻聊天记录。
> 最后更新：2026-10-24。所有命令都在本机 macOS + 一台租用的 4090 上验证过。

---

## 0. 三十秒版本

项目在 A 股上复现 Kronos 论文的三类实验（价格 IC/RankIC、波动率、生成），
三臂消融（仅Kronos / 仅微观 / 融合）。**P0 数据地基已完成，P1 arm-1 与 M2 已出第一版数字**。
卡在「20 个交易日的 L2 盘口数据」拿不到（百度网盘 API 变更）。

---

## 1. 环境

### 本机（macOS）
- Python：`/Users/luolingli/miniforge3/envs/vibe-trading/bin/python3.12`
  （有 tushare / pandas 2.3.3 / pyarrow 25.0.1 / duckdb 1.5.5 / scipy / sklearn；**无 torch**）
- 另一个环境 `kronos`（有 torch 2.12.0，无 tushare）——只在本地测主干时用
- 数据盘：`项目/曦源-Kronos课题/tick数据/QDCData/`

### GPU 服务器（租用 4090）
| 项 | 值 |
|---|---|
| 连接 | `ssh root@47.107.102.231 -p 9002` |
| 凭据 | `项目/曦源-Kronos课题/gpu/secret.md`（**不要把密码写进代码/git**） |
| 持久化根 | `/share/home/tm884089579940000/a891264510/work1024`（**唯一可持久目录**） |
| 规格 | RTX 4090 25.25GB / 14 vCPU / **1007GB RAM** / 5.6PB 盘 |
| 框架 | torch 2.2.2 + CUDA 12.1（镜像自带） |
| venv | `$W/envs/v1`（`--system-site-packages` 复用镜像 torch） |

**关键**：`/root` 是**只读**文件系统 → 公钥推不进去，配置目录必须重定向。
本机用 **ControlMaster 连接复用**，认证一次、12 小时保活：

```bash
# 建立（密码在 gpu/secret.md）
expect -c 'spawn ssh -M -S /tmp/gpu.sock -o ControlPersist=12h -fN -p 9002 root@47.107.102.231; expect { -re {[Pp]assword:} { send "***\r" } eof {} }'
# 之后
ssh -S /tmp/gpu.sock -p 9002 root@47.107.102.231 '<cmd>'
scp -P 9002 -o ControlPath=/tmp/gpu.sock -o ControlMaster=no <file> root@47.107.102.231:$W/...
```

**服务器没有 rsync**，上传只能 `scp` 或 `tar czf - ... | ssh ... 'tar xzf - -C ...'`。

---

## 2. 目录结构

```
项目/曦源-Kronos课题/
├─ v1/                          ← 本项目的新代码库（别动 claims/ handoff/ 原脚本）
│  ├─ xy/paths.py               路径与凭据单一入口
│  ├─ xy/data/
│  │  ├─ ts_pull.py             tushare 拉取（ref/daily/daily_basic/limit/suspend/adj/index）
│  │  ├─ daily.py               cn_tick 3s → 日频（DuckDB，77 秒）
│  │  ├─ minute.py              cn_tick → 1min/5min（48 桶口径）
│  │  ├─ pool.py                票池白名单 + 后复权 + 收益标签 + td_gap
│  │  ├─ splits.py              walk-forward + purge + embargo
│  │  ├─ dataset.py             长表 → [code,time,6] 张量 + 窗口索引
│  │  └─ l2.py                  L2 十档 → 盘口特征（不重建订单簿）
│  ├─ xy/model/backbone.py      冻结 Kronos：normalize → encode → decode_s1 → 隐状态
│  ├─ xy/train/run_arm.py       三臂统一入口（NULL-token 受控 + 早停）
│  ├─ xy/eval/
│  │  ├─ ic.py                  pooled IC/RankIC + block bootstrap + NW + 零分布
│  │  ├─ m2.py                  M2 单日截面（含当日动量对照 + 增量 IC）
│  │  ├─ compare.py             三臂汇总 + 零分布判定
│  │  └─ report.py              数据卡自动生成
│  ├─ raw/                      tushare 原始落盘（不进 git）
│  ├─ runs/panel/               面板；runs/tensor/ 张量；runs/arm/ 训练结果
│  └─ reports/                  数据卡、M2、交叉对比
├─ KronosLocal/                 模型权重 + 官方代码（只读）
├─ tick数据/QDCData/            cn_tick（25.6GB/9B行） + L2（20240205.7z）
└─ gpu/secret.md                GPU 连接信息
```

---

## 3. 完整运行顺序

```bash
cd 项目/曦源-Kronos课题/v1
PY=/Users/luolingli/miniforge3/envs/vibe-trading/bin/python3.12

# ---- 数据 ----
$PY -m xy.data.ts_pull ref                       # 交易日历/股票列表/更名
$PY -m xy.data.ts_pull daily  --start 20240102 --end 20261015
$PY -m xy.data.ts_pull daily_basic
$PY -m xy.data.ts_pull limit
$PY -m xy.data.ts_pull adj
$PY -m xy.data.daily                             # 日频面板（77s）
$PY -m xy.data.pool --horizon 5                  # 复权 + 白名单 + 标签
$PY -m xy.data.minute --freq 5 --topn 500        # 5min 面板（4.5min）
$PY -m xy.data.dataset --freq daily              # 张量
$PY -m xy.data.dataset --freq 5min
$PY -m xy.eval.report --card                     # 数据卡

# ---- 自检（任何改动后必跑）----
$PY -m xy.eval.ic --selftest
$PY -m xy.data.splits --selftest
$PY -m xy.model.backbone --selftest              # 用 kronos env 的 python

# ---- 训练（在 GPU 上）----
W=/share/home/tm884089579940000/a891264510/work1024
tar czf - v1/xy v1/runs/tensor KronosLocal/kronos_small/weights \
        KronosLocal/deps/tokenizer_base KronosLocal/deps/Kronos/model \
  | ssh -S /tmp/gpu.sock -p 9002 root@47.107.102.231 "tar xzf - -C $W/code"
ssh -S /tmp/gpu.sock -p 9002 root@47.107.102.231 \
  "cd $W/code/v1 && $W/envs/v1/bin/python -m xy.train.run_arm --arm 1 --freq daily --epochs 10 --seeds 0 1"
```

---

## 4. 已产出的结果（2026-10-24）

### 数据
| 产物 | 规模 |
|---|---|
| 日频面板 | 3,451,043 行 / 672 日 / 5,324 票 / 66.5MB |
| 复权票池 | 3,450,783 行 / 5,323 票 / 153MB |
| 5min 面板 | 16,024,225 行 / 500 票 / 48 桶 / 271MB |
| L2 解析 | **7,102 只票 / 25,780,530 快照**（全市场，不是 36 只） |
| 张量 | daily (5323,672,6) 86MB；5min (500,32256,6) 387MB |

### 三条参照线
- **噪声门槛（日频测试段）= 0.00166**（194 日 / 100.4 万行，block permutation 95% 分位）
- 噪声门槛（M2 单日截面）= 0.0140（1/√5097）
- 论文同域基准 RankIC = **0.0375**（Kronos_S，XSHG）

### arm-1 结果
- seed 0 best val_IC **+0.00653**（4 轮早停），seed 1 **+0.00794**（6 轮）
- 超噪声 **4–5 倍**且同号 → 可复现为正；达到论文基准的 **19%**
- **都在第 1 个 epoch 达峰后恶化 → 头过拟合**，瓶颈是训练数据量/正则，不是模型
- 可训练参数 2,174,098

### M2 结果（2024-02-05，全市场）
| 特征 | 原始 IC | **增量 IC**（扣当日动量） |
|---|---|---|
| imb1 | +0.3471 | **+0.3077** |
| imb10 | +0.3184 | **+0.3210** |
| slope5 | −0.1095 | **−0.1891** |
| ofi | +0.0151 | **−0.0592**（符号翻转，待解释） |
| _ret_today（对照）_ | _+0.4357_ | _—_ |

**盘口失衡扣掉动量后几乎不衰减 → 独立于 OHLCV 的信息通道**（P2 第一份正面证据）。
但单日 + 急跌/反弹行情，0.30 **极可能是反转效应的非线性残留**，必须 ≥20 日才能判定。

---

## 5. 已知坑（都是踩过的）

| 坑 | 说明 |
|---|---|
| 服务器 `/root` 只读 | 公钥推不进去；`HOME` 要重定向到 `$W/bgo-home` |
| 服务器**没有 rsync** | 用 `scp` 或 `tar \| ssh` |
| 服务器缺包 | `huggingface_hub` / `einops` / `py7zr` 要补装；pip 镜像时通时不通 |
| `stock_basic` 日期是 `YYYYMMDD` 字符串 | DuckDB 必须 `strptime(x,'%Y%m%d')`，不能直接 CAST |
| 5min 桶数 | 不处理 `11:30`/`15:00` 会得到 **50 个桶**（含 1 秒空桶），正确的是 **48** |
| `l2.py` 时段阈值单位 | `_sec()` 返回**秒**，09:30 = **34200**，不是 570（570 是分钟） |
| 停牌会让 `lag/lead` 跨缺口 | 已加 `td_gap` 列；窗口必须要求 `td_gap==1` |
| IPO 首日/复牌跳空 | `|ret1|>0.25` 的 70 行全是真实跳空，不是复权错误 |
| `qdc-cli` 是 macOS arm64 | 服务器跑不了 |
| 服务器没有 7z | 用 `py7zr`（已装 1.1.4） |
| 百度网盘 API | `ls`/`transfer`/`download` 全 `31023 param error`，BaiduPCS-Go 3.9.7 不兼容 |
| `qdc-cli` 目录里没有 L2 SKU | L2 只通过百度网盘分发（SKU 名「10档逐笔 Tick L2(网盘5T)」） |

---

## 8. 百度网盘 L2 下载（2026-10-24 已攻克到最后一公里）

### 8.1 已解决的三个问题

**① 31023 param error** —— GitHub Issue #503 给出根因：账号文件列表 API 携带
`limit=0-2147483647`，百度收紧参数校验后判为非法。
**修复方式（二进制等长补丁，不需要 Go 编译）**：
```bash
# BaiduPCS-Go v3.9.7 二进制里 0-2147483647 只出现 1 次（Go 字符串表）
python3 -c "
b=open('BaiduPCS-Go','rb').read(); assert b.count(b'0-2147483647')==1
open('BaiduPCS-Go','wb').write(b.replace(b'0-2147483647', b'0-0000001000'))"
```
改后 `limit=0-0000001000`（12 字符，格式合法，上界降到 1000）→ **`ls` 恢复**。

**② 分享链接的根路径** —— `share/list` 的 `dir` 必须是
`/sharelink<uk>-<fs_id>/<目录名>`，**不能**用 `/<目录名>`（那会返回 errno 2）。
`uk` 取页面里的 `share_uk`，`fs_id` 取顶层条目的 `fs_id`。

**③ 登录** —— `login -cookies="BDUSS=...; STOKEN=..."` 比 `-bduss=... -stoken=...` 可靠。

### 8.2 已验证可用

- 补丁版 BaiduPCS-Go 已部署在服务器 `$W/BaiduPCS-Go`
- BDUSS/STOKEN 在服务器 `.bduss` / `.stoken`（600 权限）
- `ls`、`download` 均实测通过（8.55MB / 2.3MB/s）
- 分享内容清单已导出：`/tmp/l2_manifest.json`（2024–2026 共 **676 个日文件 / 2.85TB**）
- 按行情体制分层选出的 **18 天 / 74.5GB**：`/tmp/l2_selected.json`

### 8.3 转存：已由用户在浏览器完成

用户已于 2026-10-21 把整个分享保存到：
```
/我的资源/A股逐笔十档行情/2017 ... 2026/YYYYMM/YYYYMMDD.7z
```
**所以不需要转存接口**。`/share/transfer` 返回 errno 2 的问题可以绕过。

**下载命令**（已部署的补丁客户端）：
```bash
ssh -S /tmp/gpu.sock -p 9002 root@47.107.102.231
cd $W && export HOME=$W/bgo-home
./BaiduPCS-Go login -cookies="BDUSS=$(cat .bduss); STOKEN=$(cat .stoken)"
./BaiduPCS-Go download "/我的资源/A股逐笔十档行情/2024/202404/20240408.7z" -saveto $W/l2/days
```

**当前状态**：18 天（74.5GB）正在后台下载，脚本 `$W/dl_l2.sh`，日志 `$W/l2/dl.log`，
产物落 `$W/l2/days/YYYYMMDD.7z`。实测速度约 2.3MB/s → 约 9 小时。
日期清单见 `v1/runs/l2_selected_days.json`（按行情体制分层抽取）。

**处理命令**（多日模式已加进 `xy/data/l2.py`）：
```bash
python -m xy.data.l2 --dir $W/l2/days --out $W/l2/parsed_multi
python -m xy.eval.m2_multi --parsed $W/l2/parsed_multi
```

**教训**：下次遇到类似需求，先花 10 分钟搜 GitHub issue，比盲试 API 快得多——
这个 31023 的修复方案在 issue 里写得明明白白。另外，**先问一句用户是不是已经存好了**，
比逆向转存接口快得多。

---

## 9. 纪律（违反任何一条都会毁掉结论）

0. **绝不用 `best_val_ic = max(各轮)` 做模型对比。** 必须用**全轮中位数**。
   2026-10-24 实测：DLinear 的 best=+0.072、中位数=−0.038；同一实验两种指标
   得出相反结论，冠军和垫底对调。训练轨迹不稳时，取 max 等于在噪声里挑最好的一个。
   （`xy/train/run_arm.py` 与 `run_baseline.py` 都已改为早停 patience=3 + 恢复最优状态，
   报告里必须同时给 best 和 median。）

1. **单日数据不判定**。任何 IC 必须带 `n_days`；`n_days=1` 只能写"管线通了"。
2. **零分布门槛先于实验**。`|IC| < 0.00166`（日频）/ `< 0.014`（M2 单日）不得声称有信号。
3. **增量 IC 才是 P2 的证据**。原始 IC 会把反转效应当成微观结构增量。
4. **重叠 horizon 不能用朴素 t**。用 block bootstrap 或 Newey-West。
5. **不引用未核实数字**。每个结论要能指到 `runs/` 下的 json 或一条命令。
6. **GPU 机器禁止任何挖矿任务**（服务商红线，检测到不退款）。
7. **凭据不进代码/git**：tushare token 在 `.secrets/`，GPU 密码在 `gpu/secret.md`，BDUSS 在服务器 `.bduss`（600）。
8. **验证段出的数字不叫结论**。必须再到独立测试段复算才能写进摘要。

---

## 10. 下一步（按优先级）

| # | 事 | 状态 |
|---|---|---|
| 1 | **拿到 ≥20 日 L2** | ❌ 卡在百度网盘；正在 GitHub 上找可用客户端 |
| 2 | arm-1 加正则/缩头/扩数据重跑 | ⬜ 可做 |
| 3 | arm-2 / arm-3 三臂消融 | ⬜ GPU 已就绪 |
| 4 | 5min 频段 arm-1 | ⬜ |
| 5 | 波动率（MAE/R²）+ 生成（判别分/TSTR） | ⬜ |
| 6 | 3 个基线重跑（PatchTST/iTransformer/DLinear） | ⬜ |

---

## 11. 数据完整性（重新跑流程时必做）

换数据源重跑时，必须证明**没有污染**：
1. 下载后校验大小 + md5，与源一致；
2. 重跑 `xy.data.daily`，输出必须与 `runs/panel/daily_all.parquet` 的
   `(行数, 交易日数, 票数)` 完全一致，且与 tushare 官方日线的 **MAPE 仍为 0.0000%**；
3. 重跑 `xy.data.pool`，`|ret1|>0.25` 占比仍应 ≈0.002%；
4. 每次改动数据后重跑三个 selftest。

---

## 12. 2026-10-25 追加：测试段评估（test_eval）的坑与结论

### 新增文件
- `xy/eval/test_eval.py`：加载 `best_state.pt`，在 t≥85% 的独立时间段复算
  pooled IC / RankIC / **按天 block bootstrap**（加权实现）。

### 四个坑（按严重程度）

1. **`sliding_window_view` 的窗口轴在最后**：`[T,6]` 开窗得 `[T-lb+1, 6, lb]`，
   **不是** `[T-lb+1, lb, 6]`。必须 `.transpose(0,2,1)`。否则报
   `mat1 and mat2 shapes cannot be multiplied (3072x240 and 6x256)`——
   3072=6×512 是把通道维当成 batch 了。
2. **不能一次性累积全部窗口**：K 线 238万×240×6×4B=13.7GB + 微观 27GB，
   触发容器 OOM（exit 137）。必须**逐票流式**：收集一票→立刻预测→只留预测值。
3. **block bootstrap 不能用 np.concatenate 拼块**：4838 个块 × 1000 次迭代，
   每次还要在 238 万样本上算相关 → 单次要几十分钟。改用**加权相关**：
   每天被抽中几次就是该天样本的权重，`w=counts[day_idx]`，数学等价、全程向量化。
4. **Bash 工具 120 秒超时会 SIGKILL**（exit 137）——长任务必须
   `setsid nohup ... &` 放后台，不能前台跑。

### 当前耗时基准（单评估，238.7 万窗口）
- arm-1（无微观输入）：约 18 分钟
- arm-3（有微观输入 + cross-attn）：约 25–30 分钟
- 9 个评估约 2–2.5 小时。**batch 2048 无明显加速**（GPU 计算量是瓶颈）。

### arm-1 seed 0 测试段结果（已完成，强结果）
```
pooled IC     = +0.04617   95% CI [0.04132, 0.05101]   block t = 18.4
pooled RankIC = +0.02513   n = 2,387,380   n_days = 4,815
```
对照论文沪市 IC 0.0549 / RankIC 0.0375 → 达成 84% / 67%（冻结 small + 小头）。

### 已知局限
test 取 85–100% 而 val 占 70–100%，两者重叠 → 早停间接看过 test 前 15%。
彻底修法：val 收紧到 70–85% 后重训 9 个模型（9×40 分钟 GPU）。
