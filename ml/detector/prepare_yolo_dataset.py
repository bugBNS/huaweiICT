"""把 SDG artifacts 里的 RGB + object_detection.jsonl 转成 YOLO 数据（A-02）。

用法（单 run smoke；正式评测请用不同 run 的 train/val/test）：
  python -m ml.detector.prepare_yolo_dataset \
    --artifacts-dir .tmp_sdg/artifacts \
    --run-id <run_id> \
    --train-camera ceiling_00 --val-camera ceiling_01 \
    --out data/sdg_yolo --sample-fps 2
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import yaml

from ml.detector.config import CLASS_TO_ID
from ml.detector.sdg_annotations import iter_frames, parse_frame


def _find_file(root: Path, prefix: str, suffix: str) -> Path:
    matches = sorted(root.rglob(f"{prefix}*{suffix}"))
    if not matches:
        raise FileNotFoundError(f"找不到 {prefix}*{suffix} under {root}")
    return matches[0]


def _write_split(
    artifacts_dir: Path,
    run_id: str,
    camera: str,
    split: str,
    out_dir: Path,
    sample_fps: float,
    max_frames: int | None,
) -> dict:
    video_path = _find_file(artifacts_dir, f"{run_id}.{camera}", ".rgb.mp4")
    jsonl_path = _find_file(artifacts_dir, f"{run_id}.{camera}", ".object_detection.jsonl")
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"无法打开 {video_path}")
    src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    step = max(1, int(round(src_fps / sample_fps)))
    frames = list(iter_frames(jsonl_path))
    if not frames:
        raise ValueError(f"{jsonl_path} 为空")
    img_dir = out_dir / "images" / split
    lbl_dir = out_dir / "labels" / split
    img_dir.mkdir(parents=True, exist_ok=True)
    lbl_dir.mkdir(parents=True, exist_ok=True)

    kept = 0
    boxes = 0
    frame_idx = 0
    while True:
        ok, image = cap.read()
        if not ok:
            break
        if frame_idx % step != 0:
            frame_idx += 1
            continue
        if max_frames and kept >= max_frames:
            break
        h, w = image.shape[:2]
        ann = frames[min(frame_idx, len(frames) - 1)]
        rows: list[str] = []
        for cls, x1, y1, x2, y2 in parse_frame(ann):
            cls_id = CLASS_TO_ID.get(cls)
            if cls_id is None:
                continue
            x1, x2 = max(0.0, min(x1, w)), max(0.0, min(x2, w))
            y1, y2 = max(0.0, min(y1, h)), max(0.0, min(y2, h))
            if x2 <= x1 or y2 <= y1:
                continue
            cx, cy = (x1 + x2) / 2 / w, (y1 + y2) / 2 / h
            bw, bh = (x2 - x1) / w, (y2 - y1) / h
            rows.append(f"{cls_id} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")
        stem = f"{camera}_{frame_idx:06d}"
        cv2.imwrite(str(img_dir / f"{stem}.jpg"), image, [cv2.IMWRITE_JPEG_QUALITY, 92])
        (lbl_dir / f"{stem}.txt").write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")
        kept += 1
        boxes += len(rows)
        frame_idx += 1
    cap.release()
    return {"split": split, "camera": camera, "frames": kept, "boxes": boxes,
            "src_fps": src_fps, "step": step, "video": str(video_path), "jsonl": str(jsonl_path)}


def main() -> None:
    parser = argparse.ArgumentParser(description="SDG artifacts -> YOLO 数据集")
    parser.add_argument("--artifacts-dir", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--train-camera", default="ceiling_00")
    parser.add_argument("--val-camera", default="ceiling_01")
    parser.add_argument("--out", default="data/sdg_yolo")
    parser.add_argument("--sample-fps", type=float, default=2.0)
    parser.add_argument("--max-frames", type=int, default=None)
    args = parser.parse_args()

    out_dir = Path(args.out)
    artifacts = Path(args.artifacts_dir)
    stats = [
        _write_split(artifacts, args.run_id, args.train_camera, "train", out_dir,
                     args.sample_fps, args.max_frames),
        _write_split(artifacts, args.run_id, args.val_camera, "val", out_dir,
                     args.sample_fps, args.max_frames),
    ]
    data = {
        "path": str(out_dir.resolve()),
        "train": "images/train",
        "val": "images/val",
        "names": {idx: name for name, idx in CLASS_TO_ID.items()},
    }
    (out_dir / "data.yaml").write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    (out_dir / "prepare_stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    print("data.yaml ->", out_dir / "data.yaml")


if __name__ == "__main__":
    main()
