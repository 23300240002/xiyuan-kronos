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

---

# 交接（2026-10-26 00:40）

## 一句话现状

**P2 命题在 L2 通道上部分成立**：L2 订单簿单独可预测 1 小时收益（IC +0.0268，3/3 种子为正），
但当前的交叉注意力融合会把增量破坏掉（融合臂比两个单模态都差）。
GPU 队列正在跑 Rank 损失（Q1），后面还有 Q2–Q6 排着。

## 1. 五条主线任务状态

| # | 任务 | 状态 | 关键结果/位置 |
|---|---|---|---|
| 1 | Rank 损失 | 🔄 跑第 2 个（Q1） | arm-1 s0 val_IC +0.0368；**约 7 分钟/epoch，比 MSE 慢 2.5 倍** |
| 2 | 混合损失 mse+rank | ⬜ 排队（Q2） | — |
| 3 | 波动率任务（P4） | ⬜ 排队（Q3） | `xy/train/run_vol.py` 已写好并验证标签 |
| 4 | 多频率 1min/15min | ⬜ 排队（Q4） | 张量已建好并上传（1min 1.9G / 15min 129M） |
| 5 | kronos_base 三臂 | ⬜ 排队（Q5） | 权重已上传（391M，`KronosLocal/kronos_base/weights`） |
| 6 | SDE 特征接入 | ⬜ 排队（Q6） | SDE 张量已建好并上传（6 维 / 18 维并联） |
| 7 | **L2 三臂（额外）** | ✅ **完成** | `reports/07_L2三臂消融.md` |
| 8 | M2 十八天 | ✅ 完成 | `reports/04_M2多日截面.md` |

## 2. 三个重大发现（按重要性）

### ① L2 订单簿单独有预测力（最干净的正面结果）

短上下文 L=24/H=12，18 天按日切分 12/3/3，3 种子，测试段：

| 臂 | 输入 | test IC ± std | 逐种子 |
|---|---|---|---|
| arm-1 | 仅 K 线 | +0.0033 ± 0.0096 | −0.009 / +0.003 / +0.015 |
| **arm-2** | **仅 L2 订单簿 7 维** | **+0.0268 ± 0.0115** | **+0.043 / +0.018 / +0.020（全正）** |
| arm-3 | 融合 | −0.0161 ± 0.0156 | +0.000 / −0.037 / −0.012 |

与 M2 特征级发现互相印证：**imb1 增量 IC +0.0593（t=2.73，18 天，分层符号全正）**。

### ② 当前 Fusion（交叉注意力）有害

ΔIC(arm3−arm1) = −0.0194（2/3 负）；ΔIC(arm3−arm2) = −0.0429（3/3 负）。
可能原因：L=24 短序列注意力噪声大、门控初值 0 + LN 在 12 天数据下不稳、两路尺度差异大。
**已实现两种替代融合（见 §4），但还没上传服务器、也没跑。**

### ③ 同架构换通道结论反转

M1 成交流通道：arm-2 无信号（CI 跨 0）。L2 订单簿通道：arm-2 有强信号。
→ **增量在订单簿状态，不在成交流水**。这解释了主三臂实验（M1）为什么是阴性。

## 3. 本轮修的 6 个 bug（都值得记住）

| # | Bug | 症状 | 修法 |
|---|---|---|---|
| 1 | `run_arm` 变量遮蔽 | `loss = loss_v` 覆盖字符串参数，rank 模式第 2 个 batch 起变 mix | 参数改名 `loss_type` |
| 2 | `run_l2arm` 设备不匹配 | arm-2/3 一跑就崩（arm-1 因替换掉 mb 而幸免） | evaluate 用 `dev` 而非 `device` |
| 3 | `sde` 时间键格式 | 输出 HHMM(930) 而 K 线侧用分钟数(570)，匹配率 0% | 改输出 `bucket` |
| 4 | `m2_multi` OOM | 一次性读 14 万文件（90 亿单元格）被静默杀死 | 逐文件即时聚合 |
| 5 | `l2_tensor` code 后缀 | `000001.SZ` vs 票池 `000001`，匹配 0 | `code.split(".")[0]` |
| 6 | 服务器 5min meta 缺 times | `KeyError: 'times'` | 上传本地新版 meta |

## 4. ✅ 融合三模式已实现、验证并上传（01:00 更新）

**`run_arm.py` 与 `run_l2arm.py` 都已支持 `--fusion {xattn,concat,gate_res}`**，
服务器已同步，L2 对比实验已跑完（结果见 `07_L2三臂消融.md` §7）：
concat IC +0.0022（vs xattn −0.0161），方差降 58%，但仍不超 arm-2 的 +0.0268。

三种模式的实现：

```python
Fusion(mode="xattn")    # 原始交叉注意力（当前所有实验用的）
Fusion(mode="concat")   # K线末点 + 微观均值拼接 → Head（无注意力，最稳）
Fusion(mode="gate_res") # h + tanh(g)·W(m_mean)（标量门控残差）
```

- `concat` 输出 `[B, 2*d_model]` 向量，Head 直接吃（不做时间池化）
- `xattn` / `gate_res` 保留时间维，用「末点 + 尾部均值 + 尾部标准差」三拼
- 三种模式 × 三臂共 9 种组合已通过形状与梯度验证（0.53M–1.88M 参数）
- 目录名后缀现为 `{loss}_{micro}_{size}_{fusion}`

## 5. 下一步优先级

1. **修融合**（最高价值）：`--fusion concat` 跑 L2 arm-3，目标在 arm-2 的 +0.0268 之上拿正增量
2. **扩 L2 天数**：18 天且分散是最大限制（lookback 被压在 24）。网盘还有 676 天可用，
   下载脚本机制已跑通（`/tmp/dl_one.sh`，BaiduPCS-Go 已 patch，2.3MB/s，约 4GB/天）
3. **Rank 损失降本**：7 分钟/epoch × 10 epoch × 12 个 run = 14 小时，太贵。
   建议降到 `--epochs 6`，或只跑 arm-1/arm-3 各 2 个种子
4. 中性化（市值/换手）——`daily_basic` 数据已拉，纯后处理，最便宜

## 6. 操作手册

```bash
W=/share/home/tm884089579940000/a891264510/work1024
SSH="ssh -S /tmp/gpu.sock -p 9002 root@47.107.102.231"

# 看 GPU 队列阶段
$SSH "strings $W/runs/gpu_master.log | grep -aE '^####|^--- ' | tail -5"

# 看 L2 三臂结果
$SSH "cd $W/code/v1 && $W/envs/v1/bin/python -c \"
import json,glob,numpy as np
r={}
for f in sorted(glob.glob('runs/l2arm/arm*/result.json')):
    d=json.load(open(f)); r.setdefault(d['arm'],[]).append(d['test']['ic'])
for a,v in sorted(r.items()): print('arm-%d IC %+.5f (n=%d)'%(a,np.mean(v),len(v)))\""

# 上传代码（注意：队列在跑时热替换会让后续 run 用新代码，命名可能不一致）
cd "/Users/luolingli/Documents/work/项目/曦源-Kronos课题"
tar --disable-copyfile -czf /tmp/xy.tgz v1/xy
scp -P 9002 -o ControlPath=/tmp/gpu.sock -o ControlMaster=no /tmp/xy.tgz root@47.107.102.231:$W/
$SSH "cd $W && tar xzf xy.tgz -C $W/code --overwrite"
```

**踩坑提醒**：
- 本地长任务必须用工具的 `run_in_background`，`nohup &` 会被工具超时杀掉
- 服务器长任务用 `setsid nohup ... & disown`
- `tar czf - 相对路径` 解压会深一层，需 `mv` 归位
- 目录名现在带 `{loss}_{micro}_{size}` 后缀，防覆盖

---

# 交接（2026-10-26 13:40 · 12 小时窗口收尾）

## 一句话现状

**找到了第一个产生真实增量的融合方法：MoE**（RankIC +0.0668 vs 仅 K 线 +0.0598，
IC +0.0126 vs +0.0033）。30 天连续 L2 数据解析中（7/30 天）。

## 1. 本轮最大成果：MoE 融合突破

| 方法 | test IC | test RankIC | 参数量 |
|---|---|---|---|
| arm-2 单模态（上界参照） | **+0.0268** | +0.0323 | 1.88M |
| arm-1 单模态 | +0.0033 | +0.0598 | 1.88M |
| xattn（原版） | −0.0161 | +0.0173 | 1.88M |
| gate_res | −0.0109 | +0.0328 | 0.56M |
| concat | +0.0022 | +0.0452 | 0.53M |
| film | −0.0039 | +0.0515 | 0.63M |
| gmu | +0.0020 | +0.0541 | 0.83M |
| **moe2** | **+0.0126** | **+0.0668 ± 0.0035** | 0.83M |
| late_ens（buggy） | −0.0171 | +0.0108 | 0.66M |

**MoE 为什么能行**（文献机制被验证）：路由 `w=softmax(R[h;m])` 让两路走**独立专家网络**，
梯度在专家层面天然分流，弱模态不会被强模态淹没。而 xattn/GMU 共享一个融合算子，
弱模态只能被压制或忽略。

**这是项目第一次"融合 > 最好单模态"**，P2 命题从阴性转为**条件性阳性**。

## 2. 本轮修的 11 个 bug（前 7 个见上一节交接）

| # | Bug | 后果 |
|---|---|---|
| 8 | `run_arm --freq` 只接受 daily/5min | 多频率秒失败 |
| 9 | `test_eval --match` 没传到 evaluate | **评估会用错权重算出假结果** |
| 10 | `queue_fix.sh` 的 pgrep 自匹配死循环 | 补跑队列永久卡住 |
| 11 | l2 解析单线程 1 小时/天 | 30 天要 30 小时 |
| 12 | GMU/FiLM/MoE 未广播微观 token | size mismatch |
| 13 | `late_ens` 单 token 的 std 恒为 0 | 微观头输入 1/3 退化，IC −0.0338 |

## 3. 数据状态

**30 天连续 L2 块（20241008–20241118）解析中：7/30 天完成，约 90GB**

- 位置 `$W/l2/parsed_30d/`（每票每日一个 parquet）
- **含 40 个无量纲原始十档**（bdist/adist 档位距离 + blog/alog 挂单量对数）+ 13 个派生特征
- 解析器已加多进程（`--workers 10`），约 7 分钟/天
- **注意**：解析曾因 BrokenPipeError 中断过一次，已从断点续跑（脚本 `parse30.sh` 里写死了剩余 25 天的日期）

## 4. 未完成的任务（按优先级）

| # | 任务 | 说明 |
|---|---|---|
| 1 | **30 天解析跑完** | 剩 23 天，约 2.7 小时。完成后建张量 → L2 截面实验（lookback 可到 240） |
| 2 | **xsec stride=40 公平验证** | 决定截面模型 headline 结论的严格性，约 20 分钟 |
| 3 | xsec_z / rank / sde 的测试段评估 | 目前只有 val IC，口径不统一 |
| 4 | 多频率 15min/1min | `--freq` 已修，脚本 `/tmp/multifreq.sh` 可直接跑 |
| 5 | MoE 在 M1 通道上复现 | 验证"MoE 有效"不是 L2 特例 |
| 6 | 真·晚期集成 | 分别训练 arm-1/arm-2 → 推理时平均预测（需保存预测值） |

## 5. 关键命令

```bash
W=/share/home/tm884089579940000/a891264510/work1024
SSH="ssh -S /tmp/gpu.sock -p 9002 root@47.107.102.231"

# 解析进度
$SSH "ls $W/l2/parsed_30d/ | cut -c1-8 | sort -u | wc -l; tail -1 $W/runs/parse30.log"

# 融合横评结果
$SSH "cd $W/code/v1 && $W/envs/v1/bin/python -c \"
import json,glob,numpy as np
for fus in ['xattn','concat','gate_res','gmu','film','moe2','late_ens']:
    v=[json.load(open(f))['test'] for f in glob.glob('runs/l2arm/arm3_L24_H12_%s_s*/result.json'%fus)]
    if v: print('%-9s IC %+.5f RankIC %+.5f (n=%d)'%(fus,np.mean([x['ic'] for x in v]),np.mean([x['rank_ic'] for x in v]),len(v)))\""

# 续跑解析（如再次中断）
$SSH "cd $W && DONE=\$(ls l2/parsed_30d/ | cut -c1-8 | sort -u | paste -sd, -) && ..."  # 见 parse30.sh
```

## 6. 踩坑提醒（新增）

- **`kill -STOP` 会让监控误判**：监控若自动重启会造出重复队列，务必只读告警
- **`pgrep -f 'pattern'` 会匹配自己**：`while pgrep -f 'xxx'` 死循环，改用 PID 或加 `grep -v $$`
- **单 token 的 `std` 恒为 0**：任何"末点+均值+标准差"池化都要检查序列长度是否为 1
- **多进程 Pool 崩溃会抛 BrokenPipeError**：父进程死时子进程还在写，续跑要跳过已完成部分
