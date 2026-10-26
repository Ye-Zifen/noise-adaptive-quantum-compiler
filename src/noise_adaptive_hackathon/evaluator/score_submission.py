from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SubmissionScore:
    track_a_weight: float
    track_b_weight: float
    track_a_score: float
    track_b_score: float
    final_score: float


def score_submission(track_a_score: float, track_b_score: float) -> SubmissionScore:
    track_a_weight = 0.75
    track_b_weight = 0.25
    final = track_a_weight * track_a_score + track_b_weight * track_b_score
    return SubmissionScore(
        track_a_weight=track_a_weight,
        track_b_weight=track_b_weight,
        track_a_score=track_a_score,
        track_b_score=track_b_score,
        final_score=final,
    )
