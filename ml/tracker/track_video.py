"""视频检测 + IoU 跟踪兜底，输出 S-01 TrackSequence（A-03）。

A-03 目标是 ByteTrack；当前 Ultralytics `model.track` 在本机挂起，先用 IoU
贪心跟踪把轨迹链路跑通。IoUTracker 接口可替换为 ByteTrack，输出 schema 不变。

用法：
  python -m ml.tracker.track_video --model best.pt --video clip.mp4 \
    --run-id run_x --scenario-id near_miss --out tracks.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2

from ml.tracker.iou_tracker import Detection, IoUTracker
from schemas.models import Track, TrackSequence


def main() -> None:
    parser = argparse.ArgumentParser(description="视频检测 + IoU 跟踪")
    parser.add_argument("--model", required=True)
    parser.add_argument("--video", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--scenario-id", default="near_miss")
    parser.add_argument("--out", required=True)
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", default="0")
    parser.add_argument("--max-frames", type=int, default=None)
    parser.add_argument("--model-version", default=None)
    parser.add_argument("--iou-threshold", type=float, default=0.1)
    parser.add_argument("--max-age", type=int, default=100)
    args = parser.parse_args()

    from ultralytics import YOLO

    model = YOLO(args.model)
    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        raise FileNotFoundError(args.video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    tracker = IoUTracker(iou_threshold=args.iou_threshold, max_age=args.max_age)
    frame_idx = 0
    last_ts = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if args.max_frames and frame_idx >= args.max_frames:
            break
        results = model.predict(source=frame, conf=args.conf, imgsz=args.imgsz,
                                device=args.device, verbose=False)
        result = results[0]
        h, w = result.orig_shape
        dets: list[Detection] = []
        if result.boxes is not None:
            for box in result.boxes:
                name = str(model.names.get(int(box.cls.item()), int(box.cls.item())))
                if name not in ("person", "forklift"):
                    continue
                x1, y1, x2, y2 = [float(v) for v in box.xyxy[0].tolist()]
                dets.append(Detection(name, x1, y1, x2, y2, float(box.conf.item())))
        ts = int(round(frame_idx / fps * 1000))
        tracker.update(dets, ts, w, h)
        last_ts = ts
        frame_idx += 1
    cap.release()

    tracks = [
        Track(**{"class": t.class_name}, track_id=t.track_id, points=t.points)
        for t in tracker.tracks()
    ]
    seq = TrackSequence(
        run_id=args.run_id,
        scenario_id=args.scenario_id,
        model_version=args.model_version or f"{Path(args.model).stem}+iou",
        risk_rule_version=None,
        coordinate_mode="IMAGE_NORMALIZED",
        timestamp_ms=last_ts,
        tracks=tracks,
    )
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(
        json.dumps(seq.model_dump(by_alias=True, mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"frames={frame_idx} tracks={len(tracks)} -> {args.out}")


if __name__ == "__main__":
    main()
