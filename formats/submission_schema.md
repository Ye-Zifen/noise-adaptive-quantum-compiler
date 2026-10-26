# 提交格式

提交会作为黑盒编译器命令被评测。

## 命令接口

```bash
your-compiler \
  --circuit path/to/circuit.json \
  --backend path/to/backend.json \
  --out path/to/compiled_circuit.json
```

`--command` 中可以包含你自己的固定参数。评测器会把 `--circuit`、`--backend` 和 `--out` 追加到命令末尾。

## 输入文件

- `circuit.json`：Cirq JSON 输入程序线路。
- `backend.json`：比赛后端快照。

正式评测时不会把 `benchmark.json` 放到同一个工作目录里。不要依赖 benchmark metadata 或硬编码样本路径。

## 输出文件

必须写出两个文件：

- `compiled_circuit.json`：Cirq JSON 编译后线路，使用物理 `LineQubit`。
- `compiled_circuit.layout.json`：required sidecar，描述每个程序 qubit 的初始物理位置。

如果 `--out` 是 `foo.json`，sidecar 文件名应该是 `foo.layout.json`。

## Layout sidecar

格式：

```json
{
  "schema_version": "1.0",
  "initial_layout": {
    "0": 5,
    "1": 8
  }
}
```

要求：

- `schema_version` 必须是 `"1.0"`。
- `initial_layout` 的 key 是输入程序 qubit 编号。
- `initial_layout` 的 value 是物理 qubit 编号。
- 必须覆盖输入线路中出现的所有程序 qubit。
- 物理 qubit 不能重复，不能越界。

## 编译线路校验规则

- 只能使用 backend `basis_gates` 中的门。
- 不能使用 `swap`，需要移动时请分解成合法 `cx`。
- 两比特门必须满足 coupling map。
- 测量必须是最终测量，key 必须是 `z`。
- 不允许中途测量、reset、feedforward 和 classically controlled operation。
- Track B 输出必须保持在 Stim 支持的 Clifford 子集。

## 等价性规则

带噪评分前，评测器会用 `initial_layout` 在源线路和编译后线路前插入隐藏无噪挑战态，并比较输出分布。编译后线路必须和源线路实现同一个逻辑变换，而不仅仅是在公开输入上给出正确答案。

命令失败、超时、输出缺失、sidecar 缺失或非法、结构校验失败、等价性检查失败、无噪语义检查失败，都会让对应 benchmark 得分为 `0.0`。
