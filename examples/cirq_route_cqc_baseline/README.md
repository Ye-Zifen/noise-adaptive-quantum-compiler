# Cirq RouteCQC baseline 示例

这个目录给出一个最小可提交 baseline。它的目标是展示参赛接口和输出格式，不代表最优策略。

## 方法

`compiler.py` 做三件事：

1. 读取 `--circuit` 指向的 Cirq JSON 输入线路。
2. 读取 `--backend` 指向的后端快照，用 `coupling_map` 构造 Cirq routing graph。
3. 调用 `cirq.RouteCQC(...).route_circuit(...)` 做 routing，然后写出编译线路和 layout sidecar。

如果 Cirq routing 产生 `SWAP`，示例会把它分解成三个 `CX`，因为公开后端 basis 不允许直接输出 `swap`。

## 编译一个样本

在仓库根目录运行：

```bash
python examples/cirq_route_cqc_baseline/compiler.py \
  --circuit benchmarks/track_a/public/track_a_001/circuit.json \
  --backend backends/medium/medium_snapshot_a.json \
  --out results/example_cirq_track_a_001.json
```

输出文件：

```text
results/example_cirq_track_a_001.json
results/example_cirq_track_a_001.layout.json
```

## 评测整个公开集

```bash
EXAMPLE_COMPILER="$(pwd)/examples/cirq_route_cqc_baseline/compiler.py"
nah-evaluate-submission \
  --root . \
  --shots-a 256 \
  --shots-b 1024 \
  --out results/example_cirq_public_summary.json \
  --command python "$EXAMPLE_COMPILER"
```

`public_summary.json` 是本仓库中用这个示例跑过一次公开集得到的参考输出。由于评分使用采样，shot 数和 seed 改变时分数会有小幅波动。

这里使用绝对路径是有意的：评测器会在临时目录中执行提交命令，不能依赖当前 shell 的相对路径。

## 参赛者可以从这里改什么

- 改 layout 选择：优先选择读出错误率低、两比特错误率低的位置。
- 改 routing：减少长路径移动和额外 `cx`。
- 改 gate decomposition：保证仍然满足后端 basis 和 Track B Clifford 限制。
- 保持输出接口不变：必须写 compiled circuit 和 layout sidecar。
