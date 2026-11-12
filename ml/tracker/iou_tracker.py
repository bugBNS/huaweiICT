"""轻量 IoU 跟踪兜底（A-03）。

A-03 的目标是 ByteTrack；当前 supervision 0.31 不提供 ByteTrack，且没有稳定
的 ByteTrack 依赖，先用 IoU 贪心匹配把轨迹链路跑通。接口保持可替换：
  update(detections, timestamp_ms, frame_w, frame_h) -> list[TrackPoint]
后续接 ByteTrack 时只替换本类，输出 schema 不变。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from schemas.models import BBoxXYXY, TrackPoint


@dataclass
class Detection:
    class_name: str
    x1: float
    y1: float
    x2: float
    y2: float
    conf: float


@dataclass
class _Track:
    track_id: str
    class_name: str
    x1: float
    y1: float
    x2: float
    y2: float
    last_seen: int
    hits: int = 1
    points: list[TrackPoint] = field(default_factory=list)


def iou(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    return inter / max(area_a + area_b - inter, 1e-9)


class IoUTracker:
    def __init__(self, iou_threshold: float = 0.3, max_age: int = 15,
                 class_prefix: dict[str, str] | None = None):
        self.iou_threshold = iou_threshold
        self.max_age = max_age
        self.class_prefix = class_prefix or {"person": "p", "forklift": "f"}
        self._tracks: list[_Track] = []
        self._counters: dict[str, int] = {}

    def _new_id(self, class_name: str) -> str:
        prefix = self.class_prefix.get(class_name, "t")
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return f"{prefix}{self._counters[prefix]}"

    def _point(self, tr: _Track, timestamp_ms: int, frame_w: int, frame_h: int,
               conf: float | None, observed: bool) -> TrackPoint:
        cx, cy = (tr.x1 + tr.x2) / 2, (tr.y1 + tr.y2) / 2
        return TrackPoint(
            timestamp_ms=timestamp_ms,
            x=max(0.0, min(cx / frame_w, 1.0)),
            y=max(0.0, min(cy / frame_h, 1.0)),
            position_unit="norm",
            speed_mps=None,
            heading_rad=None,
            bbox=BBoxXYXY(x1=tr.x1, y1=tr.y1, x2=tr.x2, y2=tr.y2, unit="px"),
            center=(cx, cy),
            foot=(cx, tr.y2),
            conf=conf,
            observed=observed,
        )

    def update(self, detections: list[Detection], timestamp_ms: int,
               frame_w: int, frame_h: int) -> list[TrackPoint]:
        # 贪心匹配：按 IoU 从高到低，同类别
        pairs: list[tuple[float, int, int]] = []
        for ti, tr in enumerate(self._tracks):
            for di, det in enumerate(detections):
                if det.class_name != tr.class_name:
                    continue
                score = iou((tr.x1, tr.y1, tr.x2, tr.y2), (det.x1, det.y1, det.x2, det.y2))
                if score >= self.iou_threshold:
                    pairs.append((score, ti, di))
        pairs.sort(reverse=True)
        used_t, used_d = set(), set()
        matched: dict[int, int] = {}
        for _, ti, di in pairs:
            if ti in used_t or di in used_d:
                continue
            used_t.add(ti); used_d.add(di); matched[ti] = di

        out: list[TrackPoint] = []
        for ti, tr in enumerate(self._tracks):
            if ti in matched:
                det = detections[matched[ti]]
                tr.x1, tr.y1, tr.x2, tr.y2 = det.x1, det.y1, det.x2, det.y2
                tr.last_seen = timestamp_ms
                tr.hits += 1
                point = self._point(tr, timestamp_ms, frame_w, frame_h, det.conf, True)
            elif timestamp_ms - tr.last_seen <= self.max_age * 100:
                point = self._point(tr, timestamp_ms, frame_w, frame_h, None, False)
            else:
                continue
            tr.points.append(point)
            out.append(point)

        # 未匹配检测 -> 新轨迹
        for di, det in enumerate(detections):
            if di in used_d:
                continue
            tr = _Track(self._new_id(det.class_name), det.class_name,
                        det.x1, det.y1, det.x2, det.y2, timestamp_ms)
            point = self._point(tr, timestamp_ms, frame_w, frame_h, det.conf, True)
            tr.points.append(point)
            self._tracks.append(tr)
            out.append(point)

        # 淘汰过期轨迹
        self._tracks = [t for t in self._tracks if timestamp_ms - t.last_seen <= self.max_age * 100]
        return out

    def tracks(self):
        return [t for t in self._tracks if t.points]
