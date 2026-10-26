from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MeasurementRunResult:
    success_rate: float
    correct_shots: int
    total_shots: int
