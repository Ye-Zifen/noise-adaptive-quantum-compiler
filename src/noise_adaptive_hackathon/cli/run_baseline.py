from __future__ import annotations

import argparse
from pathlib import Path

import cirq

from noise_adaptive_hackathon.baseline.cirq_cqc import CirqCQCCompiler
from noise_adaptive_hackathon.baseline.movement_aware import MovementAwareCompiler
from noise_adaptive_hackathon.baseline.paper_greedy import PaperGreedyEdgeCompiler, PaperGreedyVertexCompiler
from noise_adaptive_hackathon.baseline.reliability_greedy import ReliabilityGreedyCompiler
from noise_adaptive_hackathon.baseline.vanilla import VanillaCompiler
from noise_adaptive_hackathon.evaluator.equivalence import write_layout_sidecar
from noise_adaptive_hackathon.formats.backend import CompetitionBackend


COMPILERS = {
    "vanilla": VanillaCompiler,
    "movement_aware": MovementAwareCompiler,
    "reliability_greedy": ReliabilityGreedyCompiler,
    "cirq_cqc": CirqCQCCompiler,
    "paper_greedy_vertex": PaperGreedyVertexCompiler,
    "paper_greedy_edge": PaperGreedyEdgeCompiler,
}


def get_compiler(name: str):
    return COMPILERS[name]()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="运行一个内置双赛道 baseline 编译器。")
    parser.add_argument("--compiler", required=True, choices=sorted(COMPILERS))
    parser.add_argument("--circuit", required=True, type=Path)
    parser.add_argument("--backend", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=7)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    compiler = get_compiler(args.compiler)
    backend = CompetitionBackend.parse_raw(args.backend.read_text(encoding="utf-8"))
    circuit = cirq.read_json(args.circuit)
    compiled = compiler.compile(circuit, backend, seed=args.seed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    cirq.to_json(compiled, args.out)
    write_layout_sidecar(args.out, _compiler_initial_layout(compiler, circuit, backend))
    return 0


def _compiler_initial_layout(compiler, circuit: cirq.Circuit, backend: CompetitionBackend) -> dict:
    layout = getattr(compiler, "last_initial_layout", None)
    if layout is not None:
        return layout
    if hasattr(compiler, "initial_layout"):
        return compiler.initial_layout(circuit, backend)
    logical_qubits = sorted(circuit.all_qubits(), key=lambda qubit: qubit.x)
    return {qubit: qubit.x for qubit in logical_qubits}


if __name__ == "__main__":
    raise SystemExit(main())
