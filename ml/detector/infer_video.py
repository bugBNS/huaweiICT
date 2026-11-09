"""短视频抽帧检测，输出逐帧 S-01 DetectionFrame JSONL（A-02）。

不伪造 FPS：默认每 stride 帧抽一帧，timestamp_ms 由源视频 FPS 计算。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2

from schemas.models import BBoxXYXY, Detection, DetectionFrame
from ml.detector.config import DEFAULT_CONF, DEFAULT_IMGSZ, DEFAULT_IOU, TARGET_CLASSES


def run(
    model_path: str,
    video_path: str,
    run_id: str,
    scenario_id: str,
    out_path: str,
    stride: int = 15,
    conf: float = DEFAULT_CONF,
    iou: float = DEFAULT_IOU,
    imgsz: int = DEFAULT_IMGSZ,
    device: str = "0",
    model_version: str | None = None,
) -> int:
    from ultralytics import YOLO

    model = YOLO(model_path)
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"无法打开视频: {video_path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    count = 0
    frame_idx = 0
    with open(out_path, "w", encoding="utf-8") as f:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if frame_idx % stride != 0:
                frame_idx += 1
                continue
            results = model.predict(source=frame, conf=conf, iou=iou, imgsz=imgsz,
                                    device=device, verbose=False)
            result = results[0]
            h, w = result.orig_shape
            detections: list[Detection] = []
            if result.boxes is not None:
                for box in result.boxes:
                    name = str(model.names.get(int(box.cls.item()), int(box.cls.item())))
                    if name not in TARGET_CLASSES:
                        continue
                    x1, y1, x2, y2 = [float(v) for v in box.xyxy[0].tolist()]
                    detections.append(Detection(
                        **{"class": name},
                        bbox=BBoxXYXY(x1=x1, y1=y1, x2=x2, y2=y2, unit="px"),
                        conf=float(box.conf.item()),
                    ))
            frame_obj = DetectionFrame(
                run_id=run_id,
                scenario_id=scenario_id,
                model_version=model_version or Path(model_path).stem,
                risk_rule_version=None,
                coordinate_mode="IMAGE_PIXEL",
                timestamp_ms=int(round(frame_idx / fps * 1000)),
                image_id=f"frame_{frame_idx:06d}",
                image_width=int(w),
                image_height=int(h),
                detections=detections,
            )
            f.write(json.dumps(frame_obj.model_dump(by_alias=True, mode="json"), ensure_ascii=False) + "\n")
            count += 1
            frame_idx += 1
    cap.release()
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="短视频 person/forklift 检测")
    parser.add_argument("--model", required=True)
    parser.add_argument("--video", required=True)
    parser.add_argument("--run-id", default="run_demo")
    parser.add_argument("--scenario-id", default="sc_demo")
    parser.add_argument("--out", required=True)
    parser.add_argument("--stride", type=int, default=15)
    parser.add_argument("--conf", type=float, default=DEFAULT_CONF)
    parser.add_argument("--iou", type=float, default=DEFAULT_IOU)
    parser.add_argument("--imgsz", type=int, default=DEFAULT_IMGSZ)
    parser.add_argument("--device", default="0")
    parser.add_argument("--model-version", default=None)
    args = parser.parse_args()
    n = run(args.model, args.video, args.run_id, args.scenario_id, args.out,
            args.stride, args.conf, args.iou, args.imgsz, args.device, args.model_version)
    print(f"frames={n} -> {args.out}")


if __name__ == "__main__":
    main()
