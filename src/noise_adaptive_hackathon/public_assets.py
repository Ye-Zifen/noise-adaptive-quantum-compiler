from __future__ import annotations

import json
import shutil
from dataclasses import replace
from pathlib import Path

from noise_adaptive_hackathon.benchmarks.io import write_benchmark
from noise_adaptive_hackathon.benchmarks.track_a import generate_track_a_benchmark
from noise_adaptive_hackathon.benchmarks.track_b import generate_track_b_benchmark
from noise_adaptive_hackathon.formats.backend import CompetitionBackend, TRACK_A_BASIS


def generate_public_assets(root: Path) -> None:
    _clear_stale_assets(root)
    backends_root = root / "backends"
    benchmarks_root = root / "benchmarks"

    for size_class in ("small", "medium", "large"):
        (backends_root / size_class).mkdir(parents=True, exist_ok=True)
    for track in ("track_a", "track_b"):
        (benchmarks_root / track / "public").mkdir(parents=True, exist_ok=True)

    for backend in (
        _build_backend(
            snapshot_id="small_snapshot_a",
            size_class="small",
            num_qubits=7,
            coupling_map=_small_topology(),
            base_two_qubit_error=0.022,
        ),
        _build_backend(
            snapshot_id="medium_snapshot_a",
            size_class="medium",
            num_qubits=16,
            coupling_map=_grid_topology(rows=4, cols=4),
            base_two_qubit_error=0.015,
        ),
        _build_backend(
            snapshot_id="large_snapshot_a",
            size_class="large",
            num_qubits=32,
            coupling_map=_large_sparse_topology(),
            base_two_qubit_error=0.011,
        ),
    ):
        (backends_root / backend.size_class / f"{backend.snapshot_id}.json").write_text(
            backend.json(indent=2),
            encoding="utf-8",
        )

    _write_public_track(
        root=root,
        track="track_a",
        backend_snapshot_id="medium_snapshot_a",
        backend_size_class="medium",
        benchmarks=(
            generate_track_a_benchmark(family="bv", logical_qubits=6, seed=7, sample_id="track_a_001"),
            generate_track_a_benchmark(family="hs", logical_qubits=6, seed=11, sample_id="track_a_002"),
            generate_track_a_benchmark(family="toffoli", logical_qubits=6, seed=17, sample_id="track_a_003"),
            generate_track_a_benchmark(family="fredkin", logical_qubits=6, seed=19, sample_id="track_a_004"),
            generate_track_a_benchmark(family="peres", logical_qubits=6, seed=23, sample_id="track_a_005"),
            generate_track_a_benchmark(family="or", logical_qubits=6, seed=29, sample_id="track_a_006"),
            generate_track_a_benchmark(family="adder", logical_qubits=6, seed=31, sample_id="track_a_007"),
            generate_track_a_benchmark(family="structured_random", logical_qubits=7, seed=37, sample_id="track_a_008"),
        ),
    )
    _write_public_track(
        root=root,
        track="track_b",
        backend_snapshot_id="large_snapshot_a",
        backend_size_class="large",
        benchmarks=(
            generate_track_b_benchmark(num_qubits=16, depth=16, seed=17, family="ghz", sample_id="track_b_001"),
            generate_track_b_benchmark(num_qubits=24, depth=28, seed=19, family="parity", sample_id="track_b_002"),
        ),
    )


def _clear_stale_assets(root: Path) -> None:
    for stale in (
        root / "benchmarks" / "track_a" / "private",
        root / "benchmarks" / "track_b" / "private",
        root / "benchmarks" / "track_a" / "private_manifest.json",
        root / "benchmarks" / "track_b" / "private_manifest.json",
    ):
        if stale.is_dir():
            shutil.rmtree(stale)
        elif stale.exists():
            stale.unlink()


def _write_public_track(
    root: Path,
    track: str,
    backend_snapshot_id: str,
    backend_size_class: str,
    benchmarks,
) -> None:
    split_root = root / "benchmarks" / track / "public"
    if split_root.exists():
        shutil.rmtree(split_root)
    split_root.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, object] = {
        "track": track,
        "split": "public",
        "backend_snapshot_id": backend_snapshot_id,
        "backend_size_class": backend_size_class,
        "benchmarks": [],
    }
    for benchmark in benchmarks:
        enriched = replace(
            benchmark,
            metadata={
                **benchmark.metadata,
                "split": "public",
                "backend_snapshot_id": backend_snapshot_id,
                "backend_size_class": backend_size_class,
            },
        )
        write_benchmark(enriched, split_root / enriched.name)
        manifest["benchmarks"].append(
            {
                "name": enriched.name,
                "family": enriched.family,
                "backend_snapshot_id": backend_snapshot_id,
                "backend_size_class": backend_size_class,
            }
        )
    (root / "benchmarks" / track / "public_manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )


def _build_backend(
    snapshot_id: str,
    size_class: str,
    num_qubits: int,
    coupling_map: list[tuple[int, int]],
    base_two_qubit_error: float,
) -> CompetitionBackend:
    low_noise_qubits = {0, 1, 4, 5}
    bad_qubits = {num_qubits // 2, min(num_qubits - 1, num_qubits // 2 + 3)}
    bad_couplers = {tuple(sorted(coupling_map[len(coupling_map) // 3])), tuple(sorted(coupling_map[-2]))}
    two_qubit_error = {}
    for control, target in coupling_map:
        edge = tuple(sorted((control, target)))
        error = base_two_qubit_error + 0.0012 * ((control * 7 + target * 3) % 6)
        if control in low_noise_qubits and target in low_noise_qubits:
            error *= 0.45
        if edge in bad_couplers:
            error *= 2.6
        two_qubit_error[f"{control}-{target}"] = min(error, 0.065)

    readout_error = {}
    for qubit in range(num_qubits):
        error = 0.008 + 0.002 * ((qubit * 5) % 7)
        if qubit in low_noise_qubits:
            error *= 0.55
        if qubit in bad_qubits:
            error *= 3.0
        readout_error[str(qubit)] = min(error, 0.085)

    return CompetitionBackend.parse_obj(
        {
            "schema_version": "2.0",
            "snapshot_id": snapshot_id,
            "size_class": size_class,
            "num_qubits": num_qubits,
            "basis_gates": list(TRACK_A_BASIS),
            "coupling_map": [list(edge) for edge in coupling_map],
            "two_qubit_error": two_qubit_error,
            "readout_error": readout_error,
            "single_qubit_error": 0.001,
        }
    )


def _small_topology() -> list[tuple[int, int]]:
    return [(0, 1), (1, 2), (2, 3), (2, 4), (4, 5), (4, 6)]


def _grid_topology(rows: int, cols: int) -> list[tuple[int, int]]:
    edges: list[tuple[int, int]] = []
    for row in range(rows):
        for col in range(cols):
            node = row * cols + col
            if col + 1 < cols:
                edges.append((node, node + 1))
            if row + 1 < rows:
                edges.append((node, node + cols))
    return edges


def _large_sparse_topology() -> list[tuple[int, int]]:
    edges = _grid_topology(rows=4, cols=8)
    extra = [(1, 10), (5, 14), (8, 17), (12, 21), (18, 27), (21, 30)]
    return sorted(set(edges + extra))
