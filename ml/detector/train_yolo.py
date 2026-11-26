"""YOLO11n 微调入口（A-02 的可运行替代基线）。

说明：A-02 的目标是 RTMDet-tiny；当前环境 torch 2.10 + CUDA 13，MMDetection/mmcv
没有可用预编译轮子，先用 Ultralytics YOLO11n 做可运行的 smoke/基线。
不要把 YOLO 结果写成 RTMDet 结果；最终报告需注明后端。
"""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="YOLO11n 人员/叉车微调")
    parser.add_argument("--data", required=True, help="data.yaml 路径")
    parser.add_argument("--base", default="yolo11n.pt", help="预训练权重")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--imgsz", type=int, default=1280)
    parser.add_argument("--batch", type=int, default=4)
    parser.add_argument("--device", default="0")
    parser.add_argument("--project", default="runs/detect")
    parser.add_argument("--name", default="sdg_yolo11n")
    parser.add_argument("--seed", type=int, default=20261109)
    args = parser.parse_args()

    from ultralytics import YOLO

    model = YOLO(args.base)
    model.train(
        data=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        project=args.project,
        name=args.name,
        workers=0,          # Windows 下避免 dataloader 多进程问题
        seed=args.seed,
        exist_ok=True,
        pretrained=True,
    )
    print("weights:", Path(args.project) / args.name / "weights" / "best.pt")


if __name__ == "__main__":
    main()
