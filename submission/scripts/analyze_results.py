"""Aggregate evaluation summaries into a comparison table and figures.

Reads the summary JSONs in ``submission/results/`` and writes:
  * ``submission/results/comparison_table.csv``
  * ``submission/docs/figures/success_rate_by_sample.png``
  * ``submission/docs/figures/track_and_final_scores.png``

Run from the release-bundle root:
    python submission/scripts/analyze_results.py
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

# Use a CJK-capable font so Chinese labels render in the figures.
for candidate in (
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
):
    if Path(candidate).exists():
        font_manager.fontManager.addfont(candidate)
        matplotlib.rcParams["font.family"] = font_manager.FontProperties(fname=candidate).get_name()
        break
matplotlib.rcParams["axes.unicode_minus"] = False

RESULTS = Path(__file__).resolve().parents[1] / "results"
FIGS = Path(__file__).resolve().parents[1] / "docs" / "figures"

SUMMARIES = {
    "本提交": RESULTS / "public_summary.json",
    "RouteCQC baseline": RESULTS / "baseline_cqc_summary.json",
    "reliability_greedy": RESULTS / "reliability_greedy_summary.json",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    data = {name: load(p) for name, p in SUMMARIES.items() if p.exists()}
    if "本提交" not in data:
        raise SystemExit("missing public_summary.json; run run_public_eval.sh first")

    sample_names = [s["benchmark_name"] for s in data["本提交"]["sample_results"]]

    # ---- comparison CSV ----
    csv_path = RESULTS / "comparison_table.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        header = ["benchmark"] + [f"{n} success_rate" for n in data] + ["本提交 2q_gates"]
        writer.writerow(header)
        sub_by_name = {s["benchmark_name"]: s for s in data["本提交"]["sample_results"]}
        per_name = {
            name: {s["benchmark_name"]: s for s in d["sample_results"]} for name, d in data.items()
        }
        for bn in sample_names:
            row = [bn] + [round(per_name[name][bn]["success_rate"], 4) for name in data]
            row.append(sub_by_name[bn]["two_qubit_gate_count"])
            writer.writerow(row)
        writer.writerow([])
        for key in ("track_a_score", "track_b_score", "final_score"):
            writer.writerow([key] + [round(data[name][key], 4) for name in data])
    print(f"wrote {csv_path}")

    # ---- per-sample success-rate bar chart ----
    FIGS.mkdir(parents=True, exist_ok=True)
    x = range(len(sample_names))
    width = 0.8 / len(data)
    fig, ax = plt.subplots(figsize=(11, 5))
    for i, (name, d) in enumerate(data.items()):
        by = {s["benchmark_name"]: s["success_rate"] for s in d["sample_results"]}
        ax.bar([xi + i * width for xi in x], [by[n] for n in sample_names], width, label=name)
    ax.set_xticks([xi + width * (len(data) - 1) / 2 for xi in x])
    ax.set_xticklabels(sample_names, rotation=45, ha="right")
    ax.set_ylabel("success_rate")
    ax.set_title("公开集各样本成功率对比")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIGS / "success_rate_by_sample.png", dpi=150)
    plt.close(fig)
    print(f"wrote {FIGS / 'success_rate_by_sample.png'}")

    # ---- track / final score chart ----
    metrics = ["track_a_score", "track_b_score", "final_score"]
    labels = ["Track A", "Track B", "Final"]
    fig, ax = plt.subplots(figsize=(8, 5))
    width = 0.8 / len(data)
    for i, (name, d) in enumerate(data.items()):
        ax.bar([j + i * width for j in range(len(metrics))], [d[m] for m in metrics], width, label=name)
    ax.set_xticks([j + width * (len(data) - 1) / 2 for j in range(len(metrics))])
    ax.set_xticklabels(labels)
    ax.set_ylabel("score")
    ax.set_title("赛道分数与总分对比")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    for i, (name, d) in enumerate(data.items()):
        for j, m in enumerate(metrics):
            ax.text(j + i * width, d[m] + 0.01, f"{d[m]:.3f}", ha="center", va="bottom", fontsize=7)
    fig.tight_layout()
    fig.savefig(FIGS / "track_and_final_scores.png", dpi=150)
    plt.close(fig)
    print(f"wrote {FIGS / 'track_and_final_scores.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
