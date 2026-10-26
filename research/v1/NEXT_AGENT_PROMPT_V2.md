# 下一个 Agent 的上手 Prompt（V2 · 2026-10-26 15:10）

> 复制下面整段给下一个 agent。
> **重要**：本文件取代旧的 `NEXT_AGENT_PROMPT.md`。旧的交接里"30 天解析快跑完了"是错的——
> 那份数据**全部作废**。先读 §0 再读别的。

---

## 0. 三十秒版本（先看这个，别跳过）

上一轮 Agent 查出一个**P0 数据事故**：30 天 L2 连续块的解析产物 `l2/parsed_30d`
**全部被跨日期污染**（不同日期的文件内容是彼此的副本，11 个日期只有 6 组不同内容）。
根因是 `xy/data/l2.py` 用 `out.rglob()` 在整个输出目录上扫描，而解压残留从不清理。

**万幸**：污染数据**尚未被用来建过任何张量**，所以**没有任何已发表结论被污染**。
但 `parsed_30d` 必须全部重建，这是当前唯一的阻断项。

**当前状态**（15:10）：
- ✅ 已停止污染进程、已写出事故报告 `reports/11_数据污染事故.md`
- ❌ **l2.py 还没修**（服务器上仍是 14:09 版本，第 189 行 rglob 原样未动）
- ❌ `parsed_30d` 里仍有 75,370 个污染 parquet + 11 个残留解压目录
- 🔄 GPU 上 **MoE + M1** 验证正在跑（s0 已完成，s1 在跑，s2 未开始）

---

## 1. 你的首要任务

**按顺序做 T1→T2→T3，做完才能谈实验。** 这 3 件是阻断项。

1. **修 `xy/data/l2.py`**（T1）——不改这个，后面全是白跑
2. **清理并重跑 30 天解析**（T2）
3. **用"签名去重"验证解析正确性**（T3，唯一能抓住本 bug 的方法）
4. 然后才是 **建 30 天 L2 张量 → L2 截面实验**（T4/T5）

---

## 2. 项目本质（没变）

**冻结 Kronos 时序基础模型（102M/4.1M 参数）当特征提取器，只训一个小头**，
在 500 只 A 股 × 5min K 线上做收益率预测，验证三件事：

1. **P2 命题**：微观结构数据（订单簿 L2 / 成交流 M1）能否给 K 线带来增量？
2. **P4 三任务**：收益率、波动率、跨频率稳健性
3. **算法改进**：不靠加数据，靠结构/损失/融合方式提升

---

## 3. 已确立结论（直接采信，不要重跑）

| 结论 | 数据 | 强度 |
|---|---|---|
| **5min 三臂：融合无增量**（P2 阴性） | arm-1 IC +0.03791 / arm-3 +0.03638，ΔIC −0.00153，t≈−0.67（3 种子配对） | 强 |
| **M1 成交流单模态无信号** | arm-2 IC +0.00075 ± 0.00053 | 强 |
| **L2 订单簿单模态有真信号** | arm-2 IC +0.02676（18 天分散，L=24），是 K 线单模态 +0.00328 的 8 倍，3/3 种子为正 | 强 |
| **交叉注意力融合有害** | xattn IC −0.01612，比两个单模态都差 | 强 |
| **concat 把融合修到中性** | +0.00216，方差降 58%，但仍不超 arm-2 | 强 |
| **截面注意力使 RankIC 提升 2.9 倍** | +0.04118 vs arm-1 +0.01442；归因于**结构**而非标签（截面标签单独用 −30%） | 中（stride 待对齐） |
| **MoE 是唯一产生增量的融合** | L2 上 IC +0.01259（vs arm-1 +0.00328，3.8×），RankIC +0.06682（vs +0.05983） | 中（L=24 限定） |
| **波动率可预测** | 冻结隐状态 → 2 小时已实现波动率，R² +0.0322 ± 0.0032 | 强 |

### 机制解释（写论文要用）
- **模态不平衡**（arXiv 2609.10261）：融合网络里强模态占 77% 梯度，弱模态被淹没。
  这解释了为什么 xattn/GMU 都失败——它们共享一个融合算子。
- **MoE 为什么能行**：专家网络让梯度分流，弱模态走自己的专家，不被淹没。

### 口径限定（写论文必须带上）
- 融合无增量：仅限 **M1 通道 + L=240 + 672 天**
- L2 单模态有信号：仅限 **18 天分散 + L=24（半天上下文）**
- 交叉注意力有害：仅限 **L=24 短序列**
- MoE 产生增量：仅限 **L2 + L=24**，M1 通道验证中
- 截面注意力 2.9 倍：训练 **stride=80（一半样本）**，严格公平性待验证

---

## 4. 环境

```bash
# 本地项目
cd "/Users/luolingli/Documents/work/项目/曦源-Kronos课题/v1"

# 服务器（SSH 复用连接，必须带 -S）
W=/share/home/tm884089579940000/a891264510/work1024
SSH="ssh -S /tmp/gpu.sock -p 9002 root@47.107.102.231"
$SSH "ls $W"          # 先确认连接还活着
# 若连接断了：ssh -MNf -S /tmp/gpu.sock -p 9002 root@47.107.102.231

# 环境
# 服务器：$W/envs/v1/bin/python（torch 2.4 + GPU，14 vCPU / 1007GB RAM / RTX4090 25GB）
# 本地：/Users/luolingli/miniforge3/envs/kronos/bin/python（无 GPU，只做语法/形状验证）
# 服务器没有 rsync，传文件用 scp 或 tar|ssh

# GitHub 同步（research/ 子目录）
cd /tmp/xiyuan-kronos-sync && git add -A research/ && git commit -m "..." && git push
```

---

## 5. 子任务清单（详细 prompt，可直接分派给子 agent）

> 每个子任务都写成了**可独立分派的完整 prompt**。
> 分派时把该段 + 「§7 通用纪律」一起给子 agent。

### T1 · 修 l2.py 跨日期污染（P0，阻断，无依赖）

```
任务：修复 $W/code/v1/xy/data/l2.py 的跨日期数据污染 bug。

【已确认的根因，不要重新排查】
run() 函数第 189 行: stocks = sorted([p.parent for p in out.rglob("行情.csv")])
第 201 行:           feat.to_parquet(out / f"{date_tag}_{name}.parquet", index=False)

out 是输出根 $W/l2/parsed_30d。z.extract() 把当天 500 只票解压到 out/<YYYYMMDD>/<code>/，
且解压后从不清理。于是第 N 个归档运行时，rglob 扫到的是前 N-1 天残留的目录 + 当天新解压的，
再统统按第 N 天的 date_tag 重写 → 文件名是第 N 天，内容是历史某天。

【铁证】
- 日志：票池过滤后剩 500，下一行却"待处理 59852 只票"（差 119 倍）
- 实测 000001.SZ：20241014 内容与 20241008 逐元素相等（allclose=True）
- 11 个日期按内容签名只有 6 组不同值；000002.SZ 呈现完全相同的分组结构
- parquet 总数 75,370，正确应为 30×500=15,000

【修复要求】
1. rglob 范围限定到本次归档解压出的子树（推荐从 z.getnames() 直接推出目录，不扫目录）
2. 解压暂存与输出目录分离，处理完 rmtree 清理残留（当前 120G 磁盘大部分是残留）
3. 加幂等断言：同一 (date_tag, code) 若被处理两次则 raise（把静默错误变成崩溃）
4. 保持 --pool-from / --keep-raw / --workers / 单归档 --archive 模式语义不变
5. 保持多进程

【验收（必须实测，不许只看代码）】
- 每日期 parquet 数 == 500
- 相邻日期同名票 allclose == False
- 日志显示"待处理 500"，不再出现 59852
- 处理完不残留 <YYYYMMDD>/<code>/ 目录
- 单归档 --archive 模式仍可用

【注意】本地也有一份 xy/data/l2.py，本地改完再上传服务器，两处同步。
```

### T2 · 清理 + 重跑 30 天解析（依赖 T1）

```
任务：T1 验收通过后，清理污染数据并重跑 30 天 L2 解析。

【第 0 步 安全检查】
ps -eo pid,args | grep -E "xy.data.l2" | grep -v grep   # 必须为空

【第 1 步 清理（破坏性）】
目标：/share/home/tm884089579940000/a891264510/work1024/l2/parsed_30d
- 先 echo 解析后的绝对路径并核对前缀，确认正是 parsed_30d
- 【不要直接 rm】先 mv 成 parsed_30d_corrupt_backup，验证新解析无误后再删
- 绝不要碰 $W/l2/days/（210G 原始 7z，唯一原始资产，删了要重下 74.5GB）
- 绝不要碰 runs/tensor/micro_l2_5min（18 天散点张量，与本 bug 无关）

【第 2 步 重跑】
W=/share/home/tm884089579940000/a891264510/work1024
cd $W/code/v1
setsid nohup bash $W/parse30c.sh > $W/runs/parse30d_fixed.log 2>&1 < /dev/null & disown
sleep 40 && ls -la $W/runs/parse30d_fixed.log   # 验证日志真被创建（setsid 偶发不生效）

【第 3 步 验收】
- parquet 总数 == 15000；每日期 == 500
- 相邻日期同票内容不同
- 日志每段"待处理 500"
- 与 5min K 线日期/票池对齐（20241008–20241118）

【纪律】--workers ≤ 6（与训练共享 14 vCPU）；日志直写不过 grep；
禁止加任何自动重启监控（历史上因此造出 3 个重复队列，浪费 50 分钟 GPU）。
```

### T3 · 解析正确性校验工具（依赖 T2，代码可先写）

```
任务：写一个可复用的校验脚本，证明 parsed_30d 没有跨日期污染。

核心思路【这是唯一能抓住本 bug 的校验方法】：
不要用 path_date 列校验（它随写入而正确，永远"对"）。
必须用【跨记录的内容签名】：
  sig = (行数, 首行 mid, 末行 mid, 全部数值列校验和)
对同一只票，在 30 个日期上应得到 30 个【两两不等】的签名。
若出现重复 → 说明又污染了。

交付：
- 脚本落到项目 xy/data/verify_l2.py（服务器上 /tmp 亦可，但建议入库）
- 输出：每日期 parquet 数、签名分组表、重复组报告
- 断言：任何一组签名包含 >1 个日期 → exit 1
把它做成 T2 的强制收尾步骤，以后每次重解析都跑。
```

### T4 · 建 30 天 L2 张量（依赖 T2/T3 通过）

```
任务：用修好的 parsed_30d 建 L2 张量，lookback 可提到 240（5 天，与 K 线臂同口径）。

参考现有实现：xy/data/l2_tensor.py（18 天版本，产出 runs/tensor/micro_l2_5min）
- 现有 meta: 7 维特征（imb1/imb5/imb10/ofi/slope5/spread/dmid），aligned_with=5min，nan_ratio=0.9733
- 新解析带 --keep-raw，含 40 个无量纲原始十档（bdist/adist/blog/alog 各 10 档）
  → 可考虑同时产出 7 维版和 47 维版（7 派生 + 40 原始），供 DeepLOB 路线用

要点：
- 时间对齐：解析输出的 t 是秒（09:30=34200），K 线侧是 bucket；务必核对匹配率
- 覆盖率：建完检查 nan_ratio（18 天版是 0.9733）
- 建完打印 shape / nan_ratio / matched_bars 并与 18 天版对比
- 新张量命名勿覆盖 micro_l2_5min，用 micro_l2_30d_5min

验收：n_l2_days == 30，日期连续覆盖 20241008–20241118，nan_ratio 合理
```

### T5 · L2 截面实验（依赖 T4）

```
任务：30 天连续 L2 + 截面注意力 + lookback 240，与 arm-1 同口径。

背景：18 天分散数据把 lookback 压在 24（半天），是 L2 实验与 K 线实验不可比的根源。
30 天连续块允许 lookback 240（5 天），这是本实验唯一的新变量。

配置要求（必须与 arm-1 完全同口径，否则不可比）：
- lookback 240 / horizon 24 / stride 40 / batch 128（5min 的 stride 必须 40）
- 3 个种子（单种子结论不可用）
- 标签口径一致；跨标签比较只能用【测试段对原始收益】算的指标
- 样本数必须重新核对（L2 覆盖率过滤后样本会降）

对照系：
- arm-1（仅 K 线，L=240）测试段 IC +0.03791
- 18 天 L2 arm-2 测试段 IC +0.02676（但那是 L=24，不可直接比——这正是要解决的）

要回答的问题：lookback 从 24 提到 240 后，L2 单模态信号是变强还是变弱？
```

### T6 · GPU 结果收集与 MoE-M1 收尾（可并行，只读）

```
任务：收集 GPU 上正在跑/已跑完的结果，不改代码不杀进程。

1. MoE 在 M1 通道（moe_m1b）：
   看 $W/runs/moe_m1b.log 与
   runs/arm/arm3_5min_s{0,1,2}_h64_d0.3_w0.1_mse_m1_small_moe2_raw/result.json
   s0 已完成：best_val_ic +0.04443（4 epoch 早停）
   注意：MoE 配置的 train_loss 是 [0,1] 归一化尺度（0.0015），与 mse 臂的 0.69
   不是同一量纲，不要横向比 loss。
   目标：3 种子 val IC 均值 ± std；若显著 > arm-3 xattn，则 P2 在 M1 通道也成立。

2. 汇总对照表（val IC；注明不能跨标签/跨 loss 口径比）：
   - arm1/arm2/arm3 mse（旧目录 arm?_5min_s?_h64_d0.3_w0.1）：
     arm1 0.05182/0.04310/0.04235；arm2 0.01671/0.00979/0.00990；
     arm3 0.05502/0.03958/0.03643
   - arm1/arm3 rank（*_rank_m1_small_xattn_raw）
   - arm3 moe2-M1（*_mse_m1_small_moe2_raw）

3. 报告要带：种子数、口径（val/test）、文件路径。禁止"应该/大概"。
```

### T7 · 修 `--loss mix`（本轮新发现的 bug，独立可做）

```
任务：修 run_arm.py 的 --loss mix。Q6 队列的 4 个 mix 运行全部无产出。

【已确认的三个事实】
1. mix 的 loss 被 rank 项完全主导：
   mse 臂 train_loss ≈ 0.0015～0.0017
   rank 臂 train_loss ≈ 0.692
   mix 臂实测 ep00 loss = 0.69418 → mse 项只贡献约 0.2%，等于没混
   原因：F.mse_loss 与 rank_loss 量纲差约 450 倍，直接相加 λ=1 时 mse 被淹没。
   修法：对两项做尺度归一（如 mse/scale_mse + λ*rank/scale_rank），
   或用自适应权重，或对 mse 项乘大系数。
   修完必须验证两项都真的在起作用（看各自梯度范数），不能只看总 loss。

2. 队列幂等检查路径与实际输出路径不一致（会重复跑已完成实验）：
   gpu_master2.sh 第 15 行:
   local OUT="runs/arm/arm${arm}_${fq}_s${s}_h64_d0.3_w0.1_${loss}_${micro}_${size}_${fus}/result.json"
   但 run_arm.py 第 446 行实际写到 ..._{loss}_{micro}_{size}_{fusion}_{label}
   → 少了 _raw 后缀。后果：队列永远认为"没跑过"，重复劳动。
   修法：两处统一；建议队列从 run_arm import 路径构造函数，避免再次漂移。

3. 为什么 4 个 mix 任务 15 秒就"结束"而没产物：优先怀疑上面第 2 条。
   请实测复现一次 mix 单跑：
   $W/envs/v1/bin/python -u -m xy.train.run_arm --arm 1 --freq 5min --epochs 1 \
     --seeds 0 --loss mix --lookback 240 --horizon 24 --stride 40 --micro m1 --fusion xattn
   看它到底写到哪里、有没有报错。

【验收】mix 单跑 1 epoch 能产出 result.json 到正确路径；两项 loss 量纲可比。
```

### T8 · xsec stride=40 公平验证（需 GPU 空闲，~20 分钟）

```
任务：把截面模型的训练 stride 从 80 改成 40，与 arm-1 公平比较。
这是 headline 结论（RankIC 提升 2.9 倍）的严格性所在。

现状：xsec 用 stride=80（一半样本），arm-1 用 stride=40。
结论"保守"（xsec 用更少数据赢了），但严格比较需补齐。

要求：
- 先确认 run_xsec.py 的 --stride 已参数化（reports/09 说已参数化，需实测确认）
- 其余配置完全不变，只改 stride 80→40
- 3 个种子
- 测试段指标必须与 arm-1 同口径，用【对原始收益】算的 pooled IC / pooled RankIC
- 预计 ~20 分钟；启动前先 ps 确认无残留训练进程

报告：xsec@40 vs xsec@80 vs arm-1 三方对照，注明样本量。
```

### T9 · 真·晚期集成（独立，需改代码）

```
任务：实现真正的晚期融合——分别训练 arm-1 和 arm-2，推理时平均预测。

为什么之前失败：late_ens 是"联合训练两个头"，且第一版把单 token [B,1,d] 做
"末点+均值+标准差"池化，单 token 的 std 恒为 0，微观头输入 1/3 退化 → IC −0.0338。

正确做法：
1. 分别训练 arm-1（仅 K 线）和 arm-2（仅 L2），各自保存权重
2. 推理时分别预测，再平均（或按验证段 IC 加权）
3. 结构上不可能破坏任一路——理论最稳的融合

需要：保存预测值的机制（当前只存 best_state.pt 和 result.json，没存 predictions）。
验收：3 种子，测试段 IC/RankIC，与 arm-1/arm-2 单模态对照。
```

---

## 6. 优先级

| 优先级 | 任务 | 状态 | 说明 |
|---|---|---|---|
| **P0** | T1 修 l2.py | ❌ 未做 | 阻断一切 L2 实验 |
| **P0** | T2 清理+重跑 | ⬜ 待 T1 | 约 2–3 小时（30 天 × ~5 分钟） |
| **P0** | T3 签名校验 | ⬜ 待 T2 | 唯一能抓住本 bug 的校验 |
| **P1** | T6 MoE-M1 收尾 | 🔄 跑着 | s0 完成 +0.04443，s1 在跑 |
| **P1** | T4 建 30 天张量 | ⬜ 待 T2/T3 | lookback 可到 240 |
| **P2** | T5 L2 截面实验 | ⬜ 待 T4 | 当前最高科学价值 |
| **P2** | T7 修 --loss mix | ⬜ 独立 | 顺手修，成本低 |
| **P3** | T8 xsec stride=40 | ⬜ 需 GPU 空 | ~20 分钟 |
| **P3** | T9 真·晚期集成 | ⬜ 独立 | 需改代码存预测值 |

---

## 7. 通用纪律（每个子 agent 都要遵守，来自 11 个文档的血泪教训）

### 进程管理（最大的坑）
1. **残留进程会静默抢 GPU**。本项目多次出现 2–3 个 `run_arm` 并存，
   单次训练从 25 分钟变 80+ 分钟。启动前必查：
   ```bash
   $SSH 'ps -eo pid,etimes,args | grep -E "run_arm|xy.data.l2|test_eval" | grep -v grep'
   ```
2. **判断卡死不能只看"没输出"**（grep 会缓冲）。用两次采样看 CPU 时间：
   ```bash
   P=$(pgrep -f run_arm | head -1); ps -o time= -p $P; sleep 10; ps -o time= -p $P
   ```
3. **`pgrep -f 'pattern'` 会匹配自己**，`while pgrep -f 'xxx'` 是死循环。
4. **绝对不要加"自动重启"**。曾因此造出 3 个重复队列并行跑不同 seed，浪费 50 分钟 GPU。
   监控只做只读告警。
5. **`setsid nohup ... & disown` 偶发不生效**，启动后必须验证日志文件真被创建。
6. **长任务日志必须直写，不要过 `grep | tail`**（会缓冲到进程结束，看不到进度）。

### 评估与目录
7. **`test_eval` 必须传 `--match`**。同一 arm/seed 有多个版本目录时，
   `sorted(glob)[0]` 会选到最早的，用错权重算出**看起来正常但完全错误**的结果。
8. **单 token 的 std 恒为 0**。任何"末点+均值+标准差"池化都要检查序列长度。
9. **不要用数据自带的元数据列校验数据**（如 `path_date`）——
   它随写入而正确，永远"对"。要用内容签名。**这是本次事故的核心教训。**

### 口径一致性
10. **跨标签的 val IC 不可直接比**（raw vs 截面 z-score 的 Pearson 口径不同）。
11. **stride 决定样本量**：5min=40 / 15min=13 / 1min=200，不对齐就不是"频率"的差异。
12. **L2 覆盖率低**，涉及 L2 的模型要按微观侧有效性过滤窗口，否则 NaN 污染训练。
13. **跨 loss 口径的 train_loss 不可比**（MoE 配置是归一化尺度 0.0015，mse 是 0.69）。
14. **测试段只有 3 天（5min）/ 20,638 窗口（L2）**，IC 绝对值小，
    任何结论必须标注「测试段天数 + 窗口数」。
15. **val→test 衰减普遍 17%**，最极端一例 41% → 3.5%。只报验证段结果的结论一律不可信。
16. **种子方差可达 ±0.021**，单种子结论不可用。

### 统计纪律（HANDOFF §9）
17. **绝不用 `best_val_ic = max(各轮)` 做模型对比**，必须用全轮中位数。
    （实测 DLinear best=+0.072、中位数=−0.038，结论完全相反）
18. **单日数据不判定**；**零分布门槛先于实验**；
    **增量 IC 才是 P2 的证据**（原始 IC 会把反转效应当成增量）；
    **重叠 horizon 不能用朴素 t**（用 block bootstrap / Newey-West）。
19. **不引用未核实数字**。每个结论要能指到 `runs/` 下的 json 或一条命令。

### 其它
20. **破坏性操作前必须 echo 出解析后的绝对路径并核对前缀**。
21. **绝不要碰**：`$W/l2/days/`（210G 原始归档）、`runs/tensor/micro_l2_5min`（18 天散点张量）。
22. 服务器没有 rsync；`/root` 只读；凭据不进代码/git。

---

## 8. 代码地图

```
xy/
  model/backbone.py      冻结 Kronos 封装（hidden() 返回 [B,T,d]）
  train/run_arm.py       三臂训练（核心！Fusion 类有 7 种融合；--loss mse/rank/mix）
  train/run_l2arm.py     L2 专用（L=24/H=12 短上下文）
  train/run_xsec.py      截面注意力模型（MASTER 借鉴，含特征缓存）
  train/run_vol.py       波动率任务
  eval/test_eval.py      测试段评估（注意 --match 参数！）
  data/l2.py             订单簿解析（--keep-raw 存 40 维原始十档）★ 待修
  data/l2_tensor.py      3 秒快照 → 5min 桶聚合
  data/build_tensor.py   建张量
```

**必读报告（按顺序）**：
1. `reports/11_数据污染事故.md` — **先读这个**，本轮的 P0
2. `reports/09_全流程Review.md` — 所有实验核对、可比性矩阵、结论分级
3. `reports/10_融合方法横评.md` — 7 种融合对比与 MoE 突破
4. `reports/08_算法改进.md` — 截面注意力的来龙去脉
5. `HANDOFF.md` — 13 个 bug 清单
6. `PITFALLS.md` — 注意事项唯一权威版本

---

## 9. 数据资产

| 资产 | 位置 | 状态 |
|---|---|---|
| 5min K 线张量 | `$W/code/v1/runs/tensor/5min/x.npy` [500, 32256, 6]，672 天 | ✅ 可用 |
| 1min / 15min / daily | 同目录 | ✅ 可用 |
| M1 成交流（12 维） | `runs/tensor/micro_m1_5min/` | ✅ 可用 |
| SDE 特征（6 维） | `runs/tensor/micro_sde_5min/` | ✅ 可用 |
| L2 18 天分散（7 维） | `runs/tensor/micro_l2_5min/` | ✅ 可用（n_l2_days=18） |
| **L2 30 天连续块** | `$W/l2/parsed_30d/` | 🔴 **全部作废，待重建** |
| L2 原始归档 | `$W/l2/days/*.7z`（210G） | ✅ 完好，无需重下 |

---

## 10. 一句话交接

**上一轮找到并定位了一个 P0 数据污染事故，已止损但未修复。
你的第一件事是把 `l2.py` 修好、重跑 30 天解析、用签名去重校验正确性。
在 T1–T3 完成之前，任何 L2 实验都是白跑。**
**算法侧方向已明确（MoE + 截面注意力），数据侧原始归档是完好的，
修好解析器就能拿到真正的 30 天连续块。**
