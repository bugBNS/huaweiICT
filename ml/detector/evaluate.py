"""检测评估：调用 Ultralytics val，输出 JSON 指标（A-02）。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _jsonable(value):
    if isinstance(value, (int, float, str, bool)) or value is None:
        return value
    try:
        return float(value)
    except Exception:
        return str(value)


def main() -> None:
    parser = argparse.ArgumentParser(description="检测 mAP/Precision/Recall 评估")
    parser.add_argument("--weights", required=True)
    parser.add_argument("--data", required=True)
    parser.add_argument("--split", default="val")
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=4)
    parser.add_argument("--device", default="0")
    parser.add_argument("--out", default="reports/detection_eval.json")
    args = parser.parse_args()

    from ultralytics import YOLO

    model = YOLO(args.weights)
    metrics = model.val(data=args.data, split=args.split, imgsz=args.imgsz,
                        batch=args.batch, device=args.device, workers=0, verbose=False)
    result = {k: _jsonable(v) for k, v in metrics.results_dict.items()}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
