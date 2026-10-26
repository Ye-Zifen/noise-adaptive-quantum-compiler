from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import cirq

from noise_adaptive_hackathon.benchmarks.io import load_benchmark
from noise_adaptive_hackathon.evaluator.equivalence import (
    EquivalenceValidation,
    load_layout_sidecar,
    validate_compiler_equivalence,
)
from noise_adaptive_hackathon.evaluator.score_submission import score_submission
from noise_adaptive_hackathon.evaluator.validate_circuit import (
    count_two_qubit_gates,
    estimate_log_reliability,
    validate_compiled_circuit,
)
from noise_adaptive_hackathon.formats.backend import CompetitionBackend
from noise_adaptive_hackathon.simulator.cirq_runner import run_track_a
from noise_adaptive_hackathon.simulator.stim_runner import run_track_b

MAX_OUTPUT_BYTES = 2_000_000
SEMANTIC_CHECK_SHOTS = 64
MAX_CAPTURED_OUTPUT_CHARS = 2_000


@dataclass(frozen=True)
class SubmissionSampleResult:
    benchmark_name: str
    track: str
    success_rate: float
    valid: bool
    shots: int
    correct_shots: int
    depth: int
    two_qubit_gate_count: int
    estimated_log_reliability: float
    compile_time_sec: float
    validation_errors: list[str]


@dataclass(frozen=True)
class SubmissionEvaluationSummary:
    compiler_name: str
    split: str
    track_a_score: float
    track_b_score: float
    final_score: float
    sample_results: list[SubmissionSampleResult]


def evaluate_submission_command(
    root: Path,
    command: list[str],
    shots_a: int,
    shots_b: int,
    seed: int,
    timeout_sec: int,
) -> SubmissionEvaluationSummary:
    split = "public"
    track_a_benchmarks = _load_benchmarks(root / "benchmarks" / "track_a" / split)
    track_b_benchmarks = _load_benchmarks(root / "benchmarks" / "track_b" / split)

    track_a_results = [
        _evaluate_single_benchmark(
            root=root,
            benchmark_dir=benchmark_dir,
            command=command,
            shots=shots_a,
            seed=seed + index,
            timeout_sec=timeout_sec,
        )
        for index, benchmark_dir in enumerate(track_a_benchmarks)
    ]
    track_b_results = [
        _evaluate_single_benchmark(
            root=root,
            benchmark_dir=benchmark_dir,
            command=command,
            shots=shots_b,
            seed=seed + 10_000 + index,
            timeout_sec=timeout_sec,
        )
        for index, benchmark_dir in enumerate(track_b_benchmarks)
    ]

    track_a_score = _mean_success_rate(track_a_results)
    track_b_score = _mean_success_rate(track_b_results)
    total = score_submission(track_a_score=track_a_score, track_b_score=track_b_score)
    return SubmissionEvaluationSummary(
        compiler_name="submission",
        split=split,
        track_a_score=track_a_score,
        track_b_score=track_b_score,
        final_score=total.final_score,
        sample_results=track_a_results + track_b_results,
    )


def _evaluate_single_benchmark(
    root: Path,
    benchmark_dir: Path,
    command: list[str],
    shots: int,
    seed: int,
    timeout_sec: int,
) -> SubmissionSampleResult:
    benchmark = load_benchmark(benchmark_dir)
    backend_path = root / "backends" / benchmark.metadata["backend_size_class"] / f"{benchmark.metadata['backend_snapshot_id']}.json"
    backend = CompetitionBackend.parse_raw(backend_path.read_text(encoding="utf-8"))

    with tempfile.TemporaryDirectory() as temp_dir_string:
        temp_dir = Path(temp_dir_string)
        isolated_circuit = temp_dir / "circuit.json"
        isolated_backend = temp_dir / "backend.json"
        out_path = temp_dir / "compiled_circuit.json"
        shutil.copy2(benchmark_dir / "circuit.json", isolated_circuit)
        shutil.copy2(backend_path, isolated_backend)

        started = time.perf_counter()
        try:
            subprocess.run(
                command + ["--circuit", str(isolated_circuit), "--backend", str(isolated_backend), "--out", str(out_path)],
                check=True,
                timeout=timeout_sec,
                capture_output=True,
                text=True,
                cwd=temp_dir,
                env=_subprocess_env(),
            )
            compile_time = time.perf_counter() - started
            if not out_path.exists():
                return _invalid_result(benchmark.name, benchmark.track, shots, compile_time, ["compiler did not write output"])
            if out_path.stat().st_size > MAX_OUTPUT_BYTES:
                return _invalid_result(benchmark.name, benchmark.track, shots, compile_time, ["compiled circuit output is too large"])
            compiled = cirq.read_json(out_path)
            layout = load_layout_sidecar(out_path, benchmark, backend)
        except subprocess.TimeoutExpired as error:
            compile_time = time.perf_counter() - started
            return _invalid_result(
                benchmark.name,
                benchmark.track,
                shots,
                compile_time,
                _timeout_errors(error, timeout_sec),
            )
        except subprocess.CalledProcessError as error:
            compile_time = time.perf_counter() - started
            return _invalid_result(
                benchmark.name,
                benchmark.track,
                shots,
                compile_time,
                _subprocess_errors(error),
            )
        except Exception as error:
            compile_time = time.perf_counter() - started
            return _invalid_result(benchmark.name, benchmark.track, shots, compile_time, [_exception_summary(error)])

    if isinstance(layout, EquivalenceValidation):
        return _invalid_result(benchmark.name, benchmark.track, shots, compile_time, layout.errors, compiled)
    validation = validate_compiled_circuit(compiled, backend, benchmark.track)
    if not validation.valid:
        return _invalid_result(benchmark.name, benchmark.track, shots, compile_time, validation.errors, compiled)
    equivalence = validate_compiler_equivalence(benchmark, compiled, layout, seed)
    if not equivalence.valid:
        return _invalid_result(benchmark.name, benchmark.track, shots, compile_time, equivalence.errors, compiled)
    if not _passes_noiseless_semantics(benchmark, compiled, seed):
        return _invalid_result(
            benchmark.name,
            benchmark.track,
            shots,
            compile_time,
            ["noiseless semantic check failed"],
            compiled,
        )

    try:
        if benchmark.track == "track_a":
            run = run_track_a(benchmark, compiled, backend, shots=shots, seed=seed)
        else:
            run = run_track_b(benchmark, compiled, backend, shots=shots, seed=seed)
    except Exception as error:
        return _invalid_result(benchmark.name, benchmark.track, shots, compile_time, [type(error).__name__], compiled)

    return SubmissionSampleResult(
        benchmark_name=benchmark.name,
        track=benchmark.track,
        success_rate=run.success_rate,
        valid=True,
        shots=run.total_shots,
        correct_shots=run.correct_shots,
        depth=len(compiled),
        two_qubit_gate_count=count_two_qubit_gates(compiled),
        estimated_log_reliability=estimate_log_reliability(compiled, backend),
        compile_time_sec=compile_time,
        validation_errors=[],
    )


def _passes_noiseless_semantics(benchmark, compiled: cirq.Circuit, seed: int) -> bool:
    try:
        result = cirq.Simulator(seed=seed).run(compiled, repetitions=SEMANTIC_CHECK_SHOTS)
        samples = result.measurements["z"]
    except Exception:
        return False
    return all(benchmark.expected_output_rule.is_correct("".join(str(bit) for bit in row)) for row in samples)


def _invalid_result(
    benchmark_name: str,
    track: str,
    shots: int,
    compile_time: float,
    errors: list[str],
    circuit: cirq.Circuit | None = None,
) -> SubmissionSampleResult:
    return SubmissionSampleResult(
        benchmark_name=benchmark_name,
        track=track,
        success_rate=0.0,
        valid=False,
        shots=shots,
        correct_shots=0,
        depth=len(circuit) if circuit is not None else 0,
        two_qubit_gate_count=count_two_qubit_gates(circuit) if circuit is not None else 0,
        estimated_log_reliability=0.0,
        compile_time_sec=compile_time,
        validation_errors=errors,
    )


def _subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    src_root = str(Path(__file__).resolve().parents[2])
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = src_root if not existing else f"{src_root}{os.pathsep}{existing}"
    return env


def _subprocess_errors(error: subprocess.CalledProcessError) -> list[str]:
    errors = [f"compiler exited with status {error.returncode}"]
    errors.extend(_captured_output_errors(stdout=error.stdout, stderr=error.stderr))
    return errors


def _timeout_errors(error: subprocess.TimeoutExpired, timeout_sec: int) -> list[str]:
    errors = [f"compiler timed out after {timeout_sec} seconds"]
    errors.extend(_captured_output_errors(stdout=error.stdout, stderr=error.stderr))
    return errors


def _captured_output_errors(stdout: str | bytes | None, stderr: str | bytes | None) -> list[str]:
    errors: list[str] = []
    for label, value in (("stdout", stdout), ("stderr", stderr)):
        snippet = _captured_output_snippet(value)
        if snippet:
            errors.append(f"{label}: {snippet}")
    return errors


def _captured_output_snippet(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    normalized = " ".join(line.strip() for line in value.splitlines() if line.strip())
    if len(normalized) > MAX_CAPTURED_OUTPUT_CHARS:
        return normalized[:MAX_CAPTURED_OUTPUT_CHARS] + "...[truncated]"
    return normalized


def _exception_summary(error: Exception) -> str:
    message = str(error).strip()
    if not message:
        return type(error).__name__
    return f"{type(error).__name__}: {_captured_output_snippet(message)}"


def _load_benchmarks(directory: Path) -> list[Path]:
    return sorted(path for path in directory.iterdir() if path.is_dir())


def _mean_success_rate(results: list[SubmissionSampleResult]) -> float:
    if not results:
        return 0.0
    return sum(result.success_rate for result in results) / len(results)
