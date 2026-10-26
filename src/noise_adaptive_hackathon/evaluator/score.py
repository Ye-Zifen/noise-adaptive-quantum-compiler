from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CircuitValidation:
    valid: bool
    errors: list[str]


@dataclass(frozen=True)
class SampleResult:
    sample_id: str
    compiler_name: str
    success_rate: float
    shots: int
    correct_shots: int
    depth: int
    two_qubit_gate_count: int
    estimated_log_reliability: float
    compile_time_sec: float
    valid: bool


@dataclass(frozen=True)
class EvaluationSummary:
    compiler_name: str
    mean_success_rate: float
    sample_results: list[SampleResult]
