#!/usr/bin/env bash
# 在双赛道公开 benchmark 上完整评测本提交编译器，并把 summary JSON 写到 submission/results/。
# 用法（在发布包根目录运行）：
#   bash submission/scripts/run_public_eval.sh
set -euo pipefail

# 切到仓库根目录（本脚本位于 submission/scripts/ 下两级）。
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT"

export PYTHONPATH="${PYTHONPATH:-}:$ROOT/src"
RESULTS="$SCRIPT_DIR/../results"
COMP="$SCRIPT_DIR/../compiler.py"

# 选择 Python 解释器（优先 3.11+；若只有 3.10 也能运行，仅 pyproject 版本门限不满足）。
PY="${PYTHON:-$( [ -x "$ROOT/.venv/bin/python" ] && echo "$ROOT/.venv/bin/python" || command -v python )}"

echo "[1/3] 评测本提交编译器 ..."
"$PY" -m noise_adaptive_hackathon.cli.evaluate_submission \
  --root . --shots-a 256 --shots-b 1024 --seed 7 \
  --out "$RESULTS/public_summary.json" \
  --command "$PY" "$COMP"

echo "[2/3] 评测 RouteCQC baseline（对比基线）..."
"$PY" -m noise_adaptive_hackathon.cli.evaluate_submission \
  --root . --shots-a 256 --shots-b 1024 --seed 7 \
  --out "$RESULTS/baseline_cqc_summary.json" \
  --command "$PY" -m noise_adaptive_hackathon.cli.run_baseline --compiler cirq_cqc

echo "[3/3] 评测 reliability_greedy baseline（对比基线）..."
"$PY" -m noise_adaptive_hackathon.cli.evaluate_submission \
  --root . --shots-a 256 --shots-b 1024 --seed 7 \
  --out "$RESULTS/reliability_greedy_summary.json" \
  --command "$PY" -m noise_adaptive_hackathon.cli.run_baseline --compiler reliability_greedy

echo "完成。summary 写入 $RESULTS"
