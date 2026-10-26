from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import cirq

from .model import CompetitionBenchmark, ExpectedOutputRule


def write_benchmark(benchmark: CompetitionBenchmark, directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    cirq.to_json(benchmark.circuit, directory / "circuit.json")
    payload = {
        "track": benchmark.track,
        "name": benchmark.name,
        "family": benchmark.family,
        "logical_qubits": [qubit.x for qubit in benchmark.logical_qubits],
        "expected_output_rule": {
            "rule_type": benchmark.expected_output_rule.rule_type,
            "bitstring": benchmark.expected_output_rule.bitstring,
            "allowed_bitstrings": list(benchmark.expected_output_rule.allowed_bitstrings),
            "parity_checks": [
                {"qubits": list(indices), "value": value}
                for indices, value in benchmark.expected_output_rule.parity_checks
            ],
        },
        "metadata": benchmark.metadata,
    }
    (directory / "benchmark.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_benchmark(directory: Path) -> CompetitionBenchmark:
    payload = json.loads((directory / "benchmark.json").read_text(encoding="utf-8"))
    circuit = cirq.read_json(directory / "circuit.json")
    logical_qubits = tuple(cirq.LineQubit(index) for index in payload["logical_qubits"])
    return CompetitionBenchmark(
        track=payload["track"],
        name=payload["name"],
        family=payload["family"],
        circuit=circuit,
        logical_qubits=logical_qubits,
        expected_output_rule=_load_expected_rule(payload["expected_output_rule"]),
        metadata=payload["metadata"],
    )


def _load_expected_rule(payload: dict[str, Any]) -> ExpectedOutputRule:
    return ExpectedOutputRule(
        rule_type=payload["rule_type"],
        bitstring=payload.get("bitstring"),
        allowed_bitstrings=tuple(payload.get("allowed_bitstrings", [])),
        parity_checks=tuple(
            (tuple(check["qubits"]), int(check["value"]))
            for check in payload.get("parity_checks", [])
        ),
    )
