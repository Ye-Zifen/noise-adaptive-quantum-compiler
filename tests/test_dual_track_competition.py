from __future__ import annotations

from pathlib import Path

import cirq
import pytest

from noise_adaptive_hackathon.baseline.cirq_cqc import CirqCQCCompiler
from noise_adaptive_hackathon.baseline.movement_aware import MovementAwareCompiler
from noise_adaptive_hackathon.baseline.paper_greedy import PaperGreedyEdgeCompiler, PaperGreedyVertexCompiler
from noise_adaptive_hackathon.baseline.reliability_greedy import ReliabilityGreedyCompiler
from noise_adaptive_hackathon.baseline.vanilla import VanillaCompiler
from noise_adaptive_hackathon.benchmarks.track_a import TRACK_A_FAMILIES, generate_track_a_benchmark
from noise_adaptive_hackathon.benchmarks.track_b import generate_track_b_benchmark
from noise_adaptive_hackathon.evaluator.score_submission import score_submission
from noise_adaptive_hackathon.evaluator.validate_circuit import validate_compiled_circuit
from noise_adaptive_hackathon.formats.backend import CompetitionBackend, TRACK_A_BASIS
from noise_adaptive_hackathon.simulator.cirq_runner import run_track_a
from noise_adaptive_hackathon.simulator.stim_runner import run_track_b


def demo_backend() -> CompetitionBackend:
    coupling_map = [(row * 4 + col, row * 4 + col + 1) for row in range(4) for col in range(3)]
    coupling_map += [(row * 4 + col, (row + 1) * 4 + col) for row in range(3) for col in range(4)]
    return CompetitionBackend.parse_obj(
        {
            "schema_version": "2.0",
            "snapshot_id": "medium_snapshot_a",
            "size_class": "medium",
            "num_qubits": 16,
            "basis_gates": list(TRACK_A_BASIS),
            "coupling_map": coupling_map,
            "two_qubit_error": {f"{left}-{right}": 0.012 + 0.001 * (index % 5) for index, (left, right) in enumerate(coupling_map)},
            "readout_error": {str(index): 0.008 + 0.001 * (index % 6) for index in range(16)},
            "single_qubit_error": 0.001,
        }
    )


def test_backend_rejects_swap_basis() -> None:
    payload = demo_backend().dict()
    payload["basis_gates"] = [*payload["basis_gates"], "swap"]
    with pytest.raises(Exception):
        CompetitionBackend.parse_obj(payload)


@pytest.mark.parametrize("family", TRACK_A_FAMILIES)
def test_track_a_functional_benchmarks_are_noiseless_correct(family: str) -> None:
    benchmark = generate_track_a_benchmark(family=family, logical_qubits=6 if family != "structured_random" else 7, seed=31)
    result = cirq.Simulator(seed=5).run(benchmark.circuit, repetitions=16)

    assert family != "qft"
    assert benchmark.expected_output_rule.rule_type == "bitstring"
    assert all(benchmark.expected_output_rule.is_correct("".join(str(bit) for bit in row)) for row in result.measurements["z"])


def test_track_b_parity_benchmark_uses_parity_checks() -> None:
    benchmark = generate_track_b_benchmark(num_qubits=12, depth=14, seed=7, family="parity")
    result = cirq.Simulator(seed=11).run(benchmark.circuit, repetitions=32)

    assert benchmark.expected_output_rule.rule_type == "parity_checks"
    assert benchmark.expected_output_rule.parity_checks
    assert all(benchmark.expected_output_rule.is_correct("".join(str(bit) for bit in row)) for row in result.measurements["z"])


@pytest.mark.parametrize(
    "compiler_factory",
    [
        VanillaCompiler,
        MovementAwareCompiler,
        ReliabilityGreedyCompiler,
        CirqCQCCompiler,
        PaperGreedyVertexCompiler,
        PaperGreedyEdgeCompiler,
    ],
)
def test_baselines_compile_valid_no_swap_outputs(compiler_factory) -> None:
    backend = demo_backend()
    compiler = compiler_factory()
    track_a = generate_track_a_benchmark(family="adder", logical_qubits=6, seed=3)
    track_b = generate_track_b_benchmark(num_qubits=12, depth=12, seed=5, family="parity")

    compiled_a = compiler.compile(track_a.circuit, backend, seed=13)
    compiled_b = compiler.compile(track_b.circuit, backend, seed=13)

    assert all(not isinstance(op.gate, cirq.SwapPowGate) for op in compiled_a.all_operations())
    assert all(not isinstance(op.gate, cirq.SwapPowGate) for op in compiled_b.all_operations())
    assert validate_compiled_circuit(compiled_a, backend, "track_a").valid
    assert validate_compiled_circuit(compiled_b, backend, "track_b").valid


def test_track_runners_produce_measurement_based_scores() -> None:
    backend = demo_backend()
    compiler = ReliabilityGreedyCompiler()
    track_a = generate_track_a_benchmark(family="hs", logical_qubits=6, seed=17)
    track_b = generate_track_b_benchmark(num_qubits=12, depth=10, seed=19, family="ghz")

    result_a = run_track_a(track_a, compiler.compile(track_a.circuit, backend, seed=23), backend, shots=32, seed=29)
    result_b = run_track_b(track_b, compiler.compile(track_b.circuit, backend, seed=23), backend, shots=64, seed=29)

    assert 0.0 <= result_a.success_rate <= 1.0
    assert 0.0 <= result_b.success_rate <= 1.0
    assert result_a.total_shots == 32
    assert result_b.total_shots == 64


def test_score_submission_blends_tracks() -> None:
    final = score_submission(track_a_score=0.8, track_b_score=0.4)
    assert final.track_a_weight == pytest.approx(0.75)
    assert final.track_b_weight == pytest.approx(0.25)
    assert final.final_score == pytest.approx(0.7)
