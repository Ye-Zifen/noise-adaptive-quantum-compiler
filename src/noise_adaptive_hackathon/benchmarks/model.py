from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import cirq

ParityCheck = tuple[tuple[int, ...], int]


@dataclass(frozen=True)
class ExpectedOutputRule:
    rule_type: Literal["bitstring", "allowed_bitstrings", "parity_checks"]
    bitstring: str | None = None
    allowed_bitstrings: tuple[str, ...] = ()
    parity_checks: tuple[ParityCheck, ...] = ()

    def is_correct(self, bitstring: str) -> bool:
        if self.rule_type == "bitstring":
            return bitstring == self.bitstring
        if self.rule_type == "allowed_bitstrings":
            return bitstring in self.allowed_bitstrings
        return all(_parity(bitstring, indices) == value for indices, value in self.parity_checks)


def _parity(bitstring: str, indices: tuple[int, ...]) -> int:
    return sum(int(bitstring[index]) for index in indices) % 2


@dataclass(frozen=True)
class CompetitionBenchmark:
    track: Literal["track_a", "track_b"]
    name: str
    family: str
    circuit: cirq.Circuit
    logical_qubits: tuple[cirq.LineQubit, ...]
    expected_output_rule: ExpectedOutputRule
    metadata: dict[str, Any]
