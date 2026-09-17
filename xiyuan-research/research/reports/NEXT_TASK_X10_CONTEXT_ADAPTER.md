# 下一步实现任务：真实 Kronos context adapter 与 X-10 配对审计

## 任务身份

- 任务：TP9 / X-10 的最小实现前置
- 预算：1 个实现轮次，约 2--4 小时；不训练大模型，不新增跨模态玩具模型
- 结果目标：把“理论上的 $Z_L$”变成可追踪的真实 Kronos context 接口，并明确哪些信息仍需项目决定
- 完成判据：见最后一节；未满足时保持 BLOCKED

## 为什么先做它

当前真实 KronosLocal 的 `decode_s1` 已经返回 `[B,T,512]` context，但公共预测服务只返回未来路径。没有 adapter，就无法知道对齐项的两个输入是什么、是否同一 cutoff、是否实际进入预测头。先把低频接口固定下来，才能判断后续是路线 B（表征双分支）还是退回路线 A/C。

## 执行步骤

### 1. 固定低频接口

实现一个只读函数，输入：

```text
asset_id, cutoff_time, OHLCVA[context_length, 6], timestamps[context_length]
```

输出：

```text
context_last[512], asset_id, cutoff_time, normalization_stats, model_name
```

规则：归一化统计量只能来自 cutoff 以前的窗口或训练集；`context_last` 只能来自 `decode_s1` 的最后一个 observed token；不调用自回归生成，不传未来标签。

### 2. 做接口级测试

至少通过：

- 形状：`context_last.shape == [B, 512]`；
- 重复性：`eval()` 下同输入重复运行完全一致；
- 时间审计：输入窗口最后一个时间等于 `cutoff_time`，未来行不能进入函数；
- 归一化审计：验证/测试窗口不重新拟合均值和标准差；
- 缺失处理：高频缺失时明确回退到低频基线，不用零向量伪装成真实高频表征。

### 3. 决定高频配对协议

由项目组确认并落表：

```text
pair_key = (asset_id, cutoff_time)
high_frequency_window = (cutoff_time - W_H, cutoff_time]
label_window = (cutoff_time, cutoff_time + horizon]
```

必须分别记录事件时间、接收时间和实际可用时间。若三者不同，`cutoff_time` 使用部署时真正可用的时间。

### 4. 只实现一个可撤回候选

在 X-10 明确“共享子空间”后，增加两个投影头 `phi_L`、`phi_H`，并记录：

```text
L_align = mean(||phi_L(context_last) - phi_H(high_repr)||^2)
```

同时保留 `high_private = high_repr - stopgrad(phi_H(high_repr))` 或等价的显式私有通道，避免把整个高频表征压成低频表征。若尺度锚定、配对规则或部署可得性任何一项不成立，候选权重固定为 `delta=0`，只保留诊断结果。

### 5. 设计最小比较

固定同一数据切分、标签窗口、训练预算和预测头，比较：

1. 低频 Kronos context；
2. 低频 context + 高频表示，`delta=0`；
3. 同一双路模型 + 一个预注册的 `delta>0` 共享投影对齐。

主指标使用预先指定的任务损失；同时报告缺失高频回退、状态分层和部署延迟。不要用训练集 alignment loss 下降替代样本外风险证据。

## 预算与停止条件

- 本轮只完成 adapter、接口审计和小批量 smoke test；不进行超参扫描，不比较多个 alignment 变体。
- 若没有真实高频数据、时间戳字典或项目对 `L_align` 的定义，停止在步骤 3，并把 X-10 保持 BLOCKED。
- 若双路 context 只能通过修改预训练模型内部得到，先提交接口补丁和审计结果，再决定是否训练。

## 已完成的前置交付物

- `scripts/audit_kronos_x10.py`：真实权重 context 冒烟测试，PASS；
- `scripts/kronos_context_adapter.py`：真实窗口 context adapter 冒烟测试，PASS；
- `claims/C-X10-001.md`：接口审计结果卡。

## 交付物

- `scripts/audit_kronos_x10.py`：真实权重 context 冒烟测试；
- `scripts/kronos_context_adapter.py`：真实窗口 context adapter；
- `claims/C-X10-001.md`：接口审计结果卡；
- 一份 pair schema 和数据字典补丁；
- 一份预注册实验配置，包含 `delta=0` 基线和最多一个候选。

## 不能用此任务声称什么

它不能证明高频有增量预测信息，不能证明对齐损失有效，不能把模型 D 闭式推广到神经网络，也不能替代导师对接入空间和部署定义的确认。
