from __future__ import annotations

import cirq

from noise_adaptive_hackathon.formats.backend import CompetitionBackend

from .common import BaseCompetitionCompiler, trivial_layout


class VanillaCompiler(BaseCompetitionCompiler):
    name = "vanilla"

    def initial_layout(self, circuit: cirq.Circuit, backend: CompetitionBackend) -> dict[cirq.LineQubit, int]:
        return trivial_layout(circuit, backend)

    def route_path(self, source: int, target: int, backend: CompetitionBackend) -> list[int]:
        return backend.shortest_path(source, target)
