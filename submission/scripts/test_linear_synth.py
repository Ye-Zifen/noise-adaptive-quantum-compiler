"""Correctness test for the topology-aware CNOT (linear) synthesizer in compiler.py.

The synthesizer is the high-risk part of the submission, so it is gated at runtime
by a self-check (rebuild the GF(2) map and compare).  This test exercises that
synthesizer directly on many random invertible matrices over random connected
graphs and asserts that (a) every emitted CNOT lies on a graph edge and (b) the
rebuilt linear map exactly equals the input.

Run:  PYTHONPATH=<release_root>/src python test_linear_synth.py
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

import networkx as nx

sys.path.insert(0, str(Path(__file__).resolve().parent))
import compiler as C


def _identity(n):
    return [[1 if i == k else 0 for k in range(n)] for i in range(n)]


def _rand_invertible(n, depth, rng):
    M = _identity(n)
    for _ in range(depth):
        a, b = rng.sample(range(n), 2)
        M[b] = [x ^ y for x, y in zip(M[b], M[a])]
    return M


def _rand_connected_graph(n, extra, rng):
    G = nx.Graph()
    nodes = list(range(n))
    rng.shuffle(nodes)
    for k in range(1, n):
        G.add_edge(nodes[k], nodes[rng.randrange(k)])
    pairs = [(a, b) for a in range(n) for b in range(a + 1, n) if not G.has_edge(a, b)]
    rng.shuffle(pairs)
    for a, b in pairs[:extra]:
        G.add_edge(a, b)
    return G


def main(trials: int = 600) -> int:
    rng = random.Random(2024)
    total_cnots = 0
    for t in range(trials):
        n = rng.randint(3, 10)
        G = _rand_connected_graph(n, rng.randint(0, n), rng)
        A = _rand_invertible(n, rng.randint(1, 5 * n), rng)
        for order in ("sorted", "mindeg"):
            ops = C._synthesize_linear(A, G, order=order)
            assert all(G.has_edge(j, i) for j, i in ops), f"illegal edge (trial {t})"
            assert C._map_from_cnots(ops, n) == A, f"map mismatch (trial {t}, order {order})"
            total_cnots += len(ops)
    print(f"OK: {trials} trials x 2 orders passed; avg CNOTs/synthesis = {total_cnots/(trials*2):.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
