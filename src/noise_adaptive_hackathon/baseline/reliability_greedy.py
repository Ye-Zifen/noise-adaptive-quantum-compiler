from __future__ import annotations

import cirq

from noise_adaptive_hackathon.formats.backend import CompetitionBackend

from .common import BaseCompetitionCompiler, reliability_layout


class ReliabilityGreedyCompiler(BaseCompetitionCompiler):
    name = "reliability_greedy"

    def initial_layout(self, circuit: cirq.Circuit, backend: CompetitionBackend) -> dict[cirq.LineQubit, int]:
        return reliability_layout(circuit, backend)

    def route_path(self, source: int, target: int, backend: CompetitionBackend) -> list[int]:
        return backend.most_reliable_path(source, target)
