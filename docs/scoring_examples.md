# 评分示例

评测器输出的是 JSON summary。下面是字段含义和一个缩略示例。

每个 Track 内部样本等权平均；当前公开发布包中 Track A 有 8 道 public benchmark，Track B 有 2 道 public benchmark。可量化评测部分按 `0.75 * TrackA + 0.25 * TrackB` 加权，因此折算为 100 分时，Track A 每道公开题为 9.375 分，Track B 每道公开题为 12.5 分。中英文说明见 [分数占比说明 / Score Weighting](scoring_weights_bilingual.md)。

## 单个样本结果

```json
{
  "benchmark_name": "track_a_001",
  "track": "track_a",
  "success_rate": 0.78125,
  "valid": true,
  "shots": 256,
  "correct_shots": 200,
  "depth": 42,
  "two_qubit_gate_count": 18,
  "estimated_log_reliability": -0.47,
  "compile_time_sec": 0.012,
  "validation_errors": []
}
```

重要字段：

- `success_rate`：该样本的主分数，等于 `correct_shots / shots`。
- `valid`：结构校验、layout 校验、等价性检查和无噪语义检查是否全部通过。
- `validation_errors`：无效样本的错误原因。
- `depth`、`two_qubit_gate_count`、`estimated_log_reliability`：调试指标，不直接进入总分。

## 总结结果

```json
{
  "compiler_name": "submission",
  "split": "public",
  "track_a_score": 0.74,
  "track_b_score": 0.88,
  "final_score": 0.775,
  "sample_results": ["..."]
}
```

总分计算：

```text
Final Score = 0.75 * track_a_score + 0.25 * track_b_score
```

例如：

```text
0.75 * 0.74 + 0.25 * 0.88 = 0.775
```

## 无效样本

下面这些情况会让对应样本 `success_rate = 0.0`：

- 编译命令非零退出或超时。
- 没有写输出文件。
- 输出文件不是合法 Cirq JSON。
- 没有写 layout sidecar，或 sidecar schema 不合法。
- 输出门不在 backend basis 中。
- 两比特门不满足 coupling map。
- Track B 输出非 Clifford 门。
- 隐藏 compiler-equivalence 检查失败。
- 无噪语义检查失败。

无效只影响对应样本，不会直接让整个评测中断。
