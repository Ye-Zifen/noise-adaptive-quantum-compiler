# 噪声模型说明

本文说明公开评测使用的噪声模型。参赛者可以直接从 `backend.json` 读取每个后端的错误率，并据此优化 layout、routing 和 decomposition。

## 1. 适用范围

噪声只在带噪评分阶段使用。下面这些检查都是无噪声的：

- 输出线路结构校验。
- layout sidecar 校验。
- hidden compiler-equivalence check。
- noiseless semantic check。

只有通过上述检查的样本，才会进入带噪采样评分。

## 2. 后端字段

每个后端快照包含：

- `single_qubit_error`：所有单比特门共享的 depolarizing error 概率。
- `two_qubit_error`：每条 coupling edge 的两比特 depolarizing error 概率。
- `readout_error`：每个物理 qubit 的最终测量 bit-flip 概率。
- `coupling_map`：允许执行两比特门的物理边。
- `basis_gates`：允许输出的门集合。

公开后端当前范围：

| backend | qubits | two_qubit_error range | readout_error range | single_qubit_error |
|---|---:|---:|---:|---:|
| `small_snapshot_a` | 7 | 0.01152 - 0.06500 | 0.00440 - 0.03600 | 0.00100 |
| `medium_snapshot_a` | 16 | 0.00675 - 0.05148 | 0.00440 - 0.06000 | 0.00100 |
| `large_snapshot_a` | 32 | 0.00549 - 0.04420 | 0.00440 - 0.04800 | 0.00100 |

## 3. 单比特门噪声

对每个非测量单比特门，评测器先执行该门，然后加入单比特 depolarizing channel：

```text
gate(q)
DEPOLARIZE1(q, p = backend.single_qubit_error)
```

Track A 通过 Cirq density-matrix simulator 实现；Track B 通过 Stim `DEPOLARIZE1` 实现。总错误概率为 `p`，错误在非 identity Pauli 上均匀分布。

## 4. 两比特门噪声

对每个两比特门，评测器先执行该门，然后按该物理 edge 的错误率加入两比特 depolarizing channel：

```text
cx(q0, q1)
DEPOLARIZE2((q0, q1), p = backend.two_qubit_error["q0-q1"])
```

如果 `two_qubit_error` 中写的是反向 key，评测器会等价读取；结构校验也把 coupling edge 当作无向边处理。也就是说，公开 v1 模型没有方向相关的 CNOT 错误差异。

两比特 depolarizing error 的总错误概率为 `p`，错误在 15 个非 identity 两比特 Pauli 上均匀分布。

## 5. 读出噪声

最终测量前，评测器对每个被测物理 qubit 加入独立 bit-flip：

```text
X_ERROR(q, p = backend.readout_error[str(q)])
measure(q)
```

这意味着读出错误和 qubit 位置直接相关。把最终测量 qubit 放到低 `readout_error` 的物理 qubit 上，通常会提高分数。

## 6. Track A 和 Track B 的差异

Track A 使用 Cirq density-matrix noisy sampling，支持公开 backend basis 中的通用门集合。

Track B 使用 Stim noisy sampling，因此输出线路必须保持 Clifford-only：

```text
x, y, z, h, s, sdg, cx, measure
```

两条赛道使用同一类 gate-local depolarizing/readout noise。差别主要是模拟器和允许门集合。

## 7. 明确不包含的噪声

公开 v1 模型不包含：

- idle noise。
- crosstalk。
- leakage。
- pulse-level scheduling。
- drift 或 time-dependent calibration。
- correlated readout error。
- reset/feedforward/classically controlled operation。
- CNOT 方向相关错误。

因此，当前优化重点应放在 qubit 选择、routing 路径和两比特门数量上，而不是 pulse scheduling 或时间排布。

## 8. 对优化策略的直接影响

参赛者可以针对下面几个量优化：

- 降低两比特门数量：`two_qubit_error` 通常明显大于 `single_qubit_error`，额外 SWAP 分解会快速拉低成功率。
- 选择低错误率路径：routing 时优先走低 `two_qubit_error` edge，而不只是最短路径。
- 选择低读出错误 qubit：最终被测 qubit 的 `readout_error` 会直接影响 `success_rate`。
- 平衡 routing 和 readout：最好的初始 layout 往往不是单纯选择读出最好的 qubit，也不是单纯选择拓扑中心，而是同时考虑交互图、低错误 coupler 和最终测量位置。
- Track B 保持 Clifford：如果输出非 Clifford 门，该样本会在结构校验阶段直接得 `0.0`。

## 9. 评分关系

噪声模型只影响采样结果。单个样本的分数仍然是：

```text
success_rate = correct_shots / total_shots
```

总分为：

```text
Final Score = 0.75 * TrackA + 0.25 * TrackB
```

资源指标如 depth、two-qubit gate count 和 estimated log reliability 会被报告，便于诊断，但不直接进入最终加权公式。
