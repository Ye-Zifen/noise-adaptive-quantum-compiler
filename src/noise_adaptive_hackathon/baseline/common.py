from __future__ import annotations

from abc import ABC, abstractmethod
import math

import cirq
import networkx as nx

from noise_adaptive_hackathon.formats.backend import CompetitionBackend


class BaseCompetitionCompiler(ABC):
    name: str

    def compile(self, circuit: cirq.Circuit, backend: CompetitionBackend, seed: int = 0) -> cirq.Circuit:
        logical_qubits = sorted(circuit.all_qubits(), key=lambda qubit: qubit.x)
        if len(logical_qubits) > backend.num_qubits:
            raise ValueError("program circuit does not fit on backend")

        layout = self.initial_layout(circuit, backend)
        self.last_initial_layout = layout
        mapping = {logical.x: physical for logical, physical in layout.items()}
        reverse = {physical: logical for logical, physical in mapping.items()}
        physical_qubits = tuple(cirq.LineQubit.range(backend.num_qubits))
        compiled = cirq.Circuit(cirq.Moment(cirq.I(qubit) for qubit in physical_qubits))

        for op in circuit.all_operations():
            if isinstance(op.gate, cirq.MeasurementGate):
                compiled.append(cirq.measure(*[physical_qubits[mapping[q.x]] for q in op.qubits], key=op.gate.key))
                continue

            if len(op.qubits) == 1:
                logical = op.qubits[0].x
                compiled.append(op.transform_qubits(lambda _: physical_qubits[mapping[logical]]))
                continue

            if len(op.qubits) != 2:
                raise ValueError("only one- and two-qubit operations are supported by the competition compiler")

            left = op.qubits[0].x
            right = op.qubits[1].x
            path = self.route_path(mapping[left], mapping[right], backend)
            while len(path) > 2:
                source = path[-1]
                target = path[-2]
                compiled.append(_decomposed_swap(physical_qubits[source], physical_qubits[target]))
                moving_logical = reverse[source]
                displaced_logical = reverse.get(target)
                reverse[target] = moving_logical
                reverse[source] = displaced_logical
                mapping[moving_logical] = target
                if displaced_logical is not None:
                    mapping[displaced_logical] = source
                path = self.route_path(mapping[left], mapping[right], backend)
            compiled.append(
                op.transform_qubits(
                    lambda qubit: physical_qubits[mapping[qubit.x]]
                )
            )

        return compiled

    @abstractmethod
    def initial_layout(self, circuit: cirq.Circuit, backend: CompetitionBackend) -> dict[cirq.LineQubit, int]:
        raise NotImplementedError

    @abstractmethod
    def route_path(self, source: int, target: int, backend: CompetitionBackend) -> list[int]:
        raise NotImplementedError


def build_interaction_graph(circuit: cirq.Circuit) -> nx.Graph:
    graph = nx.Graph()
    logical_qubits = sorted(circuit.all_qubits(), key=lambda qubit: qubit.x)
    graph.add_nodes_from(logical_qubits)
    for op in circuit.all_operations():
        if len(op.qubits) == 2:
            left, right = op.qubits
            current = graph.get_edge_data(left, right, {}).get("weight", 0) + 1
            graph.add_edge(left, right, weight=current)
    return graph


def movement_aware_layout(circuit: cirq.Circuit, backend: CompetitionBackend) -> dict[cirq.LineQubit, int]:
    graph = build_interaction_graph(circuit)
    hardware = backend.graph()
    logical_order = sorted(graph.nodes, key=lambda node: (graph.degree(node), -node.x), reverse=True)
    available = set(range(backend.num_qubits))
    layout: dict[cirq.LineQubit, int] = {}
    for logical in logical_order:
        if not layout:
            physical = max(available, key=lambda node: (hardware.degree(node), -node))
        else:
            placed = [neighbor for neighbor in graph.neighbors(logical) if neighbor in layout]
            physical = min(
                available,
                key=lambda node: (
                    sum(nx.shortest_path_length(hardware, node, layout[p], weight=None) for p in placed) if placed else 0,
                    -hardware.degree(node),
                    node,
                ),
            )
        layout[logical] = physical
        available.remove(physical)
    return layout


def reliability_layout(circuit: cirq.Circuit, backend: CompetitionBackend) -> dict[cirq.LineQubit, int]:
    graph = build_interaction_graph(circuit)
    if len(graph.nodes) >= backend.num_qubits:
        return movement_aware_layout(circuit, backend)
    hardware = backend.graph()
    reliability_lengths = dict(nx.all_pairs_dijkstra_path_length(hardware, weight="cost"))
    path_lengths = dict(nx.all_pairs_shortest_path_length(hardware))
    candidates = [
        movement_aware_layout(circuit, backend),
        _reliability_layout_candidate(graph, hardware, reliability_lengths, path_lengths, backend),
    ]
    return min(
        candidates,
        key=lambda layout: _estimate_layout_cost(graph, hardware, layout, reliability_lengths, path_lengths),
    )


def _reliability_layout_candidate(
    graph: nx.Graph,
    hardware: nx.Graph,
    reliability_lengths: dict[int, dict[int, float]],
    path_lengths: dict[int, dict[int, int]],
    backend: CompetitionBackend,
) -> dict[cirq.LineQubit, int]:
    available = set(range(backend.num_qubits))
    layout: dict[cirq.LineQubit, int] = {}
    logical_weight = {
        node: sum(data["weight"] for _, _, data in graph.edges(node, data=True))
        for node in graph.nodes
    }

    if graph.number_of_edges() > 0:
        logical_left, logical_right, logical_data = max(
            graph.edges(data=True),
            key=lambda item: (item[2]["weight"], logical_weight[item[0]] + logical_weight[item[1]], -item[0].x, -item[1].x),
        )
        physical_left, physical_right = max(
            hardware.edges,
            key=lambda edge: (
                hardware.edges[edge]["reliability"],
                -sum(path_lengths[edge[0]].values()) - sum(path_lengths[edge[1]].values()),
                hardware.nodes[edge[0]]["readout_reliability"] + hardware.nodes[edge[1]]["readout_reliability"],
            ),
        )
        seeded = sorted(
            ((logical_left, physical_left), (logical_right, physical_right)),
            key=lambda item: (logical_weight[item[0]], -item[0].x),
            reverse=True,
        )
        for logical, physical in seeded:
            layout[logical] = physical
            available.remove(physical)

    while len(layout) < len(graph.nodes):
        logical = _next_reliability_logical(graph, layout, logical_weight)
        placed = [(neighbor, graph.edges[logical, neighbor]["weight"]) for neighbor in graph.neighbors(logical) if neighbor in layout]
        physical = max(
            available,
            key=lambda node: (
                sum(weight * math.exp(-reliability_lengths[node][layout[neighbor]]) for neighbor, weight in placed),
                -sum(weight * path_lengths[node][layout[neighbor]] for neighbor, weight in placed),
                hardware.nodes[node]["readout_reliability"],
                hardware.degree(node),
                -node,
            ),
        )
        layout[logical] = physical
        available.remove(physical)
    return layout


def _next_reliability_logical(
    graph: nx.Graph,
    layout: dict[cirq.LineQubit, int],
    logical_weight: dict[cirq.LineQubit, int],
) -> cirq.LineQubit:
    unplaced = [node for node in graph.nodes if node not in layout]
    return max(
        unplaced,
        key=lambda node: (
            sum(graph.edges[node, neighbor]["weight"] for neighbor in graph.neighbors(node) if neighbor in layout),
            logical_weight[node],
            graph.degree(node),
            -node.x,
        ),
    )


def _estimate_layout_cost(
    graph: nx.Graph,
    hardware: nx.Graph,
    layout: dict[cirq.LineQubit, int],
    reliability_lengths: dict[int, dict[int, float]],
    path_lengths: dict[int, dict[int, int]],
) -> float:
    interaction_cost = 0.0
    for left, right, data in graph.edges(data=True):
        weight = data["weight"]
        interaction_cost += weight * (
            reliability_lengths[layout[left]][layout[right]] + 0.35 * path_lengths[layout[left]][layout[right]]
        )
    readout_bonus = sum(hardware.nodes[physical]["readout_reliability"] for physical in layout.values())
    return interaction_cost - 0.1 * readout_bonus


def trivial_layout(circuit: cirq.Circuit, backend: CompetitionBackend) -> dict[cirq.LineQubit, int]:
    logical_qubits = sorted(circuit.all_qubits(), key=lambda qubit: qubit.x)
    return {logical: index for index, logical in enumerate(logical_qubits)}


def _decomposed_swap(left: cirq.LineQubit, right: cirq.LineQubit) -> tuple[cirq.Operation, cirq.Operation, cirq.Operation]:
    return (
        cirq.CNOT(left, right),
        cirq.CNOT(right, left),
        cirq.CNOT(left, right),
    )


def decompose_swaps(circuit: cirq.Circuit) -> cirq.Circuit:
    rewritten = cirq.Circuit()
    for op in circuit.all_operations():
        if isinstance(op.gate, cirq.SwapPowGate):
            rewritten.append(_decomposed_swap(op.qubits[0], op.qubits[1]))
        else:
            rewritten.append(op)
    return rewritten
