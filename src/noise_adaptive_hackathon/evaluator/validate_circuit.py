from __future__ import annotations

from dataclasses import dataclass
import math

import cirq

from noise_adaptive_hackathon.formats.backend import CompetitionBackend, TRACK_B_CLIFFORD_BASIS


@dataclass(frozen=True)
class CircuitValidation:
    valid: bool
    errors: list[str]


def validate_compiled_circuit(
    circuit: cirq.Circuit,
    backend: CompetitionBackend,
    track: str,
    max_operations: int = 20_000,
) -> CircuitValidation:
    errors: list[str] = []
    operations = list(circuit.all_operations())
    if len(operations) > max_operations:
        errors.append(f"operation count {len(operations)} exceeds limit {max_operations}")

    allowed_two_qubit_edges = {tuple(sorted(edge)) for edge in backend.coupling_map}
    seen_measurement = False
    measurement_keys: list[str] = []
    for qubit in circuit.all_qubits():
        if not isinstance(qubit, cirq.LineQubit):
            errors.append(f"unsupported qubit type {type(qubit).__name__}")
            continue
        if qubit.x < 0 or qubit.x >= backend.num_qubits:
            errors.append(f"physical qubit {qubit.x} outside backend range")

    for op in operations:
        if isinstance(op.gate, cirq.IdentityGate):
            continue
        if getattr(op, "classical_controls", None):
            errors.append("classically controlled operations are not allowed")

        gate_name = gate_name_for_operation(op)
        if gate_name is None:
            errors.append(f"unsupported operation {op}")
            continue

        if seen_measurement and gate_name != "measure":
            errors.append("non-measurement operation appears after measurement")
        if gate_name == "measure":
            seen_measurement = True
            key = cirq.measurement_key_name(op)
            measurement_keys.append(key)
            if key != "z":
                errors.append(f"measurement key must be z, got {key}")

        if gate_name not in backend.basis_gates:
            errors.append(f"gate {gate_name} is not in backend basis")
        if track == "track_b" and gate_name not in TRACK_B_CLIFFORD_BASIS:
            errors.append(f"gate {gate_name} is not allowed in Track B")
        if gate_name != "measure" and len(op.qubits) == 2 and tuple(sorted(qubit.x for qubit in op.qubits)) not in allowed_two_qubit_edges:
            errors.append(f"two-qubit gate on illegal edge {tuple(qubit.x for qubit in op.qubits)}")
        if gate_name != "measure" and len(op.qubits) > 2:
            errors.append(f"operation acts on {len(op.qubits)} qubits; only 1Q and 2Q gates are allowed")

    if not measurement_keys:
        errors.append("compiled circuit must contain a final measurement")
    if len(set(measurement_keys)) != len(measurement_keys):
        errors.append("measurement keys must be unique")
    if measurement_keys != ["z"]:
        errors.append("compiled circuit must use exactly one measurement key: z")

    return CircuitValidation(valid=not errors, errors=errors)


def gate_name_for_operation(op: cirq.Operation) -> str | None:
    if isinstance(op.gate, cirq.MeasurementGate):
        return "measure"
    if isinstance(op.gate, cirq.HPowGate) and _is_half_turn(op.gate.exponent, 1.0):
        return "h"
    if isinstance(op.gate, cirq.CXPowGate) and _is_half_turn(op.gate.exponent, 1.0):
        return "cx"
    if isinstance(op.gate, cirq.SwapPowGate):
        return "swap"
    if isinstance(op.gate, cirq.XPowGate) and len(op.qubits) == 1:
        return "x" if _is_half_turn(op.gate.exponent, 1.0) else "rx"
    if isinstance(op.gate, cirq.YPowGate) and len(op.qubits) == 1:
        return "y" if _is_half_turn(op.gate.exponent, 1.0) else "ry"
    if isinstance(op.gate, cirq.ZPowGate) and len(op.qubits) == 1:
        exponent = float(op.gate.exponent) % 2
        if _is_half_turn(exponent, 1.0):
            return "z"
        if _is_half_turn(exponent, 0.5):
            return "s"
        if _is_half_turn(exponent, 1.5):
            return "sdg"
        if _is_half_turn(exponent, 0.25):
            return "t"
        if _is_half_turn(exponent, 1.75):
            return "tdg"
        return "rz"
    return None


def count_two_qubit_gates(circuit: cirq.Circuit) -> int:
    return sum(
        1
        for op in circuit.all_operations()
        if not isinstance(op.gate, cirq.IdentityGate) and len(op.qubits) == 2
    )


def estimate_log_reliability(circuit: cirq.Circuit, backend: CompetitionBackend) -> float:
    total = 0.0
    for op in circuit.all_operations():
        if isinstance(op.gate, cirq.IdentityGate):
            continue
        gate_name = gate_name_for_operation(op)
        if gate_name == "measure":
            for qubit in op.qubits:
                total += math.log(max(1.0 - backend.readout(qubit.x), 1e-12))
        elif len(op.qubits) == 1:
            total += math.log(max(1.0 - backend.single_qubit_error, 1e-12))
        elif len(op.qubits) == 2:
            total += math.log(max(1.0 - backend.edge_error(op.qubits[0].x, op.qubits[1].x), 1e-12))
    return total


def _is_half_turn(exponent: float, target: float) -> bool:
    return abs((float(exponent) % 2) - target) < 1e-9
