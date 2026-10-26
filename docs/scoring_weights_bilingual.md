# 分数占比说明 / Score Weighting

## 中文版

本文说明算法赛道中可量化评测部分的分数占比。最终比赛成绩还会结合创新性、结果展示、算法实用性和作品说明完整性等综合评审项；本文只说明 benchmark 自动评测部分的计分方式。

## 1. Track 占比

可量化评测分由两个 Track 加权得到：

```text
Quantitative Score = 0.75 * TrackA + 0.25 * TrackB
```

- Track A 占可量化评测分的 75%。
- Track B 占可量化评测分的 25%。

## 2. 每道题占比

每个 Track 内部的样本等权平均：

```text
TrackA = mean(success_rate over Track A samples)
TrackB = mean(success_rate over Track B samples)
```

当前公开发布包中：

| Track | Public benchmark 数量 | Track 总占比 | 每道题占可量化评测分 |
|---|---:|---:|---:|
| Track A | 8 | 75% | 9.375% |
| Track B | 2 | 25% | 12.5% |

如果把可量化评测部分单独折算为 100 分，则每道公开题的参考分值为：

- Track A 每题：`75 / 8 = 9.375` 分。
- Track B 每题：`25 / 2 = 12.5` 分。

## 3. Hidden Evaluation

正式评测会使用 hidden benchmark。Hidden benchmark 仍遵循同一接口、同一 Track 权重和同一等权平均规则。如果正式评测的 hidden 样本数量与公开样本数量不同，则每道 hidden 题的占比按下面方式计算：

```text
Track A 每题占比 = 75% / hidden Track A 题数
Track B 每题占比 = 25% / hidden Track B 题数
```

具体 hidden 样本数量和最终评分细则以赛前或评测前公布的正式说明为准。

## English Version

This document explains the score weighting for the quantitative benchmark component of the algorithm track. The final competition score may also include holistic review criteria such as innovation, result presentation, algorithmic practicality, and completeness of the report. This document only describes the automatic benchmark evaluation component.

## 1. Track Weights

The quantitative evaluation score is computed from two weighted tracks:

```text
Quantitative Score = 0.75 * TrackA + 0.25 * TrackB
```

- Track A contributes 75% of the quantitative score.
- Track B contributes 25% of the quantitative score.

## 2. Per-Problem Weights

Samples within each track are averaged with equal weight:

```text
TrackA = mean(success_rate over Track A samples)
TrackB = mean(success_rate over Track B samples)
```

In the current public release package:

| Track | Number of public benchmarks | Track weight | Per-problem weight in the quantitative score |
|---|---:|---:|---:|
| Track A | 8 | 75% | 9.375% |
| Track B | 2 | 25% | 12.5% |

If the quantitative component is converted to a 100-point scale, the reference value of each public problem is:

- Track A: `75 / 8 = 9.375` points per problem.
- Track B: `25 / 2 = 12.5` points per problem.

## 3. Hidden Evaluation

The official evaluation will use hidden benchmarks. Hidden benchmarks follow the same interface, the same track weights, and the same equal-weight averaging rule within each track. If the hidden evaluation uses a different number of samples from the public release, the per-hidden-problem weight is computed as:

```text
Track A per-problem weight = 75% / number of hidden Track A problems
Track B per-problem weight = 25% / number of hidden Track B problems
```

The exact number of hidden samples and final scoring rubric will follow the official announcement before the final evaluation.
