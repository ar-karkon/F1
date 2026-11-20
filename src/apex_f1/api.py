"""Versioned HTTP API and self-contained pit-wall demo."""
from __future__ import annotations

from dataclasses import asdict
from importlib.resources import files
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from apex_f1 import __version__
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
