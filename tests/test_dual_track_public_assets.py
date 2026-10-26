from __future__ import annotations

import json
from pathlib import Path

from noise_adaptive_hackathon.formats.backend import CompetitionBackend
from noise_adaptive_hackathon.public_assets import generate_public_assets
from noise_adaptive_hackathon.public_eval import run_public_eval


def test_generate_public_assets_is_participant_only(tmp_path: Path) -> None:
    generate_public_assets(tmp_path)

    assert (tmp_path / "benchmarks" / "track_a" / "public").exists()
    assert (tmp_path / "benchmarks" / "track_b" / "public").exists()
    assert not (tmp_path / "benchmarks" / "track_a" / "private").exists()
    assert not (tmp_path / "benchmarks" / "track_b" / "private").exists()
    assert not (tmp_path / "benchmarks" / "track_a" / "private_manifest.json").exists()
    assert not (tmp_path / "benchmarks" / "track_b" / "private_manifest.json").exists()

    track_a_names = sorted(path.name for path in (tmp_path / "benchmarks" / "track_a" / "public").iterdir())
    track_b_names = sorted(path.name for path in (tmp_path / "benchmarks" / "track_b" / "public").iterdir())
    assert track_a_names == [f"track_a_{index:03d}" for index in range(1, 9)]
    assert track_b_names == ["track_b_001", "track_b_002"]
    assert all("seed" not in name for name in track_a_names + track_b_names)

    public_manifest = json.loads((tmp_path / "benchmarks" / "track_a" / "public_manifest.json").read_text())
    assert public_manifest["split"] == "public"
    assert {entry["family"] for entry in public_manifest["benchmarks"]} == {
        "adder",
        "bv",
        "fredkin",
        "hs",
        "or",
        "peres",
        "structured_random",
        "toffoli",
    }


def test_generated_backends_are_v2_no_swap_and_heterogeneous(tmp_path: Path) -> None:
    generate_public_assets(tmp_path)
    medium = CompetitionBackend.parse_raw((tmp_path / "backends" / "medium" / "medium_snapshot_a.json").read_text())

    assert medium.schema_version == "2.0"
    assert "swap" not in medium.basis_gates
    assert max(dict(medium.graph().degree()).values()) > 2
    assert len(set(medium.two_qubit_error.values())) > 3
    assert len(set(medium.readout_error.values())) > 3


def test_run_public_eval_scores_all_baselines(tmp_path: Path) -> None:
    generate_public_assets(tmp_path)

    summary = run_public_eval(tmp_path, shots_a=16, shots_b=32)

    assert summary["split"] == "public"
    assert set(summary["tracks"]) == {"track_a", "track_b"}
    assert {entry["name"] for entry in summary["baselines"]} == {
        "vanilla",
        "movement_aware",
        "reliability_greedy",
        "cirq_cqc",
        "paper_greedy_vertex",
        "paper_greedy_edge",
    }
    for entry in summary["baselines"]:
        assert 0.0 <= entry["track_a_score"] <= 1.0
        assert 0.0 <= entry["track_b_score"] <= 1.0
