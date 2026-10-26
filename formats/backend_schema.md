# 后端格式

比赛后端是静态 JSON 快照，schema version 为 `2.0`。

## 必需字段

```json
{
  "schema_version": "2.0",
  "snapshot_id": "medium_snapshot_a",
  "size_class": "medium",
  "num_qubits": 16,
  "basis_gates": ["x", "y", "z", "h", "s", "sdg", "t", "tdg", "rx", "ry", "rz", "cx", "measure"],
  "coupling_map": [[0, 1], [1, 2]],
  "two_qubit_error": {
    "0-1": 0.015,
    "1-2": 0.017
  },
  "readout_error": {
    "0": 0.008,
    "1": 0.009,
    "2": 0.010
  },
  "single_qubit_error": 0.001
}
```

## 字段含义

- `schema_version`：当前公开版本为 `2.0`。
- `snapshot_id`：后端快照 ID。
- `size_class`：后端规模，公开数据中包括 `small`、`medium`、`large`。
- `num_qubits`：物理 qubit 数量。
- `basis_gates`：提交线路允许使用的门。`swap` 不在 v1 basis 中。
- `coupling_map`：允许执行两比特门的无向物理边。
- `two_qubit_error`：每条 coupling edge 的两比特 depolarizing error 概率。
- `readout_error`：每个物理 qubit 的测量 bit-flip 概率。
- `single_qubit_error`：所有单比特门共享的 depolarizing error 概率。

`readout_error` 必须覆盖每个物理 qubit。`two_qubit_error` 必须覆盖每条 coupling edge。
