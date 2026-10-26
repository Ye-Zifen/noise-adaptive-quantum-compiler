from __future__ import annotations

import argparse
from pathlib import Path

import cirq
import networkx as nx

from noise_adaptive_hackathon.baseline.common import decompose_swaps
from noise_adaptive_hackathon.evaluator.equivalence import write_layout_sidecar
from noise_adaptive_hackathon.formats.backend import CompetitionBackend


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cirq RouteCQC baseline compiler for the hackathon contract.")
    parser.add_argument("--circuit", required=True, type=Path)
    parser.add_argument("--backend", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=0, help="Accepted for interface compatibility; RouteCQC is deterministic here.")
    return parser


def compile_with_cirq_route_cqc(
    circuit: cirq.Circuit,
    backend: CompetitionBackend,
) -> tuple[cirq.Circuit, dict[cirq.LineQubit, int]]:
    physical_qubits = tuple(cirq.LineQubit.range(backend.num_qubits))
    device_graph = nx.Graph()
    device_graph.add_nodes_from(physical_qubits)
    device_graph.add_edges_from(
        (physical_qubits[left], physical_qubits[right])
        for left, right in backend.coupling_map
    )

    routed, initial_map, _ = cirq.RouteCQC(device_graph).route_circuit(circuit)
    initial_layout = {
        logical: physical.x
        for logical, physical in initial_map.items()
    }
    return decompose_swaps(cirq.Circuit(routed)), initial_layout


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    del args.seed

    circuit = cirq.read_json(args.circuit)
    backend = CompetitionBackend.parse_raw(args.backend.read_text(encoding="utf-8"))
    compiled, initial_layout = compile_with_cirq_route_cqc(circuit, backend)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    cirq.to_json(compiled, args.out)
    write_layout_sidecar(args.out, initial_layout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
