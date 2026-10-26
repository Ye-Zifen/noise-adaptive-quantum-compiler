from __future__ import annotations

import cirq
import networkx as nx

from noise_adaptive_hackathon.formats.backend import CompetitionBackend

from .common import decompose_swaps


class CirqCQCCompiler:
    name = "cirq_cqc"

    def compile(self, circuit: cirq.Circuit, backend: CompetitionBackend, seed: int = 0) -> cirq.Circuit:
        del seed
        device_graph = nx.Graph()
        physical_qubits = tuple(cirq.LineQubit.range(backend.num_qubits))
        device_graph.add_nodes_from(physical_qubits)
        device_graph.add_edges_from(
            (physical_qubits[left], physical_qubits[right])
            for left, right in backend.coupling_map
        )
        routed, initial_map, _ = cirq.RouteCQC(device_graph).route_circuit(circuit)
        self.last_initial_layout = {
            logical: physical.x
            for logical, physical in initial_map.items()
        }
        return decompose_swaps(cirq.Circuit(routed))
