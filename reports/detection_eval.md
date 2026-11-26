# A-02 检测基线报告（smoke）

> **结论先行**：本报告是**链路 smoke**，不是最终检测指标。后端是 **Ultralytics YOLO11n fallback**，不是 RTMDet；训练/验证来自**同一个 run 的两路相机**，不能当作独立测试集。

## 1. 后端与环境

| 项 | 值 |
|---|---|
| 目标后端 | RTMDet-tiny（MMDetection） |
| 实际后端 | **YOLO11n**（Ultralytics 8.4.208） |
| 原因 | 当前 `torch 2.10 + CUDA 13` 下 MMDetection/mmcv 无可用预编译轮子，RTMDet 未跑通 |
| GPU | NVIDIA RTX 5060 Laptop（8GB） |
| 训练 | 10 epochs，batch=4，imgsz=640，约 1.4 分钟 |
| 权重 | `runs/detect/runs/detect/sdg_yolo11n/weights/best.pt`（本地，不入库） |

## 2. 数据

- 来源：SDG-Warehouse `artifacts/forklift_human_nearmiss/nearmiss-artifacts-00002.tar`（4.5GB）。
- run：`b3904eeae9c70d1b84a0_014f5a0f9461dfae29d5_run_13_seed_587824276`（10 相机近失）。
- 标注：`object_detection.jsonl`，300 帧；类别 `character` → person、`robot`（agent 路径含 forklift）→ forklift；每帧 1 人 1 叉车。
- 转换：`prepare_yolo_dataset.py`，5fps 抽帧（30fps 源，step=6）。
- split：**train=ceiling_00，val=ceiling_01**，各 50 帧/100 框。

> 这不是 A-01 的独立 run 切分；A-01 清单要求的 train/val/test 跨 shard，正式评测必须换数据。这里只验证“检测→JSON→可视化”链路。

## 3. 指标（val=ceiling_01，imgsz=640）

| 指标 | 值 |
|---|---:|
| Precision | 0.776 |
| Recall | 0.742 |
| mAP50 | **0.860** |
| mAP50-95 | **0.584** |

> 同 run 不同相机，场景/光照/人物高度相似，指标偏乐观；不能写“泛化到新仓库”。

**1280 异常**：同一权重在 `imgsz=1280` 下 mAP50 仅 0.0997。训练分辨率是 640，1280 与训练不匹配；本报告统一用 640，不把 1280 结果当作模型能力。原因未完全定位，后续单独实验。

## 4. 推理输出验证

- 单图：`reports/detection_sample.json`，2 个框（person + forklift），符合 S-01 `DetectionFrame`。
- 视频：`reports/detections_run13_ceiling01.jsonl`，20 帧（stride=15），每行一个 `DetectionFrame`。
- 可视化：`reports/figures/val_pred/`，50 张带框验证图（本地，`.gitignore` 忽略 jpg）。
- `model_version`：`yolo11n-sdg-run13-smoke`。

## 5. 局限（必须写进答辩/文档）

- 合成数据，不是真实仓库；域差异未评估。
- 单 run、同 run 不同相机，不是独立测试；不能报“最终 mAP”。
- 后端是 YOLO11n，不是 RTMDet；不能把数字写成 RTMDet 结果。
- 只在 640 训练/评估；1280 未解释清楚，暂不使用。
- 没有做 20 张失败案例分类；下一步补。

## 6. 下一步

1. 用 A-01 清单的**不同 shard** 下载 artifacts，构建独立 train/val/test；
2. 在兼容环境（torch 2.4/2.5 + mmcv）跑 RTMDet-tiny，与本 smoke 对比；
3. 补 20 张失败案例（遮挡/远距离/叉车出画）；
4. 把 `model_version=rtmdet-tiny-...` 写进最终报告，YOLO 只作为对照。

## 7. 文件

| 文件 | 说明 |
|---|---|
| `ml/detector/sdg_annotations.py` | 兼容解析 `object_detection.jsonl` |
| `ml/detector/prepare_yolo_dataset.py` | RGB+JSONL → YOLO |
| `ml/detector/train_yolo.py` | YOLO11n 微调 |
| `ml/detector/evaluate.py` | mAP 评估 |
| `ml/detector/infer_image.py` / `infer_video.py` | S-01 JSON 输出 |
| `reports/detection_eval.json` | 指标原始 JSON |
| `reports/detection_sample.json` | 单图输出 |
| `reports/detections_run13_ceiling01.jsonl` | 视频逐帧输出 |
| `reports/figures/val_pred/` | 50 张可视化 |
