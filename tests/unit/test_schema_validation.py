from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from schemas.models import (
    SCHEMA_VERSION,
    AnalysisJob,
    CounterfactualResult,
    DetectionFrame,
    MapScenario,
    PredictionBundle,
    ReviewRecord,
    RiskField,
    TrackSequence,
)

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ROOT / "samples"

SAMPLE_MODELS = {
    "detection.json": DetectionFrame,
    "tracks.json": TrackSequence,
    "prediction.json": PredictionBundle,
    "map.json": MapScenario,
    "risk_field.json": RiskField,
    "counterfactual.json": CounterfactualResult,
    "analysis_job.json": AnalysisJob,
    "review.json": ReviewRecord,
}


def _load(name: str) -> dict:
    return json.loads((SAMPLES / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize("filename, model", SAMPLE_MODELS.items())
def test_official_samples_validate(filename: str, model: type) -> None:
    payload = _load(filename)
    parsed = model.model_validate(payload)
    assert parsed.schema_version == SCHEMA_VERSION


def test_tracks_uncalibrated_cannot_use_meters() -> None:
    payload = _load("tracks.json")
    payload["tracks"][0]["points"][0]["position_unit"] = "m"
    with pytest.raises(ValidationError):
        TrackSequence.model_validate(payload)


def test_tracks_uncalibrated_cannot_carry_speed_mps() -> None:
    payload = _load("tracks.json")
    payload["tracks"][0]["points"][0]["speed_mps"] = 1.2
    with pytest.raises(ValidationError):
        TrackSequence.model_validate(payload)


def test_detection_bbox_rejects_meter_unit() -> None:
    payload = _load("detection.json")
    payload["detections"][0]["bbox"]["unit"] = "m"
    with pytest.raises(ValidationError):
        DetectionFrame.model_validate(payload)


def test_unknown_field_is_rejected() -> None:
    payload = _load("prediction.json")
    payload["accident_probability"] = 0.9
    with pytest.raises(ValidationError):
        PredictionBundle.model_validate(payload)


def test_class_must_be_lowercase_enum() -> None:
    payload = _load("detection.json")
    payload["detections"][0]["class"] = "Person"
    with pytest.raises(ValidationError):
        DetectionFrame.model_validate(payload)


def test_invalid_ttc_cannot_be_negative() -> None:
    payload = _load("risk_field.json")
    payload["metrics"]["ttc_s"] = -1
    with pytest.raises(ValidationError):
        RiskField.model_validate(payload)


def test_min_clearance_forbidden_when_not_metric() -> None:
    payload = _load("risk_field.json")
    payload["coordinate_mode"] = "IMAGE_NORMALIZED"
    with pytest.raises(ValidationError):
        RiskField.model_validate(payload)


def test_schema_version_mismatch() -> None:
    payload = _load("map.json")
    payload["schema_version"] = "0.0.1"
    with pytest.raises(ValidationError):
        MapScenario.model_validate(payload)
