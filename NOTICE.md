# Provenance / 内容来源说明

This repository bundles two separately-authored parts, both under the MIT license.
本仓库包含两部分内容,均采用 MIT 许可。

## Original work — `submission/`

Authored by the repository owner as the competition entry for the
**CCF 2026 Noise-Adaptive Quantum Compilation Challenge** (algorithm track, 2nd place):

- `submission/compiler.py` — the submitted black-box compiler
- `submission/scripts/` — batch compilation, evaluation, analysis and regression scripts
- `submission/docs/` — method write-up and figures
- `submission/results/` — evaluation outputs produced by the harness below
- `README.md`, `README_zh.md`, `run_checks.bat`

本仓库所有者为参赛而编写的原创内容,对应上述文件。

## Redistributed competition harness — repository root

The files below are the official competition release package, redistributed verbatim under its
own MIT license, **Copyright (c) 2026 SpinQ Technology**:

- `src/noise_adaptive_hackathon/` — evaluator, noise simulators, baseline compilers, CLI entry points
- `benchmarks/` — public Track A / Track B benchmark circuits
- `backends/` — device snapshots (small 7q / medium 16q / large 32q)
- `docs/`, `examples/`, `formats/`, `tests/`, `pyproject.toml`, `THIRD_PARTY_NOTICES.md`

They are bundled so that the reported scores can be reproduced with a single command after
cloning. No modifications have been made to any of these files. The original license text is
retained in `LICENSE`.

以上为赛事官方发布包,依其自身 MIT 许可原样转发(版权归 SpinQ Technology),**未作任何修改**,
随仓库附带的目的是让使用者 clone 之后一条命令即可复现文中成绩。

## Third-party methods

The compiler builds on published algorithms, credited in `submission/docs/solution_zh.md`:
SABRE (Li, Ding & Xie, ASPLOS 2019), Cirq's `RouteCQC`, and RowCol / PermRowCol from the
CNOT-circuit synthesis literature. Runtime dependencies (Cirq, Stim, NetworkX, NumPy, Pydantic)
are listed in `pyproject.toml` and `THIRD_PARTY_NOTICES.md`.
