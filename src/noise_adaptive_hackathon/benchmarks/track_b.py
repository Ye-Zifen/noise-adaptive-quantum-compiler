from __future__ import annotations

from random import Random

import cirq

from .model import CompetitionBenchmark, ExpectedOutputRule, ParityCheck

TRACK_B_FAMILIES = ("ghz", "parity")


def generate_track_b_benchmark(
    num_qubits: int,
    depth: int,
    seed: int,
    family: str = "parity",
    sample_id: str | None = None,
) -> CompetitionBenchmark:
    if num_qubits < 4:
        raise ValueError("track_b benchmarks require at least 4 qubits")
    if family not in TRACK_B_FAMILIES:
        raise ValueError(f"unsupported track_b family: {family}")

    rng = Random(seed)
    qubits = tuple(cirq.LineQubit.range(num_qubits))
    if family == "ghz":
        circuit, rule = _ghz(qubits)
    else:
        circuit, rule = _parity_network(qubits, depth, rng)
    circuit.append(cirq.measure(*qubits, key="z"))

    return CompetitionBenchmark(
        track="track_b",
        name=sample_id or f"track_b_{family}_{num_qubits}q_d{depth}_seed{seed}",
        family=family,
        circuit=circuit,
        logical_qubits=qubits,
        expected_output_rule=rule,
        metadata={
            "family": family,
            "num_qubits": num_qubits,
            "depth": depth,
            "clifford_only": True,
        },
    )


def _ghz(qubits: tuple[cirq.LineQubit, ...]) -> tuple[cirq.Circuit, ExpectedOutputRule]:
    circuit = cirq.Circuit(cirq.H(qubits[0]))
    for qubit in qubits[1:]:
        circuit.append(cirq.CNOT(qubits[0], qubit))
    return circuit, ExpectedOutputRule(
        rule_type="allowed_bitstrings",
        allowed_bitstrings=("0" * len(qubits), "1" * len(qubits)),
    )


def _parity_network(
    qubits: tuple[cirq.LineQubit, ...],
    depth: int,
    rng: Random,
) -> tuple[cirq.Circuit, ExpectedOutputRule]:
    circuit = cirq.Circuit()
    checks: list[ParityCheck] = []
    group_size = 4
    anchors = [qubits[index] for index in range(0, len(qubits), group_size)]
    for anchor in anchors:
        circuit.append(cirq.H(anchor))
    for layer in range(max(0, depth)):
        if len(anchors) < 2:
            break
        left = anchors[layer % len(anchors)]
        right = anchors[(layer + 1 + rng.randrange(len(anchors) - 1)) % len(anchors)]
        if left != right:
            circuit.append(cirq.CNOT(left, right))

    for start in range(0, len(qubits), group_size):
        group = qubits[start : min(start + group_size, len(qubits))]
        if len(group) < 2:
            continue
        anchor = group[0]
        flips: dict[int, int] = {}
        for member in group[1:]:
            circuit.append(cirq.CNOT(anchor, member))
            if rng.random() > 0.65:
                circuit.append(cirq.X(member))
                flips[member.x] = 1
            else:
                flips[member.x] = 0
            checks.append(((anchor.x, member.x), flips[member.x]))

    return circuit, ExpectedOutputRule(rule_type="parity_checks", parity_checks=tuple(checks))
