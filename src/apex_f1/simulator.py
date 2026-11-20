"""A transparent, offline, *toy* Monte Carlo race-strategy baseline.

The parameters below are illustrative constants, NOT fitted F1 telemetry or a
validated physical model. No finishing-position or podium claims are produced.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import random
from statistics import mean
from typing import Any

# Illustrative lap pace delta (seconds) and degradation per tyre-lap.
TYRES: dict[str, tuple[float, float]] = {
    "SOFT": (-0.55, 0.135),
    "MEDIUM": (0.0, 0.088),
    "HARD": (0.52, 0.052),
}


@dataclass(frozen=True)
class RaceState:
    total_laps: int = 57
    current_lap: int = 28
    base_lap_seconds: float = 93.0
    current_compound: str = "MEDIUM"
    current_tyre_age: int = 16
    pit_loss_seconds: float = 22.0
    safety_car_probability: float = 0.15

    def validate(self) -> None:
        if not 1 <= self.current_lap < self.total_laps <= 100:
            raise ValueError("Require 1 <= current_lap < total_laps <= 100")
        if self.current_compound not in TYRES:
            raise ValueError("Unsupported tyre compound")
        if not 0 <= self.current_tyre_age <= 100:
            raise ValueError("current_tyre_age must be between 0 and 100")
        if not 60 <= self.base_lap_seconds <= 240:
            raise ValueError("base_lap_seconds must be between 60 and 240")
        if not 5 <= self.pit_loss_seconds <= 60:
            raise ValueError("pit_loss_seconds must be between 5 and 60")
        if not 0 <= self.safety_car_probability <= 1:
            raise ValueError("safety_car_probability must be between 0 and 1")


@dataclass(frozen=True)
class Plan:
    key: str
    label: str
    pit_lap: int | None
    next_compound: str | None


def candidate_plans(state: RaceState) -> list[Plan]:
    """Produce consistent, interpretable counterfactual strategies."""
    next_lap = state.current_lap + 1
    late_lap = min(state.current_lap + 5, state.total_laps)
    return [
        Plan("pit_now_hard", "Pit next lap · HARD", next_lap, "HARD"),
        Plan("pit_later_hard", "Pit in five laps · HARD", late_lap, "HARD"),
        Plan("stay_out", "Stay out · current compound", None, None),
    ]


def _simulate(
    state: RaceState,
    plan: Plan,
    noise_by_lap: list[float],
    safety_car_lap: int | None,
    pit_variation: float,
) -> float:
    elapsed = 0.0
    compound = state.current_compound
    age = state.current_tyre_age

    for i, lap in enumerate(range(state.current_lap + 1, state.total_laps + 1)):
        if plan.pit_lap == lap:
            # Simplification: a pit stop near a safety car suffers reduced loss.
            sc_discount = 0.65 if safety_car_lap is not None and abs(safety_car_lap - lap) <= 1 else 1.0
            elapsed += max(0.0, state.pit_loss_seconds * sc_discount + pit_variation)
            compound = plan.next_compound or compound
            age = 0

        pace_delta, wear = TYRES[compound]
        elapsed += state.base_lap_seconds + pace_delta + wear * age + noise_by_lap[i]
        # A neutralization affects every option equally in this toy model.
        if safety_car_lap == lap:
            elapsed += 12.0
        age += 1
    return elapsed


def _percentile(sorted_values: list[float], fraction: float) -> float:
    """Linear interpolated empirical percentile, no external dependency."""
    p = (len(sorted_values) - 1) * fraction
    lo = int(p)
    hi = min(lo + 1, len(sorted_values) - 1)
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (p - lo)


def evaluate_strategies(
    state: RaceState,
    trials: int = 400,
    seed: int = 7,
) -> dict[str, Any]:
    """Paired Monte Carlo evaluation under *shared* sampled race conditions.

    Probabilities refer ONLY to which toy option has the shortest modelled
    remaining elapsed time, not to win/podium/position probabilities.
    """
    state.validate()
    if not 20 <= trials <= 5000:
        raise ValueError("trials must be between 20 and 5000")

    plans = candidate_plans(state)
    values: dict[str, list[float]] = {plan.key: [] for plan in plans}
    best_count = {plan.key: 0 for plan in plans}
    rng = random.Random(seed)
    remaining = state.total_laps - state.current_lap

    for _ in range(trials):
        shared_noise = [rng.gauss(0, 0.18) for _ in range(remaining)]
        sc_lap = (
            rng.randint(state.current_lap + 1, state.total_laps)
            if rng.random() < state.safety_car_probability
            else None
        )
        pit_variation = rng.gauss(0, 0.65)
        times = {
            plan.key: _simulate(state, plan, shared_noise, sc_lap, pit_variation)
            for plan in plans
        }
        for key, value in times.items():
            values[key].append(value)
        best_count[min(times, key=times.get)] += 1

    expected = {key: mean(results) for key, results in values.items()}
    lowest_expected = min(expected.values())
    rows = []
    for plan in plans:
        samples = sorted(values[plan.key])
        rows.append({
            "key": plan.key,
            "label": plan.label,
            "pit_lap": plan.pit_lap,
            "next_compound": plan.next_compound,
            "expected_remaining_seconds": round(expected[plan.key], 3),
            "delta_to_best_seconds": round(expected[plan.key] - lowest_expected, 3),
            "p10_remaining_seconds": round(_percentile(samples, 0.1), 3),
            "p90_remaining_seconds": round(_percentile(samples, 0.9), 3),
            "probability_fastest_of_candidates": round(best_count[plan.key] / trials, 4),
        })
    rows.sort(key=lambda row: (row["expected_remaining_seconds"], row["key"]))

    return {
        "mode": "SYNTHETIC_UNVALIDATED",
        "race_state": asdict(state),
        "trials": trials,
        "seed": seed,
        "recommended_plan_key": rows[0]["key"],
        "strategies": rows,
        "assumptions": [
            "All lap-time and tyre-wear constants are illustrative, not fitted to real racing data.",
            "This is NOT a regulation-aware, track-aware, or traffic-aware race strategy model.",
            "Safety car is a single sampled event with simplified pit-loss discount.",
            "The fastest-candidate probability is NOT a race-win probability.",
            "No 2026 active-aero, energy-management, tyre-allocation or compulsory-compound rules.",
        ],
    }
