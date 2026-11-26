from __future__ import annotations

import json

from ml.detector.sdg_annotations import extract_bbox, parse_frame
from schemas.models import BBoxXYXY, Detection, DetectionFrame


def test_parse_frame_keeps_person_and_forklift_only() -> None:
    frame = {
        "objects": [
            {"class": "person", "bbox_2d_tight": {"x_min": 10, "y_min": 20, "x_max": 30, "y_max": 60}},
            {"class": "forklift", "bbox_2d_tight": [5, 6, 50, 70]},
            {"class": "truck", "bbox_2d_tight": [0, 0, 10, 10]},
        ]
    }
    rows = parse_frame(frame)
    assert [r[0] for r in rows] == ["person", "forklift"]
    assert rows[0][1:] == (10.0, 20.0, 30.0, 60.0)
    assert rows[1][1:] == (5.0, 6.0, 50.0, 70.0)


def test_extract_bbox_returns_none_when_missing() -> None:
    assert extract_bbox({"class": "person"}) is None
    assert extract_bbox({"bbox_2d_tight": [1, 2, 3]}) is None


def test_detection_frame_serializes_to_schema_shape() -> None:
    frame = DetectionFrame(
        run_id="run_x",
        scenario_id="sc_x",
        model_version="yolo11n-sdg",
        risk_rule_version=None,
        coordinate_mode="IMAGE_PIXEL",
        timestamp_ms=0,
        image_id="frame_000000",
        image_width=1920,
        image_height=1080,
        detections=[
            Detection(**{"class": "person"}, bbox=BBoxXYXY(x1=1, y1=2, x2=30, y2=40, unit="px"), conf=0.9),
        ],
    )
    payload = json.loads(json.dumps(frame.model_dump(by_alias=True, mode="json")))
    assert payload["detections"][0]["class"] == "person"
    assert payload["detections"][0]["bbox"]["unit"] == "px"


def test_parse_real_sdg_agents_structure() -> None:
    frame = {
        "agents": {
            "/World/Characters/Worker/Worker_0/ManRoot/person_0": {
                "label": {"class": "character"},
                "annotators": {
                    "bounding_box_2d_tight_fast": {
                        "x_min": 917, "y_min": 285, "x_max": 1003, "y_max": 541,
                    }
                },
            },
            "/World/Robots/forklift/Forklift": {
                "label": {"class": "robot"},
                "annotators": {
                    "bounding_box_2d_tight_fast": {
                        "x_min": 1354, "y_min": 0, "x_max": 1718, "y_max": 430,
                    }
                },
            },
        }
    }
    rows = parse_frame(frame)
    assert [r[0] for r in rows] == ["person", "forklift"]
    assert rows[0][1:] == (917.0, 285.0, 1003.0, 541.0)
    assert rows[1][1:] == (1354.0, 0.0, 1718.0, 430.0)
