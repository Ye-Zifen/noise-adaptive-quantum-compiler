from __future__ import annotations

import json
import sys
from pathlib import Path

from noise_adaptive_hackathon.cli.evaluate_submission import main as evaluate_submission_main
from noise_adaptive_hackathon.cli.gen_dataset import main as gen_dataset_main
from noise_adaptive_hackathon.cli.run_baseline import main as run_baseline_main


def test_cli_workflow(tmp_path: Path) -> None:
    compiled_path = tmp_path / "compiled_circuit.json"
    summary_path = tmp_path / "summary.json"

    assert gen_dataset_main(["--out", str(tmp_path)]) == 0

    backend_path = tmp_path / "backends" / "medium" / "medium_snapshot_a.json"
    sample_dir = tmp_path / "benchmarks" / "track_a" / "public" / "track_a_001"
    assert run_baseline_main(
        [
            "--compiler",
            "reliability_greedy",
            "--circuit",
            str(sample_dir / "circuit.json"),
            "--backend",
            str(backend_path),
            "--out",
            str(compiled_path),
        ]
    ) == 0
    assert compiled_path.exists()

    assert evaluate_submission_main(
        [
            "--root",
            str(tmp_path),
            "--shots-a",
            "16",
            "--shots-b",
            "32",
            "--seed",
            "17",
            "--out",
            str(summary_path),
            "--command",
            sys.executable,
            "-m",
            "noise_adaptive_hackathon.cli.run_baseline",
            "--compiler",
            "reliability_greedy",
        ]
    ) == 0

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["compiler_name"] == "submission"
    assert summary["split"] == "public"
    assert summary["track_a_score"] > 0.0
    assert summary["track_b_score"] > 0.0
    assert summary["final_score"] > 0.0
    assert {"shots", "correct_shots", "two_qubit_gate_count", "estimated_log_reliability"} <= set(summary["sample_results"][0])


def test_evaluator_rejects_invalid_output(tmp_path: Path) -> None:
    assert gen_dataset_main(["--out", str(tmp_path)]) == 0
    bad_compiler = tmp_path / "bad_compiler.py"
    bad_compiler.write_text(
        "\n".join(
            [
                "import argparse",
                "import cirq",
                "parser = argparse.ArgumentParser()",
                "parser.add_argument('--circuit')",
                "parser.add_argument('--backend')",
                "parser.add_argument('--out')",
                "args = parser.parse_args()",
                "source = cirq.read_json(args.circuit)",
                "qubits = sorted(source.all_qubits())",
                "cirq.to_json(cirq.Circuit(cirq.measure(*qubits, key='not_z')), args.out)",
            ]
        ),
        encoding="utf-8",
    )
    summary_path = tmp_path / "bad_summary.json"

    assert evaluate_submission_main(
        [
            "--root",
            str(tmp_path),
            "--shots-a",
            "8",
            "--shots-b",
            "8",
            "--out",
            str(summary_path),
            "--command",
            sys.executable,
            str(bad_compiler),
        ]
    ) == 0

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["final_score"] == 0.0
    assert all(not sample["valid"] for sample in summary["sample_results"])


def test_evaluator_reports_compiler_stderr(tmp_path: Path) -> None:
    assert gen_dataset_main(["--out", str(tmp_path)]) == 0
    failing_compiler = tmp_path / "failing_compiler.py"
    failing_compiler.write_text(
        "\n".join(
            [
                "import argparse",
                "parser = argparse.ArgumentParser()",
                "parser.add_argument('--circuit')",
                "parser.add_argument('--backend')",
                "parser.add_argument('--out')",
                "parser.parse_args()",
                "raise RuntimeError('diagnostic text from compiler')",
            ]
        ),
        encoding="utf-8",
    )
    summary_path = tmp_path / "failing_summary.json"

    assert evaluate_submission_main(
        [
            "--root",
            str(tmp_path),
            "--shots-a",
            "1",
            "--shots-b",
            "1",
            "--out",
            str(summary_path),
            "--command",
            sys.executable,
            str(failing_compiler),
        ]
    ) == 0

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    first_errors = summary["sample_results"][0]["validation_errors"]
    assert "compiler exited with status 1" in first_errors
    assert any("diagnostic text from compiler" in error for error in first_errors)


def test_evaluator_isolates_submission_inputs(tmp_path: Path) -> None:
    assert gen_dataset_main(["--out", str(tmp_path)]) == 0
    spy_compiler = tmp_path / "spy_compiler.py"
    spy_compiler.write_text(
        "\n".join(
            [
                "import argparse",
                "from pathlib import Path",
                "import cirq",
                "from noise_adaptive_hackathon.baseline.reliability_greedy import ReliabilityGreedyCompiler",
                "from noise_adaptive_hackathon.evaluator.equivalence import write_layout_sidecar",
                "from noise_adaptive_hackathon.formats.backend import CompetitionBackend",
                "parser = argparse.ArgumentParser()",
                "parser.add_argument('--circuit')",
                "parser.add_argument('--backend')",
                "parser.add_argument('--out')",
                "args = parser.parse_args()",
                "if Path(args.circuit).with_name('benchmark.json').exists():",
                "    raise SystemExit('benchmark metadata leaked')",
                "backend = CompetitionBackend.parse_raw(Path(args.backend).read_text())",
                "compiler = ReliabilityGreedyCompiler()",
                "compiled = compiler.compile(cirq.read_json(args.circuit), backend)",
                "cirq.to_json(compiled, args.out)",
                "write_layout_sidecar(Path(args.out), compiler.last_initial_layout)",
            ]
        ),
        encoding="utf-8",
    )
    summary_path = tmp_path / "spy_summary.json"

    assert evaluate_submission_main(
        [
            "--root",
            str(tmp_path),
            "--shots-a",
            "8",
            "--shots-b",
            "8",
            "--out",
            str(summary_path),
            "--command",
            sys.executable,
            str(spy_compiler),
        ]
    ) == 0

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["track_a_score"] > 0.0
    assert summary["track_b_score"] > 0.0


def test_evaluator_rejects_answer_preparation_shortcut(tmp_path: Path) -> None:
    assert gen_dataset_main(["--out", str(tmp_path)]) == 0
    shortcut_compiler = tmp_path / "answer_shortcut.py"
    shortcut_compiler.write_text(
        "\n".join(
            [
                "import argparse",
                "from pathlib import Path",
                "import cirq",
                "from noise_adaptive_hackathon.evaluator.equivalence import write_layout_sidecar",
                "parser = argparse.ArgumentParser()",
                "parser.add_argument('--circuit')",
                "parser.add_argument('--backend')",
                "parser.add_argument('--out')",
                "args = parser.parse_args()",
                "source = cirq.read_json(args.circuit)",
                "logical_qubits = sorted(source.all_qubits(), key=lambda qubit: qubit.x)",
                "sample = cirq.Simulator(seed=123).run(source, repetitions=1).measurements['z'][0]",
                "physical_qubits = cirq.LineQubit.range(len(sample))",
                "ops = [cirq.X(qubit) for qubit, bit in zip(physical_qubits, sample) if int(bit)]",
                "ops.append(cirq.measure(*physical_qubits, key='z'))",
                "cirq.to_json(cirq.Circuit(ops), args.out)",
                "write_layout_sidecar(Path(args.out), {qubit: index for index, qubit in enumerate(logical_qubits)})",
            ]
        ),
        encoding="utf-8",
    )
    summary_path = tmp_path / "answer_shortcut_summary.json"

    assert evaluate_submission_main(
        [
            "--root",
            str(tmp_path),
            "--shots-a",
            "8",
            "--shots-b",
            "8",
            "--out",
            str(summary_path),
            "--command",
            sys.executable,
            str(shortcut_compiler),
        ]
    ) == 0

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    invalid = [sample for sample in summary["sample_results"] if not sample["valid"]]
    assert summary["final_score"] < 0.2
    assert len(invalid) >= 9
    assert any("compiler equivalence check failed" in error for sample in invalid for error in sample["validation_errors"])
