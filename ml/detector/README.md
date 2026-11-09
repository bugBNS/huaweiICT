# A-02 人员/叉车检测基线

## 后端选择（必须如实说明）

- **目标后端：RTMDet-tiny**（MMDetection）。
- 当前环境：`torch 2.10 + CUDA 13 (RTX 5060)`；MMDetection/mmcv 没有匹配的预编译轮子，**RTMDet 未在本机跑通**。
- 可运行替代：**Ultralytics YOLO11n**，用于把数据/训练/推理/评估链路先跑通；报告必须写“YOLO11n fallback”，不能写成 RTMDet 结果。
- 若后续换到兼容环境（如 torch 2.4 + CUDA 12.1），再按 RTMDet 训练；YOLO 的数据转换/评估口径可复用。

## 数据

一个 artifacts shard 约 4.8GB，包含 RGB + `object_detection.jsonl` + `camera_params.jsonl`。A-01 清单给出 run/clip；不要下全量 2.46TiB。

```bash
# 单 run smoke：train=ceiling_00, val=ceiling_01（同一 run，不同视角；不是最终评测）
python -m ml.detector.prepare_yolo_dataset \
  --artifacts-dir .tmp_sdg/artifacts \
  --run-id <run_id> \
  --train-camera ceiling_00 --val-camera ceiling_01 \
  --out data/sdg_yolo --sample-fps 2
```

输出：`images/{train,val}`、`labels/{train,val}`、`data.yaml`、`prepare_stats.json`。
`data/sdg_yolo/` 已在 `.gitignore` 中，不提交帧/标签。

## 训练 / 评估 / 推理

```bash
python -m ml.detector.train_yolo --data data/sdg_yolo/data.yaml --epochs 20 --batch 4
python -m ml.detector.evaluate --weights runs/detect/sdg_yolo11n/weights/best.pt \
  --data data/sdg_yolo/data.yaml --out reports/detection_eval.json
python -m ml.detector.infer_image --model runs/detect/sdg_yolo11n/weights/best.pt \
  --image frame.jpg --run-id run_x --scenario-id sc_x --out det.json
python -m ml.detector.infer_video --model runs/detect/sdg_yolo11n/weights/best.pt \
  --video clip.mp4 --run-id run_x --scenario-id sc_x --out det.jsonl --stride 15
```

输出遵循 S-01 `DetectionFrame`：`coordinate_mode=IMAGE_PIXEL`、`bbox.unit=px`、类别只允许 `person/forklift`。

## 验收边界

- **必须做**：单图/短视频输出合法 `DetectionFrame`；至少 20 张抽样可视化；报告写清后端、数据、硬件、局限。
- **不能做**：没有标注时伪造 mAP；把 COCO `truck` 强行当 forklift；把同 run 的不同相机 split 写成“独立测试集”。
- **最终评测**：用 A-01 清单里不同 shard 的 train/val/test run；本 README 的单 run 只用于链路 smoke。

## 文件

| 文件 | 作用 |
|---|---|
| `config.py` | 类别/阈值/默认参数 |
| `sdg_annotations.py` | 兼容解析 `object_detection.jsonl` |
| `prepare_yolo_dataset.py` | RGB+JSONL → YOLO 数据 |
| `train_yolo.py` | YOLO11n 微调 |
| `evaluate.py` | mAP/Precision/Recall |
| `infer_image.py` / `infer_video.py` | 单图/视频推理，输出 S-01 JSON |
