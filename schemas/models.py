"""S-01 shared contracts. A/B/C must serialize against these models."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "1.0.0"


class CoordinateMode(str, Enum):
    GROUND_METRIC = "GROUND_METRIC"
    IMAGE_NORMALIZED = "IMAGE_NORMALIZED"
    IMAGE_PIXEL = "IMAGE_PIXEL"


class AgentClass(str, Enum):
    person = "person"
    forklift = "forklift"


class JobStatus(str, Enum):
    pending = "pending"
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class StrategyId(str, Enum):
    KEEP = "KEEP"
    F_SLOW_75 = "F_SLOW_75"
    F_SLOW_50 = "F_SLOW_50"
    F_STOP = "F_STOP"
    P_YIELD = "P_YIELD"
    DETOUR = "DETOUR"


class ReviewDecision(str, Enum):
    confirm = "confirm"
    reject = "reject"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class VersionedEnvelope(StrictModel):
    schema_version: str = Field(default=SCHEMA_VERSION)
    run_id: str
    scenario_id: str | None = None
    model_version: str | None = None
    risk_rule_version: str | None = None
    coordinate_mode: CoordinateMode
    timestamp_ms: int = Field(ge=0)

    @model_validator(mode="after")
    def schema_version_frozen(self) -> VersionedEnvelope:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {SCHEMA_VERSION}")
        return self


def _forbid_metric_fields(
    coordinate_mode: CoordinateMode,
    speed_mps: float | None,
    heading_rad: float | None,
    position_unit: str | None,
) -> None:
    metric = coordinate_mode is CoordinateMode.GROUND_METRIC
    if not metric and position_unit == "m":
        raise ValueError("uncalibrated output cannot use unit=m")
    if not metric and speed_mps is not None:
        raise ValueError("speed_mps requires coordinate_mode=GROUND_METRIC")
    if not metric and heading_rad is not None:
        raise ValueError("heading_rad requires coordinate_mode=GROUND_METRIC")
    if metric and position_unit not in (None, "m"):
        raise ValueError("GROUND_METRIC position_unit must be m")


class BBoxXYXY(StrictModel):
    x1: float
    y1: float
    x2: float
    y2: float
    unit: str = Field(description="px for detections; never m")

    @model_validator(mode="after")
    def pixel_unit(self) -> BBoxXYXY:
        if self.unit != "px":
            raise ValueError("bbox unit must be px")
        if self.x2 <= self.x1 or self.y2 <= self.y1:
            raise ValueError("bbox must be a valid xyxy rectangle")
        return self


class Detection(StrictModel):
    class_name: AgentClass = Field(alias="class")
    bbox: BBoxXYXY
    conf: float = Field(ge=0, le=1)
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class DetectionFrame(VersionedEnvelope):
    image_id: str
    image_width: int = Field(gt=0)
    image_height: int = Field(gt=0)
    detections: list[Detection]
    coordinate_mode: CoordinateMode = CoordinateMode.IMAGE_PIXEL

    @model_validator(mode="after")
    def detection_mode(self) -> DetectionFrame:
        if self.coordinate_mode is not CoordinateMode.IMAGE_PIXEL:
            raise ValueError("DetectionFrame coordinate_mode must be IMAGE_PIXEL")
        return self


class TrackPoint(StrictModel):
    timestamp_ms: int = Field(ge=0)
    x: float
    y: float
    position_unit: str
    speed_mps: float | None = None
    heading_rad: float | None = None
    bbox: BBoxXYXY | None = None
    center: tuple[float, float] | None = None
    foot: tuple[float, float] | None = None
    conf: float | None = Field(default=None, ge=0, le=1)
    observed: bool = True

    def validate_against_mode(self, mode: CoordinateMode) -> None:
        _forbid_metric_fields(mode, self.speed_mps, self.heading_rad, self.position_unit)
        if mode is CoordinateMode.IMAGE_NORMALIZED:
            if not (0.0 <= self.x <= 1.0 and 0.0 <= self.y <= 1.0):
                raise ValueError("IMAGE_NORMALIZED x/y must be in [0, 1]")
            if self.position_unit != "norm":
                raise ValueError("IMAGE_NORMALIZED position_unit must be norm")
        if mode is CoordinateMode.GROUND_METRIC and self.position_unit != "m":
            raise ValueError("GROUND_METRIC position_unit must be m")
        if mode is CoordinateMode.IMAGE_PIXEL and self.position_unit != "px":
            raise ValueError("IMAGE_PIXEL position_unit must be px")


class Track(StrictModel):
    track_id: str
    class_name: AgentClass = Field(alias="class")
    points: list[TrackPoint] = Field(min_length=1)
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class TrackSequence(VersionedEnvelope):
    tracks: list[Track]

    @model_validator(mode="after")
    def points_match_mode(self) -> TrackSequence:
        for track in self.tracks:
            for point in track.points:
                point.validate_against_mode(self.coordinate_mode)
        return self


class TrajectorySample(StrictModel):
    timestamp_ms: int = Field(ge=0)
    x: float
    y: float
    position_unit: str
    speed_mps: float | None = None
    heading_rad: float | None = None


class PredictionBranch(StrictModel):
    branch_id: int = Field(ge=0)
    score: float = Field(ge=0, le=1)
    score_semantics: str = "uncalibrated_model_score"
    samples: list[TrajectorySample] = Field(min_length=1)


class AgentPrediction(StrictModel):
    track_id: str
    class_name: AgentClass = Field(alias="class")
    history: list[TrajectorySample] = Field(min_length=1)
    branches: list[PredictionBranch] = Field(min_length=1)
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class PredictionBundle(VersionedEnvelope):
    dt_ms: int = Field(default=200, gt=0)
    agents: list[AgentPrediction]

    @model_validator(mode="after")
    def no_meters_uncalibrated(self) -> PredictionBundle:
        for agent in self.agents:
            for sample in agent.history:
                _forbid_metric_fields(
                    self.coordinate_mode,
                    sample.speed_mps,
                    sample.heading_rad,
                    sample.position_unit,
                )
            for branch in agent.branches:
                for sample in branch.samples:
                    _forbid_metric_fields(
                        self.coordinate_mode,
                        sample.speed_mps,
                        sample.heading_rad,
                        sample.position_unit,
                    )
        return self


class Polygon2D(StrictModel):
    name: str
    kind: str
    vertices: list[tuple[float, float]] = Field(min_length=3)


class AgentSpawn(StrictModel):
    agent_id: str
    class_name: AgentClass = Field(alias="class")
    start: tuple[float, float]
    goal: tuple[float, float]
    speed_mps: float = Field(gt=0)
    reaction_time_s: float = Field(ge=0)
    script: str | None = None
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class MapScenario(VersionedEnvelope):
    name: str
    seed: int
    split: str
    width_m: float = Field(gt=0)
    height_m: float = Field(gt=0)
    obstacles: list[Polygon2D] = Field(default_factory=list)
    wait_lines: list[Polygon2D] = Field(default_factory=list)
    agents: list[AgentSpawn]
    coordinate_mode: CoordinateMode = CoordinateMode.GROUND_METRIC

    @model_validator(mode="after")
    def map_is_metric(self) -> MapScenario:
        if self.coordinate_mode is not CoordinateMode.GROUND_METRIC:
            raise ValueError("MapScenario must use GROUND_METRIC")
        if self.split not in {"train", "val", "test", "demo"}:
            raise ValueError("split must be train/val/test/demo")
        return self


class RiskCell(StrictModel):
    x: float
    y: float
    t_ms: int = Field(ge=0)
    risk: float = Field(ge=0, le=1)


class RiskMetrics(StrictModel):
    ttc_s: float | None = None
    pet_s: float | None = None
    min_clearance_m: float | None = None
    scene_risk_index: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def null_means_no_conflict(self) -> RiskMetrics:
        for name in ("ttc_s", "pet_s", "min_clearance_m"):
            value = getattr(self, name)
            if value is not None and value < 0:
                raise ValueError(f"{name} cannot be negative; use null when invalid")
        return self


class RiskField(VersionedEnvelope):
    metrics: RiskMetrics
    grid: list[RiskCell]
    param_snapshot: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def clearance_needs_metric(self) -> RiskField:
        if (
            self.coordinate_mode is not CoordinateMode.GROUND_METRIC
            and self.metrics.min_clearance_m is not None
        ):
            raise ValueError("min_clearance_m requires GROUND_METRIC")
        return self


class StrategyOutcome(StrictModel):
    strategy_id: StrategyId
    feasible: bool
    delay_s: float | None = None
    extra_path_m: float | None = None
    scene_risk_index: float | None = Field(default=None, ge=0, le=1)
    infeasible_reason: str | None = None


class CounterfactualResult(VersionedEnvelope):
    initial_state_id: str
    recommended_strategy: StrategyId | None
    no_feasible_strategy: bool = False
    outcomes: list[StrategyOutcome] = Field(min_length=1)
    explanation: str
    simulation_advice: bool = True

    @model_validator(mode="after")
    def recommendation_rules(self) -> CounterfactualResult:
        if not self.simulation_advice:
            raise ValueError("counterfactual output must be labeled simulation_advice")
        if self.no_feasible_strategy and self.recommended_strategy is not None:
            raise ValueError("NO_FEASIBLE_STRATEGY cannot include a recommendation")
        return self


class AnalysisJob(VersionedEnvelope):
    job_id: str
    status: JobStatus
    video_uri: str | None = None
    error_message: str | None = None
    result_uris: dict[str, str] = Field(default_factory=dict)


class ReviewRecord(StrictModel):
    schema_version: str = SCHEMA_VERSION
    job_id: str
    run_id: str
    decision: ReviewDecision
    reviewer: str
    comment: str = ""
    timestamp_ms: int = Field(ge=0)
