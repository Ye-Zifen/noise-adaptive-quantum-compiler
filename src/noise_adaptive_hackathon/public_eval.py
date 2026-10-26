from __future__ import annotations

from pathlib import Path

from noise_adaptive_hackathon.baseline.cirq_cqc import CirqCQCCompiler
from noise_adaptive_hackathon.baseline.movement_aware import MovementAwareCompiler
from noise_adaptive_hackathon.baseline.paper_greedy import PaperGreedyEdgeCompiler, PaperGreedyVertexCompiler
from noise_adaptive_hackathon.baseline.reliability_greedy import ReliabilityGreedyCompiler
from noise_adaptive_hackathon.baseline.vanilla import VanillaCompiler
from noise_adaptive_hackathon.benchmarks.io import load_benchmark
from noise_adaptive_hackathon.evaluator.score_submission import score_submission
from noise_adaptive_hackathon.formats.backend import CompetitionBackend
from noise_adaptive_hackathon.simulator.cirq_runner import run_track_a
from noise_adaptive_hackathon.simulator.stim_runner import run_track_b


def run_public_eval(root: Path, shots_a: int = 128, shots_b: int = 512) -> dict[str, object]:
    track_a = [load_benchmark(path) for path in sorted((root / "benchmarks" / "track_a" / "public").iterdir()) if path.is_dir()]
    track_b = [load_benchmark(path) for path in sorted((root / "benchmarks" / "track_b" / "public").iterdir()) if path.is_dir()]

    baselines = [
        VanillaCompiler(),
        MovementAwareCompiler(),
        ReliabilityGreedyCompiler(),
        CirqCQCCompiler(),
        PaperGreedyVertexCompiler(),
        PaperGreedyEdgeCompiler(),
    ]
    results: list[dict[str, object]] = []
    for offset, compiler in enumerate(baselines):
        track_a_score = _mean_success_rate(root, track_a, compiler, shots_a, 101 + offset, "track_a")
        track_b_score = _mean_success_rate(root, track_b, compiler, shots_b, 201 + offset, "track_b")
        total = score_submission(track_a_score=track_a_score, track_b_score=track_b_score)
        results.append(
            {
                "name": compiler.name,
                "track_a_score": track_a_score,
                "track_b_score": track_b_score,
                "final_score": total.final_score,
            }
        )

    return {
        "split": "public",
        "tracks": ["track_a", "track_b"],
        "baselines": results,
    }


def _mean_success_rate(root, benchmarks, compiler, shots, seed, track):
    rates: list[float] = []
    for index, benchmark in enumerate(benchmarks):
        backend = _load_backend_for_benchmark(root, benchmark)
        compiled = compiler.compile(benchmark.circuit, backend, seed=seed + index)
        if track == "track_a":
            result = run_track_a(benchmark, compiled, backend, shots=shots, seed=seed + index)
        else:
            result = run_track_b(benchmark, compiled, backend, shots=shots, seed=seed + index)
        rates.append(result.success_rate)
    return sum(rates) / len(rates)


def _load_backend_for_benchmark(root: Path, benchmark) -> CompetitionBackend:
    size_class = benchmark.metadata.get("backend_size_class", "medium")
    snapshot_id = benchmark.metadata.get("backend_snapshot_id", "medium_snapshot_a")
    return CompetitionBackend.parse_raw(
        (root / "backends" / size_class / f"{snapshot_id}.json").read_text(encoding="utf-8")
    )
