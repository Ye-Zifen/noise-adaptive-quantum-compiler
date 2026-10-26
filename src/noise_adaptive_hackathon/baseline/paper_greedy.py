from __future__ import annotations

import math

import cirq
import networkx as nx

from noise_adaptive_hackathon.formats.backend import CompetitionBackend

from .common import BaseCompetitionCompiler, build_interaction_graph


class PaperGreedyVertexCompiler(BaseCompetitionCompiler):
    name = "paper_greedy_vertex"

    def initial_layout(self, circuit: cirq.Circuit, backend: CompetitionBackend) -> dict[cirq.LineQubit, int]:
        return paper_greedy_vertex_layout(circuit, backend)

    def route_path(self, source: int, target: int, backend: CompetitionBackend) -> list[int]:
        return backend.most_reliable_path(source, target)


class PaperGreedyEdgeCompiler(BaseCompetitionCompiler):
    name = "paper_greedy_edge"

    def initial_layout(self, circuit: cirq.Circuit, backend: CompetitionBackend) -> dict[cirq.LineQubit, int]:
        return paper_greedy_edge_layout(circuit, backend)

    def route_path(self, source: int, target: int, backend: CompetitionBackend) -> list[int]:
        return backend.most_reliable_path(source, target)


def paper_greedy_vertex_layout(
    circuit: cirq.Circuit,
    backend: CompetitionBackend,
) -> dict[cirq.LineQubit, int]:
    program = build_interaction_graph(circuit)
    hardware = backend.graph()
    reliability_lengths = dict(nx.all_pairs_dijkstra_path_length(hardware, weight="cost"))
    weighted_degree = _weighted_degrees(program)
    unplaced = set(program.nodes)
    available = set(hardware.nodes)
    layout: dict[cirq.LineQubit, int] = {}

    first_logical = max(unplaced, key=lambda q: (program.degree(q), weighted_degree[q], -q.x))
    max_hardware_degree = max(dict(hardware.degree()).values())
    first_candidates = [node for node in available if hardware.degree(node) == max_hardware_degree]
    first_physical = max(
        first_candidates,
        key=lambda node: (
            hardware.nodes[node]["readout_reliability"],
            _incident_reliability(hardware, node),
            -node,
        ),
    )
    _place(layout, unplaced, available, first_logical, first_physical)

    while unplaced:
        logical = max(
            unplaced,
            key=lambda q: (
                sum(program.edges[q, n]["weight"] for n in program.neighbors(q) if n in layout),
                weighted_degree[q],
                program.degree(q),
                -q.x,
            ),
        )
        placed_neighbors = [(n, program.edges[logical, n]["weight"]) for n in program.neighbors(logical) if n in layout]
        physical = max(
            available,
            key=lambda node: (
                _path_score(node, placed_neighbors, layout, reliability_lengths),
                hardware.nodes[node]["readout_reliability"],
                hardware.degree(node),
                -node,
            ),
        )
        _place(layout, unplaced, available, logical, physical)
    return layout


def paper_greedy_edge_layout(
    circuit: cirq.Circuit,
    backend: CompetitionBackend,
) -> dict[cirq.LineQubit, int]:
    program = build_interaction_graph(circuit)
    hardware = backend.graph()
    reliability_lengths = dict(nx.all_pairs_dijkstra_path_length(hardware, weight="cost"))
    weighted_degree = _weighted_degrees(program)
    unplaced = set(program.nodes)
    available = set(hardware.nodes)
    layout: dict[cirq.LineQubit, int] = {}

    logical_edges = sorted(
        program.edges(data=True),
        key=lambda edge: (
            edge[2]["weight"],
            weighted_degree[edge[0]] + weighted_degree[edge[1]],
            program.degree(edge[0]) + program.degree(edge[1]),
            -edge[0].x,
            -edge[1].x,
        ),
        reverse=True,
    )
    for left, right, _ in logical_edges:
        if left in layout and right in layout:
            continue
        if left not in layout and right not in layout:
            physical_left, physical_right = _best_available_hardware_edge(hardware, available)
            ordered = sorted(
                ((left, physical_left), (right, physical_right)),
                key=lambda item: (weighted_degree[item[0]], program.degree(item[0]), -item[0].x),
                reverse=True,
            )
            _place(layout, unplaced, available, ordered[0][0], ordered[0][1])
            _place(layout, unplaced, available, ordered[1][0], ordered[1][1])
            continue

        _, unmapped = (left, right) if left in layout else (right, left)
        placed_neighbors = [(n, program.edges[unmapped, n]["weight"]) for n in program.neighbors(unmapped) if n in layout]
        physical = max(
            available,
            key=lambda node: (
                _path_score(node, placed_neighbors, layout, reliability_lengths),
                hardware.nodes[node]["readout_reliability"],
                hardware.degree(node),
                -node,
            ),
        )
        _place(layout, unplaced, available, unmapped, physical)

    while unplaced:
        logical = max(unplaced, key=lambda q: (weighted_degree[q], program.degree(q), -q.x))
        placed_neighbors = [(n, program.edges[logical, n]["weight"]) for n in program.neighbors(logical) if n in layout]
        physical = max(
            available,
            key=lambda node: (
                _path_score(node, placed_neighbors, layout, reliability_lengths),
                hardware.nodes[node]["readout_reliability"],
                hardware.degree(node),
                -node,
            ),
        )
        _place(layout, unplaced, available, logical, physical)
    return layout


def _place(
    layout: dict[cirq.LineQubit, int],
    unplaced: set[cirq.LineQubit],
    available: set[int],
    logical: cirq.LineQubit,
    physical: int,
) -> None:
    layout[logical] = physical
    unplaced.remove(logical)
    available.remove(physical)


def _weighted_degrees(program: nx.Graph) -> dict[cirq.LineQubit, int]:
    return {
        node: sum(data["weight"] for _, _, data in program.edges(node, data=True))
        for node in program.nodes
    }


def _incident_reliability(hardware: nx.Graph, node: int) -> float:
    return sum(hardware.edges[node, neighbor]["reliability"] for neighbor in hardware.neighbors(node))


def _best_available_hardware_edge(hardware: nx.Graph, available: set[int]) -> tuple[int, int]:
    edge = max(
        (edge for edge in hardware.edges if edge[0] in available and edge[1] in available),
        key=lambda edge: (
            hardware.edges[edge]["reliability"],
            hardware.nodes[edge[0]]["readout_reliability"] + hardware.nodes[edge[1]]["readout_reliability"],
            hardware.degree(edge[0]) + hardware.degree(edge[1]),
            -edge[0],
            -edge[1],
        ),
    )
    return edge


def _path_score(
    node: int,
    placed_neighbors: list[tuple[cirq.LineQubit, int]],
    layout: dict[cirq.LineQubit, int],
    reliability_lengths: dict[int, dict[int, float]],
) -> float:
    if not placed_neighbors:
        return 0.0
    return sum(
        weight * _path_reliability(node, layout[neighbor], reliability_lengths)
        for neighbor, weight in placed_neighbors
    )


def _path_reliability(
    left: int,
    right: int,
    reliability_lengths: dict[int, dict[int, float]],
) -> float:
    return math.exp(-reliability_lengths[left][right])
