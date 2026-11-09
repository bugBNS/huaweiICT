"""Dump JSON Schema files from Pydantic models."""

import json
from pathlib import Path

from schemas.models import (
    AnalysisJob,
    CounterfactualResult,
    DetectionFrame,
    MapScenario,
    PredictionBundle,
    ReviewRecord,
    RiskField,
    TrackSequence,
)

OUT = Path(__file__).resolve().parent

TARGETS = {
    "detection.schema.json": DetectionFrame,
    "tracks.schema.json": TrackSequence,
    "prediction.schema.json": PredictionBundle,
    "map.schema.json": MapScenario,
    "risk_field.schema.json": RiskField,
    "counterfactual.schema.json": CounterfactualResult,
    "analysis_job.schema.json": AnalysisJob,
    "review.schema.json": ReviewRecord,
}


def main() -> None:
    for name, model in TARGETS.items():
        path = OUT / name
        path.write_text(
            json.dumps(model.model_json_schema(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"wrote {path.name}")


if __name__ == "__main__":
    main()
