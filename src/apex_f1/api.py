"""Versioned HTTP API and self-contained pit-wall demo."""
from __future__ import annotations

from dataclasses import asdict
from importlib.resources import files
from typing import Literal

from fastapi import FastAPI, HTTPException, Path
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from apex_f1 import __version__
from apex_f1.historical_import import race_file
from apex_f1.integrations.stratlab import probe_stratlab
from apex_f1.integrations.tum_basic import (
    UpstreamExecutionError,
    UpstreamUnavailable,
    compare_tum_example,
    probe_tum,
)
from apex_f1.llm import (
    LLMNotConfigured,
    LLMSettings,
    LLMUpstreamError,
    explain_snapshot,
)
from apex_f1.opponent import PitModel, model_file
from apex_f1.replay import HistoricalRace
from apex_f1.simulator import RaceState, evaluate_strategies

app = FastAPI(
    title="Apex Intelligence Research API",
    description="Synthetic motorsport scenario evaluation. Not suitable for race operations.",
    version=__version__,
)


class EvaluateRequest(BaseModel):
    total_laps: int = Field(default=57, ge=2, le=100)
    current_lap: int = Field(default=28, ge=1, le=99)
    base_lap_seconds: float = Field(default=93.0, ge=60, le=240)
    current_compound: Literal["SOFT", "MEDIUM", "HARD"] = "MEDIUM"
    current_tyre_age: int = Field(default=16, ge=0, le=100)
    pit_loss_seconds: float = Field(default=22.0, ge=5, le=60)
    safety_car_probability: float = Field(default=0.15, ge=0, le=1)
    trials: int = Field(default=400, ge=20, le=5000)
    seed: int = 7


@app.get("/")
def dashboard() -> FileResponse:
    return FileResponse(str(files("apex_f1").joinpath("static/index.html")))


@app.get("/replay")
def historical_replay_dashboard() -> FileResponse:
    return FileResponse(str(files("apex_f1").joinpath("static/replay.html")))


def _load_local_race(year: int, round_number: int) -> HistoricalRace:
    path = race_file(year, round_number)
    if not path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Historical race missing. Run: apex-f1 import-race --year "
                   f"{year} --round {round_number}",
        )
    try:
        return HistoricalRace.load(path)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        raise HTTPException(status_code=422, detail="Invalid local historical race file") from exc


@app.get("/api/v1/historical/{year}/{round_number}/summary")
def historical_summary(
    year: int = Path(ge=2018, le=2100),
    round_number: int = Path(ge=1, le=30),
) -> dict:
    return _load_local_race(year, round_number).summary()


@app.get("/api/v1/historical/{year}/{round_number}/snapshot/{lap}")
def historical_snapshot(
    year: int = Path(ge=2018, le=2100),
    round_number: int = Path(ge=1, le=30),
    lap: int = Path(ge=1, le=100),
) -> dict:
    try:
        return _load_local_race(year, round_number).snapshot(lap)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


class LLMBriefRequest(BaseModel):
    focus: Literal["overview", "tyres", "pit_activity", "rivals"] = "overview"


@app.get("/api/v1/llm/status")
def llm_status() -> dict:
    """Only opt-in status and the model name, NEVER an API key."""
    return LLMSettings.from_env().public_status()


@app.post("/api/v1/historical/{year}/{round_number}/brief/{lap}")
def historical_llm_brief(
    body: LLMBriefRequest,
    year: int = Path(ge=2018, le=2100),
    round_number: int = Path(ge=1, le=30),
    lap: int = Path(ge=1, le=100),
) -> dict:
    """Human-triggered, historical-only LLM call with minimum as-of snapshot."""
    settings = LLMSettings.from_env()
    if not settings.configured():
        raise HTTPException(status_code=503, detail="LLM disabled or not configured on server")
    try:
        snapshot = _load_local_race(year, round_number).snapshot(lap)
        return explain_snapshot(snapshot, body.focus, settings)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LLMNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except LLMUpstreamError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/v1/opponent/status")
def opponent_model_status() -> dict:
    path = model_file()
    if not path.is_file():
        return {
            "configured": False,
            "mode": "NO_LOCAL_PIT_BASELINE",
            "setup": "Import training races and run apex-f1 fit-pit-model",
        }
    try:
        model = PitModel.load(path)
    except (ValueError, TypeError, KeyError, OSError) as exc:
        raise HTTPException(status_code=422, detail="Invalid local pit model") from exc
    return {
        "configured": True,
        "mode": "HISTORICAL_EMPIRICAL_PIT_WINDOW_BASELINE",
        "model_version": model.version,
        "training_races": model.training_races,
        "training_example_count": model.example_count,
        "horizon_driver_laps": model.horizon,
        "validated_on_holdout": False,
        "note": "Only model presence; see offline backtest results before claims.",
    }


@app.get("/api/v1/historical/{year}/{round_number}/opponent-pit/{lap}")
def opponent_pit_window(
    year: int = Path(ge=2018, le=2100),
    round_number: int = Path(ge=1, le=30),
    lap: int = Path(ge=1, le=100),
) -> dict:
    """Read a pre-fitted local baseline. No training, future data or LLM calls."""
    path = model_file()
    if not path.is_file():
        raise HTTPException(
            status_code=503,
            detail="Train from other historical races first: apex-f1 fit-pit-model",
        )
    try:
        model = PitModel.load(path)
        snapshot = _load_local_race(year, round_number).snapshot(lap)
        return model.predict_snapshot(snapshot)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (TypeError, KeyError, OSError) as exc:
        raise HTTPException(status_code=422, detail="Invalid local pit model") from exc


@app.get("/integrations")
def integrations_dashboard() -> FileResponse:
    return FileResponse(str(files("apex_f1").joinpath("static/integrations.html")))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__, "mode": "research"}


@app.get("/api/v1/demo/state")
def demo_state() -> dict:
    return {"synthetic": True, "state": asdict(RaceState())}


@app.get("/api/v1/demo/evaluation")
def demo_evaluation() -> dict:
    return evaluate_strategies(RaceState())


@app.post("/api/v1/strategy/evaluate")
def evaluate(body: EvaluateRequest) -> dict:
    state_fields = body.model_dump(exclude={"trials", "seed"})
    try:
        return evaluate_strategies(RaceState(**state_fields), trials=body.trials, seed=body.seed)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


class TUMResearchRequest(BaseModel):
    pit_laps: list[int] = Field(default_factory=lambda: [18, 25, 32], min_length=1, max_length=10)
    start_compound: Literal["A3", "A4", "A5"] = "A4"
    next_compound: Literal["A3", "A4", "A5"] = "A3"


@app.get("/api/v1/integrations/status")
def integration_status() -> dict:
    return {
        "tum": probe_tum(),
        "stratlab": probe_stratlab(),
        "note": "Source presence and source contract are not runtime execution checks.",
    }


@app.post("/api/v1/integrations/tum/compare")
def tum_compare(body: TUMResearchRequest) -> dict:
    """Execute the pinned upstream TUM basic model; historical example only."""
    try:
        return compare_tum_example(
            body.pit_laps, body.start_compound, body.next_compound
        )
    except UpstreamUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except UpstreamExecutionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
