from __future__ import annotations

from ml.tracker.iou_tracker import Detection, IoUTracker
from schemas.models import Track, TrackSequence


def _det(cls: str, x1: float, y1: float, x2: float, y2: float, conf: float = 0.9) -> Detection:
    return Detection(cls, x1, y1, x2, y2, conf)


def test_iou_tracker_keeps_id_and_marks_missed() -> None:
    tracker = IoUTracker(iou_threshold=0.3, max_age=5)
    tracker.update([_det("person", 10, 10, 50, 100)], 0, 200, 200)
    tracker.update([_det("person", 12, 12, 52, 102)], 100, 200, 200)
    points = tracker.update([], 200, 200, 200)
    assert len(points) == 1
    assert points[0].observed is False
    tracks = tracker.tracks()
    assert len(tracks) == 1
    assert tracks[0].track_id == "p1"
    assert len(tracks[0].points) == 3


def test_iou_tracker_new_object_gets_new_id() -> None:
    tracker = IoUTracker()
    tracker.update([_det("person", 10, 10, 50, 100)], 0, 200, 200)
    tracker.update([_det("forklift", 120, 10, 190, 100)], 100, 200, 200)
    ids = {t.track_id for t in tracker.tracks()}
    assert ids == {"p1", "f1"}


def test_track_sequence_schema() -> None:
    tracker = IoUTracker()
    tracker.update([_det("person", 10, 10, 50, 100)], 0, 200, 200)
    tracker.update([_det("person", 12, 12, 52, 102)], 100, 200, 200)
    tracks = [
        Track(**{"class": t.class_name}, track_id=t.track_id, points=t.points)
        for t in tracker.tracks()
    ]
    seq = TrackSequence(
        run_id="run_x", scenario_id="sc_x", model_version="yolo+iou",
        risk_rule_version=None, coordinate_mode="IMAGE_NORMALIZED",
        timestamp_ms=100, tracks=tracks,
    )
    payload = seq.model_dump(by_alias=True, mode="json")
    assert payload["tracks"][0]["class"] == "person"
    assert payload["tracks"][0]["points"][0]["position_unit"] == "norm"
