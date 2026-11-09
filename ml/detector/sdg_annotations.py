"""解析 SDG `object_detection.jsonl`（A-02）。

真实 JSONL 是“一行一帧”，每帧含 objects/detections 列表；字段名可能随版本变化，
这里做兼容解析，只保留 person/forklift，不把 truck 等类别强行映射。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Iterator

CLASS_ALIASES = {
    "person": "person",
    "human": "person",
    "worker": "person",
    "pedestrian": "person",
    "forklift": "forklift",
    "fork_lift": "forklift",
}
OBJECT_KEYS = ("agents", "objects", "detections", "annotations", "labels")
CLASS_KEYS = ("class", "class_name", "label", "category", "type", "name")
BBOX_KEYS = (
    "bounding_box_2d_tight_fast", "bounding_box_2d_loose_fast",
    "bounding_box_2d_tight", "bounding_box_2d_loose",
    "bbox_2d_tight", "bbox2d_tight", "bbox_2d", "bbox2d", "bbox", "box",
    "bbox_tight", "aabb_2d",
)


def normalize_class(value: object) -> str | None:
    if value is None:
        return None
    name = str(value).strip().lower()
    return CLASS_ALIASES.get(name)


def _bbox_from_mapping(obj: dict) -> tuple[float, float, float, float] | None:
    for key in ("x1", "x_min", "left", "xmin"):
        if key in obj:
            try:
                x1 = float(obj[key])
                y1 = float(obj.get("y1", obj.get("y_min", obj.get("top", obj.get("ymin")))))
                x2 = float(obj.get("x2", obj.get("x_max", obj.get("right", obj.get("xmax")))))
                y2 = float(obj.get("y2", obj.get("y_max", obj.get("bottom", obj.get("ymax")))))
                return x1, y1, x2, y2
            except (TypeError, ValueError):
                return None
    return None


def extract_bbox(obj: dict) -> tuple[float, float, float, float] | None:
    if isinstance(obj.get("annotators"), dict):
        obj = obj["annotators"]
    for key in BBOX_KEYS:
        value = obj.get(key)
        if value is None:
            continue
        if isinstance(value, (list, tuple)) and len(value) >= 4:
            try:
                return tuple(float(v) for v in value[:4])  # type: ignore[return-value]
            except (TypeError, ValueError):
                continue
        if isinstance(value, dict):
            box = _bbox_from_mapping(value)
            if box:
                return box
    return None


def _raw_class(obj: dict) -> object | None:
    label = obj.get("label")
    if isinstance(label, dict):
        for field in ("class", "class_name", "name", "category"):
            if field in label:
                return label[field]
    for field in ("class", "class_name", "category", "type", "name"):
        if field in obj and not isinstance(obj[field], (dict, list)):
            return obj[field]
    return None


def extract_class(obj: dict, key: str = "") -> str | None:
    raw_value = _raw_class(obj)
    if raw_value is None:
        return None
    raw = str(raw_value).strip().lower()
    # SDG 实际标签：人=character，叉车=robot（agent key 含 forklift）
    if raw == "character":
        return "person"
    if raw == "robot" and "forklift" in key.lower():
        return "forklift"
    return normalize_class(raw)


def objects_of(frame: dict) -> list[tuple[str, dict]]:
    """返回 [(agent_key, object)]；兼容 agents 字典与 objects/detections 列表。"""
    agents = frame.get("agents")
    if isinstance(agents, dict):
        return [(str(k), v) for k, v in agents.items() if isinstance(v, dict)]
    for key in OBJECT_KEYS:
        value = frame.get(key)
        if isinstance(value, list):
            return [(str(i), v) for i, v in enumerate(value) if isinstance(v, dict)]
    return []


def parse_frame(frame: dict) -> list[tuple[str, float, float, float, float]]:
    out: list[tuple[str, float, float, float, float]] = []
    for key, obj in objects_of(frame):
        cls = extract_class(obj, key)
        box = extract_bbox(obj)
        if cls and box:
            out.append((cls, *box))
    return out


def iter_frames(path: str | Path) -> Iterator[dict]:
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)
