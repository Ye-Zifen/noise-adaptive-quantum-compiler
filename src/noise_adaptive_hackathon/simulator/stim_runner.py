from __future__ import annotations

import cirq
import stim

from noise_adaptive_hackathon.benchmarks.model import CompetitionBenchmark
from noise_adaptive_hackathon.formats.backend import CompetitionBackend

from .model import MeasurementRunResult


def run_track_b(
    benchmark: CompetitionBenchmark,
    compiled_circuit: cirq.Circuit,
    backend: CompetitionBackend,
    shots: int,
    seed: int,
) -> MeasurementRunResult:
    stim_circuit = _cirq_to_stim(compiled_circuit, backend)
    sampler = stim_circuit.compile_sampler(seed=seed)
    samples = sampler.sample(shots)
    correct = sum(1 for row in samples if benchmark.expected_output_rule.is_correct("".join(str(int(bit)) for bit in row)))
    return MeasurementRunResult(success_rate=correct / shots, correct_shots=correct, total_shots=shots)


def _cirq_to_stim(circuit: cirq.Circuit, backend: CompetitionBackend) -> stim.Circuit:
    stim_circuit = stim.Circuit()
    for op in circuit.all_operations():
        if isinstance(op.gate, cirq.IdentityGate):
            continue
        if isinstance(op.gate, cirq.MeasurementGate):
            for qubit in op.qubits:
                probability = backend.readout(qubit.x)
                if probability > 0:
                    stim_circuit.append("X_ERROR", [qubit.x], probability)
            stim_circuit.append("M", [qubit.x for qubit in op.qubits])
            continue

        gate_name = _stim_gate_name(op)
        stim_circuit.append(gate_name, [qubit.x for qubit in op.qubits])
        if len(op.qubits) == 1 and backend.single_qubit_error > 0:
            stim_circuit.append("DEPOLARIZE1", [op.qubits[0].x], backend.single_qubit_error)
        if len(op.qubits) == 2:
            stim_circuit.append(
                "DEPOLARIZE2",
                [op.qubits[0].x, op.qubits[1].x],
                backend.edge_error(op.qubits[0].x, op.qubits[1].x),
            )
    return stim_circuit


def _stim_gate_name(op: cirq.Operation) -> str:
    if isinstance(op.gate, cirq.HPowGate) and op.gate.exponent % 2 == 1:
        return "H"
    if isinstance(op.gate, cirq.XPowGate) and len(op.qubits) == 1 and op.gate.exponent % 2 == 1:
        return "X"
    if isinstance(op.gate, cirq.YPowGate) and len(op.qubits) == 1 and op.gate.exponent % 2 == 1:
        return "Y"
    if isinstance(op.gate, cirq.ZPowGate) and len(op.qubits) == 1:
        normalized = float(op.gate.exponent) % 2
        if abs(normalized - 1.0) < 1e-9:
            return "Z"
        if abs(normalized - 0.5) < 1e-9:
            return "S"
        if abs(normalized - 1.5) < 1e-9:
            return "S_DAG"
    if isinstance(op.gate, cirq.CXPowGate) and op.gate.exponent % 2 == 1:
        return "CX"
    raise ValueError(f"stim runner only supports Clifford gates, got {op}")
