from __future__ import annotations

import cirq

from noise_adaptive_hackathon.benchmarks.model import CompetitionBenchmark
from noise_adaptive_hackathon.formats.backend import CompetitionBackend

from .model import MeasurementRunResult


def run_track_a(
    benchmark: CompetitionBenchmark,
    compiled_circuit: cirq.Circuit,
    backend: CompetitionBackend,
    shots: int,
    seed: int,
) -> MeasurementRunResult:
    noisy_circuit = _inject_cirq_noise(compiled_circuit, backend)
    simulator = cirq.DensityMatrixSimulator(seed=seed)
    result = simulator.run(noisy_circuit, repetitions=shots)
    samples = result.measurements["z"]
    correct = sum(1 for row in samples if benchmark.expected_output_rule.is_correct("".join(str(bit) for bit in row)))
    return MeasurementRunResult(success_rate=correct / shots, correct_shots=correct, total_shots=shots)


def _inject_cirq_noise(circuit: cirq.Circuit, backend: CompetitionBackend) -> cirq.Circuit:
    noisy = cirq.Circuit()
    for op in circuit.all_operations():
        if isinstance(op.gate, cirq.IdentityGate):
            continue
        noisy.append(op)
        if isinstance(op.gate, cirq.MeasurementGate):
            continue
        if len(op.qubits) == 1 and backend.single_qubit_error > 0:
            noisy.append(cirq.depolarize(backend.single_qubit_error).on(op.qubits[0]))
        if len(op.qubits) == 2:
            error = backend.edge_error(op.qubits[0].x, op.qubits[1].x)
            noisy.append(cirq.depolarize(error, n_qubits=2).on(*op.qubits))
    noisy = _inject_readout_error(noisy, backend)
    return noisy


def _inject_readout_error(circuit: cirq.Circuit, backend: CompetitionBackend) -> cirq.Circuit:
    rewritten = cirq.Circuit()
    for op in circuit.all_operations():
        if isinstance(op.gate, cirq.MeasurementGate):
            for qubit in op.qubits:
                probability = backend.readout(qubit.x)
                if probability > 0:
                    rewritten.append(cirq.bit_flip(probability).on(qubit))
            rewritten.append(op)
        else:
            rewritten.append(op)
    return rewritten
