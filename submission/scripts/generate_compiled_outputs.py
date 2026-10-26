"""Generate per-benchmark compiled outputs for the public set.

For every public benchmark this runs the submission compiler and stores the
evaluator-style ``compiled_circuit.json`` + ``compiled_circuit.layout.json`` in
``submission/results/compiled_outputs/<track>/<name>/``.

Run from the release-bundle root:

    PYTHONPATH=src python submission/scripts/generate_compiled_outputs.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[2]                      # repository root
COMPILER = HERE.parents[1] / "compiler.py"
OUT_ROOT = HERE.parents[1] / "results" / "compiled_outputs"


def main() -> int:
    for track in ("track_a", "track_b"):
        public = ROOT / "benchmarks" / track / "public"
        for bench_dir in sorted(p for p in public.iterdir() if p.is_dir()):
            meta = json.loads((bench_dir / "benchmark.json").read_text())["metadata"]
            backend = (
                ROOT / "backends" / meta["backend_size_class"]
                / f"{meta['backend_snapshot_id']}.json"
            )
            out_dir = OUT_ROOT / track / bench_dir.name
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / "compiled_circuit.json"
            subprocess.run(
                [
                    sys.executable, str(COMPILER),
                    "--circuit", str(bench_dir / "circuit.json"),
                    "--backend", str(backend),
                    "--out", str(out_path),
                ],
                check=True,
            )
            print(f"compiled {track}/{bench_dir.name} -> {out_path.relative_to(HERE.parents[1])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
