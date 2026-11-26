"""单图检测推理，输出 S-01 DetectionFrame JSON（A-02）。

用法：
  python -m ml.detector.infer_image --model yolo11n.pt --image frame.jpg \
      --run-id run_x --scenario-id sc_x --out det.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from schemas.models import BBoxXYXY, Detection, DetectionFrame
from ml.detector.config import DEFAULT_CONF, DEFAULT_IMGSZ, DEFAULT_IOU, TARGET_CLASSES


def _class_name(model, cls_id: int) -> str:
    names = getattr(model, "names", {})
    return str(names.get(cls_id, cls_id))


def run(
    model_path: str,
    image_path: str,
    run_id: str,
    scenario_id: str,
    out_path: str,
    conf: float = DEFAULT_CONF,
    iou: float = DEFAULT_IOU,
    imgsz: int = DEFAULT_IMGSZ,
    device: str = "0",
    model_version: str | None = None,
) -> DetectionFrame:
    from ultralytics import YOLO

    model = YOLO(model_path)
    results = model.predict(source=image_path, conf=conf, iou=iou, imgsz=imgsz, device=device, verbose=False)
    result = results[0]
    h, w = result.orig_shape
    detections: list[Detection] = []
    if result.boxes is not None:
        for box in result.boxes:
            name = _class_name(model, int(box.cls.item()))
            if name not in TARGET_CLASSES:
                continue
            x1, y1, x2, y2 = [float(v) for v in box.xyxy[0].tolist()]
            detections.append(Detection(
                **{"class": name},
                bbox=BBoxXYXY(x1=x1, y1=y1, x2=x2, y2=y2, unit="px"),
                conf=float(box.conf.item()),
            ))
    frame = DetectionFrame(
        run_id=run_id,
        scenario_id=scenario_id,
        model_version=model_version or Path(model_path).stem,
        risk_rule_version=None,
        coordinate_mode="IMAGE_PIXEL",
        timestamp_ms=0,
        image_id=Path(image_path).stem,
        image_width=int(w),
        image_height=int(h),
        detections=detections,
    )
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(
        json.dumps(frame.model_dump(by_alias=True, mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return frame


def main() -> None:
    parser = argparse.ArgumentParser(description="单图 person/forklift 检测")
    parser.add_argument("--model", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--run-id", default="run_demo")
    parser.add_argument("--scenario-id", default="sc_demo")
    parser.add_argument("--out", required=True)
    parser.add_argument("--conf", type=float, default=DEFAULT_CONF)
    parser.add_argument("--iou", type=float, default=DEFAULT_IOU)
    parser.add_argument("--imgsz", type=int, default=DEFAULT_IMGSZ)
    parser.add_argument("--device", default="0")
    parser.add_argument("--model-version", default=None)
    args = parser.parse_args()
    frame = run(args.model, args.image, args.run_id, args.scenario_id, args.out,
                args.conf, args.iou, args.imgsz, args.device, args.model_version)
    print(f"detections={len(frame.detections)} -> {args.out}")


if __name__ == "__main__":
    main()
