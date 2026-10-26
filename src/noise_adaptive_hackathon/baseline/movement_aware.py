from __future__ import annotations

import cirq

from noise_adaptive_hackathon.formats.backend import CompetitionBackend

from .common import BaseCompetitionCompiler, movement_aware_layout


class MovementAwareCompiler(BaseCompetitionCompiler):
    name = "movement_aware"

    def initial_layout(self, circuit: cirq.Circuit, backend: CompetitionBackend) -> dict[cirq.LineQubit, int]:
        return movement_aware_layout(circuit, backend)

    def route_path(self, source: int, target: int, backend: CompetitionBackend) -> list[int]:
        return backend.shortest_path(source, target)
