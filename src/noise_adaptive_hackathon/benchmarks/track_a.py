from __future__ import annotations

from random import Random

import cirq

from .model import CompetitionBenchmark, ExpectedOutputRule

TRACK_A_FAMILIES = (
    "bv",
    "hs",
    "toffoli",
    "fredkin",
    "peres",
    "or",
    "adder",
    "structured_random",
)


def generate_track_a_benchmark(
    family: str,
    logical_qubits: int,
    seed: int,
    sample_id: str | None = None,
) -> CompetitionBenchmark:
    if logical_qubits < 4:
        raise ValueError("track_a benchmarks require at least 4 qubits")
    if family not in TRACK_A_FAMILIES:
        raise ValueError(f"unsupported track_a family: {family}")

    rng = Random(seed)
    qubits = tuple(cirq.LineQubit.range(logical_qubits))
    circuit, expected = _build_functional_circuit(family, qubits, rng)
    circuit.append(cirq.measure(*qubits, key="z"))

    return CompetitionBenchmark(
        track="track_a",
        name=sample_id or f"{family}_{logical_qubits}q_seed{seed}",
        family=family,
        circuit=circuit,
        logical_qubits=qubits,
        expected_output_rule=ExpectedOutputRule(rule_type="bitstring", bitstring=expected),
        metadata={"family": family, "logical_qubits": logical_qubits, "clifford_only": False},
    )


def _build_functional_circuit(
    family: str,
    qubits: tuple[cirq.LineQubit, ...],
    rng: Random,
) -> tuple[cirq.Circuit, str]:
    if family == "bv":
        return _bv(qubits, rng)
    if family == "hs":
        return _linear_hidden_shift(qubits, rng)
    if family == "toffoli":
        return _toffoli_like(qubits, rng)
    if family == "fredkin":
        return _fredkin_like(qubits, rng)
    if family == "peres":
        return _peres_like(qubits, rng)
    if family == "or":
        return _or_like(qubits, rng)
    if family == "adder":
        return _adder_like(qubits, rng)
    return _structured_random(qubits, rng)


def _bv(qubits: tuple[cirq.LineQubit, ...], rng: Random) -> tuple[cirq.Circuit, str]:
    secret = _random_bitstring(rng, len(qubits) - 1, allow_zero=False)
    ancilla = qubits[-1]
    circuit = cirq.Circuit(cirq.X(ancilla), cirq.H.on_each(*qubits))
    for index, bit in enumerate(secret):
        if bit == "1":
            circuit.append(cirq.CNOT(qubits[index], ancilla))
    circuit.append(cirq.H.on_each(*qubits[:-1]))
    circuit.append(cirq.H(ancilla))
    circuit.append(cirq.X(ancilla))
    return circuit, secret + "0"


def _linear_hidden_shift(qubits: tuple[cirq.LineQubit, ...], rng: Random) -> tuple[cirq.Circuit, str]:
    state = list(_random_bitstring(rng, len(qubits), allow_zero=False))
    circuit = cirq.Circuit()
    _append_bitstring(circuit, qubits, state)
    for index in range(len(qubits) - 1):
        circuit.append(cirq.CNOT(qubits[index], qubits[index + 1]))
        state[index + 1] = _xor(state[index + 1], state[index])
    for index in range(len(qubits) - 2, -1, -2):
        circuit.append(cirq.CNOT(qubits[index + 1], qubits[index]))
        state[index] = _xor(state[index], state[index + 1])
    return circuit, "".join(state)


def _toffoli_like(qubits: tuple[cirq.LineQubit, ...], rng: Random) -> tuple[cirq.Circuit, str]:
    state = list("11" + str(rng.randint(0, 1)) + _random_bitstring(rng, len(qubits) - 3))
    circuit = cirq.Circuit()
    _append_bitstring(circuit, qubits, state)
    circuit += _toffoli_decomposition(qubits[0], qubits[1], qubits[2])
    state[2] = _xor(state[2], _and(state[0], state[1]))
    return circuit, "".join(state)


def _fredkin_like(qubits: tuple[cirq.LineQubit, ...], rng: Random) -> tuple[cirq.Circuit, str]:
    state = list("1" + _random_bitstring(rng, 2, allow_zero=False) + _random_bitstring(rng, len(qubits) - 3))
    circuit = cirq.Circuit()
    _append_bitstring(circuit, qubits, state)
    circuit.append(cirq.CNOT(qubits[1], qubits[2]))
    state[2] = _xor(state[2], state[1])
    circuit += _toffoli_decomposition(qubits[0], qubits[2], qubits[1])
    state[1] = _xor(state[1], _and(state[0], state[2]))
    circuit.append(cirq.CNOT(qubits[1], qubits[2]))
    state[2] = _xor(state[2], state[1])
    return circuit, "".join(state)


def _peres_like(qubits: tuple[cirq.LineQubit, ...], rng: Random) -> tuple[cirq.Circuit, str]:
    state = list("11" + str(rng.randint(0, 1)) + _random_bitstring(rng, len(qubits) - 3))
    circuit = cirq.Circuit()
    _append_bitstring(circuit, qubits, state)
    circuit.append(cirq.CNOT(qubits[0], qubits[1]))
    state[1] = _xor(state[1], state[0])
    circuit += _toffoli_decomposition(qubits[0], qubits[1], qubits[2])
    state[2] = _xor(state[2], _and(state[0], state[1]))
    return circuit, "".join(state)


def _or_like(qubits: tuple[cirq.LineQubit, ...], rng: Random) -> tuple[cirq.Circuit, str]:
    inputs = _random_bitstring(rng, 2, allow_zero=False)
    state = list(inputs + "0" + _random_bitstring(rng, len(qubits) - 3))
    circuit = cirq.Circuit()
    _append_bitstring(circuit, qubits, state)
    circuit.append(cirq.X(qubits[0]))
    state[0] = _xor(state[0], "1")
    circuit.append(cirq.X(qubits[1]))
    state[1] = _xor(state[1], "1")
    circuit += _toffoli_decomposition(qubits[0], qubits[1], qubits[2])
    state[2] = _xor(state[2], _and(state[0], state[1]))
    circuit.append(cirq.X(qubits[0]))
    state[0] = _xor(state[0], "1")
    circuit.append(cirq.X(qubits[1]))
    state[1] = _xor(state[1], "1")
    circuit.append(cirq.X(qubits[2]))
    state[2] = _xor(state[2], "1")
    return circuit, "".join(state)


def _adder_like(qubits: tuple[cirq.LineQubit, ...], rng: Random) -> tuple[cirq.Circuit, str]:
    if len(qubits) < 6:
        raise ValueError("adder benchmark requires at least 6 qubits")
    state = list(_random_bitstring(rng, len(qubits), allow_zero=False))
    circuit = cirq.Circuit()
    _append_bitstring(circuit, qubits, state)
    circuit.append(cirq.CNOT(qubits[0], qubits[2]))
    state[2] = _xor(state[2], state[0])
    circuit.append(cirq.CNOT(qubits[1], qubits[2]))
    state[2] = _xor(state[2], state[1])
    circuit += _toffoli_decomposition(qubits[0], qubits[1], qubits[3])
    state[3] = _xor(state[3], _and(state[0], state[1]))
    circuit.append(cirq.CNOT(qubits[2], qubits[4]))
    state[4] = _xor(state[4], state[2])
    circuit += _toffoli_decomposition(qubits[2], qubits[3], qubits[5])
    state[5] = _xor(state[5], _and(state[2], state[3]))
    return circuit, "".join(state)


def _structured_random(qubits: tuple[cirq.LineQubit, ...], rng: Random) -> tuple[cirq.Circuit, str]:
    state = list(_random_bitstring(rng, len(qubits), allow_zero=False))
    circuit = cirq.Circuit()
    _append_bitstring(circuit, qubits, state)
    for _ in range(max(6, len(qubits) + 2)):
        gate = rng.choice(("x", "cx", "toffoli"))
        if gate == "x":
            target = rng.randrange(len(qubits))
            circuit.append(cirq.X(qubits[target]))
            state[target] = _xor(state[target], "1")
        elif gate == "cx":
            control, target = rng.sample(range(len(qubits)), 2)
            circuit.append(cirq.CNOT(qubits[control], qubits[target]))
            state[target] = _xor(state[target], state[control])
        else:
            control_a, control_b, target = rng.sample(range(len(qubits)), 3)
            circuit += _toffoli_decomposition(qubits[control_a], qubits[control_b], qubits[target])
            state[target] = _xor(state[target], _and(state[control_a], state[control_b]))
    return circuit, "".join(state)


def _append_bitstring(circuit: cirq.Circuit, qubits: tuple[cirq.LineQubit, ...], state: list[str]) -> None:
    for index, bit in enumerate(state):
        if bit == "1":
            circuit.append(cirq.X(qubits[index]))


def _random_bitstring(rng: Random, width: int, *, allow_zero: bool = True) -> str:
    if width <= 0:
        return ""
    while True:
        bitstring = "".join(str(rng.randint(0, 1)) for _ in range(width))
        if allow_zero or "1" in bitstring:
            return bitstring


def _xor(left: str, right: str) -> str:
    return str(int(left) ^ int(right))


def _and(left: str, right: str) -> str:
    return str(int(left) & int(right))


def _toffoli_decomposition(
    control_a: cirq.LineQubit,
    control_b: cirq.LineQubit,
    target: cirq.LineQubit,
) -> cirq.Circuit:
    return cirq.Circuit(
        cirq.H(target),
        cirq.CNOT(control_b, target),
        cirq.T(target) ** -1,
        cirq.CNOT(control_a, target),
        cirq.T(target),
        cirq.CNOT(control_b, target),
        cirq.T(target) ** -1,
        cirq.CNOT(control_a, target),
        cirq.T(control_b),
        cirq.T(target),
        cirq.H(target),
        cirq.CNOT(control_a, control_b),
        cirq.T(control_a),
        cirq.T(control_b) ** -1,
        cirq.CNOT(control_a, control_b),
    )
