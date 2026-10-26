# 参赛指南

本文说明参赛者需要实现什么、如何本地运行、输出文件必须长什么样，以及评测器如何给分。

比赛规则、开放资源边界和正式评测硬件量级见 [比赛规则与评测环境](rules_and_environment.md)。

## 1. 基本任务

每个 benchmark 会给出一个输入线路 `circuit.json` 和一个硬件后端 `backend.json`。你的任务是把输入线路映射到后端的物理 qubit 和 coupling map 上，输出一个合法的物理线路。

编译后线路需要满足两件事：

- 无噪声时，它和输入线路实现同一个测量行为。
- 有噪声时，它尽量提高正确输出概率。

比赛不是最小化门数比赛。门数、depth 和 estimated log reliability 会被报告，但主分数只来自正确输出概率。

## 2. 黑盒命令接口

评测器会按下面的形式调用你的编译器：

```bash
your-compiler \
  --circuit path/to/circuit.json \
  --backend path/to/backend.json \
  --out path/to/compiled_circuit.json
```

你的程序可以有其他固定参数，但必须接受这三个参数。举例：

```bash
nah-evaluate-submission \
  --root . \
  --shots-a 256 \
  --shots-b 1024 \
  --out results/my_summary.json \
  --command python path/to/my_compiler.py --my-fixed-flag value
```

评测器会把 `--circuit`、`--backend` 和 `--out` 自动追加到 `--command` 后面。

## 3. 输入文件

`circuit.json` 是 Cirq JSON 线路。输入 qubit 是 `cirq.LineQubit(0)`, `cirq.LineQubit(1)` 这样的程序 qubit。

`backend.json` 是静态硬件快照，包含：

- `num_qubits`：物理 qubit 数量。
- `basis_gates`：允许输出的门集合。
- `coupling_map`：允许执行两比特门的物理边。
- `two_qubit_error`：每条 coupling edge 的两比特错误率。
- `readout_error`：每个物理 qubit 的读出错误率。
- `single_qubit_error`：全局单比特门错误率。

公开 benchmark 的 `benchmark.json` 只用于本地查看。正式评测时你的命令只会看到 `circuit.json` 和 `backend.json`。

## 4. 输出文件

假设评测器传入：

```bash
--out /tmp/run/compiled_circuit.json
```

你必须写出：

```text
/tmp/run/compiled_circuit.json
/tmp/run/compiled_circuit.layout.json
```

如果 `--out` 是 `my_result.json`，sidecar 就应该叫 `my_result.layout.json`。

### 编译线路

`compiled_circuit.json` 必须是 Cirq JSON，并且线路 qubit 是物理 `LineQubit`。例如物理 qubit 5 应该写成 `cirq.LineQubit(5)`，不是自定义名字。

### Layout sidecar

`compiled_circuit.layout.json` 必须使用下面的格式：

```json
{
  "schema_version": "1.0",
  "initial_layout": {
    "0": 5,
    "1": 8,
    "2": 9
  }
}
```

含义是：

- 输入线路的程序 qubit 0 一开始放在物理 qubit 5。
- 输入线路的程序 qubit 1 一开始放在物理 qubit 8。
- 输入线路的程序 qubit 2 一开始放在物理 qubit 9。

`initial_layout` 必须覆盖输入线路中出现的所有程序 qubit，物理 qubit 不能重复，也不能越界。

## 5. 合法性要求

输出线路会先经过结构校验：

- 只能使用后端 `basis_gates` 里允许的门。
- 所有 qubit 编号必须在物理后端范围内。
- 所有两比特门必须在 `coupling_map` 的边上。
- 最终测量必须使用 key `z`。
- 不允许中途测量、reset、feedforward 或 classically controlled operation。
- 不允许直接输出 `swap`。如果需要交换状态，请分解成合法的 `cx`。
- Track B 必须保持 Clifford-only，允许集合是 `x`, `y`, `z`, `h`, `s`, `sdg`, `cx`, `measure`。

## 6. 等价性检查

为了避免“直接准备答案”的提交，评测器会在带噪评分前做隐藏 compiler-equivalence 检查。

具体做法是：评测器根据你的 `initial_layout`，在输入线路和编译后线路前面插入相同的隐藏初态扰动，然后比较两者的无噪输出分布。如果你的线路只是针对公开样本准备一个固定答案 bitstring，而没有真正实现输入线路的逻辑变换，这一步会失败。

这一步不是为了奖励某种固定 routing 方法，而是为了保证评分对象确实是编译器。

## 7. 评分方式

单个样本：

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

命令失败、超时、输出非法、layout 缺失、等价性失败或无噪语义失败，该样本得分为 `0.0`。

噪声注入方式、后端错误率含义和优化建议见 [噪声模型说明](noise_model.md)。

## 8. 本地运行流程

生成公开数据：

```bash
nah-gen-dataset --out .
```

编译一个样本：

```bash
python examples/cirq_route_cqc_baseline/compiler.py \
  --circuit benchmarks/track_a/public/track_a_001/circuit.json \
  --backend backends/medium/medium_snapshot_a.json \
  --out results/example_track_a_001.json
```

评测整个公开集：

```bash
EXAMPLE_COMPILER="$(pwd)/examples/cirq_route_cqc_baseline/compiler.py"
nah-evaluate-submission \
  --root . \
  --shots-a 256 \
  --shots-b 1024 \
  --out results/example_public_summary.json \
  --command python "$EXAMPLE_COMPILER"
```

注意：完整评测会在临时目录隔离执行提交命令。脚本路径请使用绝对路径，或者把你的编译器安装成可通过 `python -m your_package.module` 调用的模块。

运行测试：

```bash
python -m pytest
```

## 9. Cirq baseline

仓库提供了一个最小 Cirq baseline：

- 文件：`examples/cirq_route_cqc_baseline/compiler.py`
- 方法：使用 `cirq.RouteCQC` 按后端 coupling graph 做 routing。
- 输出：Cirq JSON compiled circuit 和 layout sidecar。
- 用途：说明参赛提交的最小接口，不代表最优策略。

内置 CLI 中也有同一个 baseline：

```bash
nah-run-baseline --compiler cirq_cqc \
  --circuit benchmarks/track_a/public/track_a_001/circuit.json \
  --backend backends/medium/medium_snapshot_a.json \
  --out results/cirq_cqc_track_a_001.json
```

## 10. 常见无效原因

- 只写了 `compiled_circuit.json`，没有写 `.layout.json`。
- layout 里漏掉某个输入 qubit。
- 输出测量 key 不是 `z`。
- 使用了后端 basis 里没有的门。
- `cx` 放在不相连的物理 qubit 上。
- Track B 输出了非 Clifford 门。
- 输出线路只准备某个答案 bitstring，没有通过隐藏等价性检查。
- 命令依赖当前工作目录里的 benchmark metadata。正式评测会在临时目录中隔离运行。
