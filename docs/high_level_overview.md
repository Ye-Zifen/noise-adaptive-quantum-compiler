# 仓库概览

## 问题定义

本仓库实现一个面向参赛者的噪声自适应量子编译映射任务。每次评测时，提交程序会收到：

- `--circuit`：Cirq JSON 格式的输入程序线路。
- `--backend`：JSON 格式的硬件后端快照。
- `--out`：编译后物理线路的输出路径。

编译后线路必须满足后端 basis 和 coupling map，并保持输入线路的无噪测量语义。提交还必须提供 layout sidecar，说明每个输入程序 qubit 的初始物理位置。评测器会用该 layout 做隐藏等价性检查。

## 赛道

### Track A：通用 NISQ 映射

Track A 使用 Cirq density-matrix 带噪采样。公开样本包括：

- `bv`
- `hs`
- `toffoli`
- `fredkin`
- `peres`
- `or`
- `adder`
- `structured_random`

这些样本使用确定性测量规则，并避免只靠消去 `U; U†` 就能得分的结构。

### Track B：Clifford 扩展性压力测试

Track B 使用 Stim 带噪采样。公开样本包括：

- `ghz`
- `parity`

Track B 仍然按最终测量 bitstring 给分，不使用 detector error model、logical observable 或 decoder-style 评分。

## 评分指标

样本级指标：

```text
success_rate = correct_shots / total_shots
```

Track 分数：

```text
TrackA = mean(success_rate over Track A public samples)
TrackB = mean(success_rate over Track B public samples)
```

总分：

```text
Final Score = 0.75 * TrackA + 0.25 * TrackB
```

评测器还会报告 shot 数、正确 shot 数、depth、两比特门数量、estimated log reliability、编译时间和 validation errors。

## 后端和噪声模型

后端位于 `backends/{small,medium,large}/`，使用 schema version `2.0`。后端包含稀疏拓扑、异质两比特错误率、异质读出错误率和一个全局单比特错误率。

噪声模型故意保持简单：

- 单比特门后加入单比特 depolarizing error。
- `cx` 后加入两比特 depolarizing error。
- 最终测量前加入读出 bit-flip error。
- 不包含 idle noise、crosstalk、pulse scheduling 或 drift model。

完整噪声定义见 [噪声模型说明](noise_model.md)。

## 校验流程

带噪评分前会依次检查：

- Cirq JSON 可读取，且输出大小受限。
- 所有物理 qubit 都是合法 `LineQubit`。
- 所有门都在后端 basis 中。
- 所有两比特操作都满足 coupling map。
- Track B 只使用 Clifford 子集。
- 测量是最终测量，并且 key 为 `z`。
- 不出现 reset、feedforward 或 classically controlled operation。
- layout sidecar 存在，并覆盖所有输入程序 qubit。
- 隐藏无噪输入挑战下，编译后线路和源线路输出分布一致。
- 无噪采样满足 benchmark 规则。

任一步失败，对应样本得分为 `0.0`。
