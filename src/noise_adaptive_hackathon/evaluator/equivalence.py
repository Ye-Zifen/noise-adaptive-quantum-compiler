from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from random import Random

import cirq

from noise_adaptive_hackathon.benchmarks.model import CompetitionBenchmark
from noise_adaptive_hackathon.formats.backend import CompetitionBackend

EQUIVALENCE_CHECK_CHALLENGES = 4
EQUIVALENCE_CHECK_SHOTS_A = 128
EQUIVALENCE_CHECK_SHOTS_B = 512
EQUIVALENCE_TV_THRESHOLD_A = 0.35
EQUIVALENCE_TV_THRESHOLD_B = 0.35


@dataclass(frozen=True)
class LayoutSidecar:
    initial_layout: dict[int, int]


@dataclass(frozen=True)
class EquivalenceValidation:
    valid: bool
    errors: list[str]


def layout_sidecar_path(out_path: Path) -> Path:
    return out_path.with_name(f"{out_path.stem}.layout.json")


def write_layout_sidecar(out_path: Path, initial_layout: dict[cirq.LineQubit | int, int]) -> None:
    normalized = {
        str(_program_qubit_id(program)): int(physical)
        for program, physical in initial_layout.items()
    }
    layout_sidecar_path(out_path).write_text(
        json.dumps({"schema_version": "1.0", "initial_layout": normalized}, indent=2),
        encoding="utf-8",
    )


def load_layout_sidecar(
    out_path: Path,
    benchmark: CompetitionBenchmark,
    backend: CompetitionBackend,
) -> LayoutSidecar | EquivalenceValidation:
    path = layout_sidecar_path(out_path)
    if not path.exists():
        return EquivalenceValidation(
            valid=False,
            errors=[f"compiler must write layout sidecar {path.name}"],
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as error:
        return EquivalenceValidation(valid=False, errors=[f"layout sidecar is not valid JSON: {type(error).__name__}"])
    if payload.get("schema_version") != "1.0":
        return EquivalenceValidation(valid=False, errors=["layout sidecar schema_version must be 1.0"])
    raw_layout = payload.get("initial_layout")
    if not isinstance(raw_layout, dict):
        return EquivalenceValidation(valid=False, errors=["layout sidecar initial_layout must be an object"])

    program_ids = [qubit.x for qubit in benchmark.logical_qubits]
    layout: dict[int, int] = {}
    errors: list[str] = []
    for program_id in program_ids:
        key = str(program_id)
        if key not in raw_layout:
            errors.append(f"initial_layout missing program qubit {program_id}")
            continue
        physical = raw_layout[key]
        if not isinstance(physical, int):
            errors.append(f"initial_layout[{program_id}] must be an integer physical qubit")
            continue
        if physical < 0 or physical >= backend.num_qubits:
            errors.append(f"initial_layout[{program_id}] physical qubit {physical} outside backend range")
            continue
        layout[program_id] = physical
    if len(set(layout.values())) != len(layout):
        errors.append("initial_layout physical qubits must be unique")
    if errors:
        return EquivalenceValidation(valid=False, errors=errors)
    return LayoutSidecar(initial_layout=layout)


def validate_compiler_equivalence(
    benchmark: CompetitionBenchmark,
    compiled: cirq.Circuit,
    layout: LayoutSidecar,
    seed: int,
    challenges: int = EQUIVALENCE_CHECK_CHALLENGES,
) -> EquivalenceValidation:
    measured_qubits = _compiled_measurement_qubits(compiled)
    if measured_qubits is None:
        return EquivalenceValidation(valid=False, errors=["compiled circuit must have one final z measurement"])
    if len(measured_qubits) != len(benchmark.logical_qubits):
        return EquivalenceValidation(
            valid=False,
            errors=[
                "compiled final measurement width must match program circuit width "
                f"({len(measured_qubits)} != {len(benchmark.logical_qubits)})"
            ],
        )

    patterns = _challenge_patterns(len(benchmark.logical_qubits), seed, challenges, benchmark.track)
    shots = EQUIVALENCE_CHECK_SHOTS_A if benchmark.track == "track_a" else EQUIVALENCE_CHECK_SHOTS_B
    threshold = EQUIVALENCE_TV_THRESHOLD_A if benchmark.track == "track_a" else EQUIVALENCE_TV_THRESHOLD_B
    for index, pattern in enumerate(patterns):
        source = _with_logical_challenge(benchmark.circuit, benchmark.logical_qubits, pattern)
        challenged_compiled = _with_physical_challenge(compiled, benchmark.logical_qubits, layout.initial_layout, pattern)
        try:
            if benchmark.track == "track_a":
                source_hist = _exact_histogram(source)
                compiled_hist = _exact_histogram(challenged_compiled)
            else:
                source_hist = _sample_histogram(source, shots=shots, seed=seed + 97 * index)
                compiled_hist = _sample_histogram(challenged_compiled, shots=shots, seed=seed + 97 * index)
        except Exception as error:
            return EquivalenceValidation(valid=False, errors=[f"compiler equivalence simulation failed: {type(error).__name__}"])
        distance = _total_variation(source_hist, compiled_hist)
        if distance > threshold:
            return EquivalenceValidation(
                valid=False,
                errors=[
                    "compiler equivalence check failed "
                    f"(challenge={index}, total_variation={distance:.3f}, threshold={threshold:.3f})"
                ],
            )
    return EquivalenceValidation(valid=True, errors=[])


def _program_qubit_id(program: cirq.LineQubit | int) -> int:
    if isinstance(program, cirq.LineQubit):
        return program.x
    return int(program)


def _compiled_measurement_qubits(circuit: cirq.Circuit) -> tuple[cirq.LineQubit, ...] | None:
    measurements = [op for op in circuit.all_operations() if isinstance(op.gate, cirq.MeasurementGate)]
    if len(measurements) != 1:
        return None
    if cirq.measurement_key_name(measurements[0]) != "z":
        return None
    return tuple(measurements[0].qubits)


def _challenge_patterns(width: int, seed: int, count: int, track: str) -> list[tuple[str, ...]]:
    rng = Random(seed)
    patterns: list[tuple[str, ...]] = []
    if width:
        patterns.append(tuple("x" if index == 0 else "i" for index in range(width)))
    if width > 1:
        second = "x" if track == "track_b" else "h"
        patterns.append(tuple(second if index == width - 1 else "i" for index in range(width)))
    choices = ("i", "x") if track == "track_b" else ("i", "x", "h", "xh")
    while len(patterns) < count:
        pattern = tuple(rng.choice(choices) for _ in range(width))
        if any(entry != "i" for entry in pattern) and pattern not in patterns:
            patterns.append(pattern)
    return patterns[:count]


def _with_logical_challenge(
    circuit: cirq.Circuit,
    logical_qubits: tuple[cirq.LineQubit, ...],
    pattern: tuple[str, ...],
) -> cirq.Circuit:
    challenged = cirq.Circuit()
    for qubit, entry in zip(logical_qubits, pattern):
        challenged.append(_prep_ops(qubit, entry))
    challenged += circuit
    return challenged


def _with_physical_challenge(
    circuit: cirq.Circuit,
    logical_qubits: tuple[cirq.LineQubit, ...],
    initial_layout: dict[int, int],
    pattern: tuple[str, ...],
) -> cirq.Circuit:
    challenged = cirq.Circuit()
    for logical, entry in zip(logical_qubits, pattern):
        challenged.append(_prep_ops(cirq.LineQubit(initial_layout[logical.x]), entry))
    challenged += circuit
    return challenged


def _prep_ops(qubit: cirq.LineQubit, entry: str) -> tuple[cirq.Operation, ...]:
    if entry == "i":
        return ()
    if entry == "x":
        return (cirq.X(qubit),)
    if entry == "h":
        return (cirq.H(qubit),)
    if entry == "xh":
        return (cirq.X(qubit), cirq.H(qubit))
    raise ValueError(f"unsupported challenge entry: {entry}")


def _sample_histogram(circuit: cirq.Circuit, shots: int, seed: int) -> dict[str, int]:
    simulator = cirq.CliffordSimulator(seed=seed) if _is_clifford_circuit(circuit) else cirq.Simulator(seed=seed)
    result = simulator.run(circuit, repetitions=shots)
    return {
        "".join(str(bit) for bit in row): count
        for row, count in result.histogram(key="z", fold_func=tuple).items()
    }


def _exact_histogram(circuit: cirq.Circuit) -> dict[str, float]:
    measured_qubits = _compiled_measurement_qubits(circuit)
    if measured_qubits is None:
        raise ValueError("circuit must contain one z measurement")
    unitary_part = cirq.Circuit(
        op for op in circuit.all_operations() if not isinstance(op.gate, cirq.MeasurementGate)
    )
    qubits = sorted(unitary_part.all_qubits() | set(measured_qubits))
    qubit_positions = {qubit: index for index, qubit in enumerate(qubits)}
    measured_positions = [qubit_positions[qubit] for qubit in measured_qubits]
    result = cirq.Simulator().simulate(unitary_part, qubit_order=qubits)
    histogram: dict[str, float] = {}
    for basis_index, amplitude in enumerate(result.final_state_vector):
        probability = abs(amplitude) ** 2
        if probability < 1e-12:
            continue
        bits = cirq.big_endian_int_to_bits(basis_index, bit_count=len(qubits))
        key = "".join(str(bits[position]) for position in measured_positions)
        histogram[key] = histogram.get(key, 0.0) + float(probability)
    return histogram


def _is_clifford_circuit(circuit: cirq.Circuit) -> bool:
    for op in circuit.all_operations():
        if isinstance(op.gate, (cirq.MeasurementGate, cirq.IdentityGate)):
            continue
        if isinstance(op.gate, (cirq.HPowGate, cirq.CXPowGate, cirq.XPowGate, cirq.YPowGate)):
            if abs((float(op.gate.exponent) % 2) - 1.0) < 1e-9:
                continue
        if isinstance(op.gate, cirq.ZPowGate):
            exponent = float(op.gate.exponent) % 2
            if any(abs(exponent - allowed) < 1e-9 for allowed in (0.5, 1.0, 1.5)):
                continue
        return False
    return True


def _total_variation(left: dict[str, float | int], right: dict[str, float | int]) -> float:
    left_total = sum(left.values())
    right_total = sum(right.values())
    keys = set(left) | set(right)
    return 0.5 * sum(abs(left.get(key, 0) / left_total - right.get(key, 0) / right_total) for key in keys)
