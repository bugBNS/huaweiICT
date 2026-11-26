# A-08 本地推理服务 smoke（2026-11-26）

## 环境

- Python 3.10，CPU
- 后端：Ultralytics YOLO11n（COCO 预训练 fallback，不是 RTMDet）
- 权重：`yolo11n.pt`（本地文件，未入库）
- 测试图：`reports/figures/val_pred/ceiling_01_000000.jpg`（本仓库不提交）
- 服务：`uvicorn services.inference.app:app --host 127.0.0.1 --port 8010`

## 结果

| 请求 | 结果 |
|---|---|
| `GET /health` | `status=ok`，模型首次请求前 `model_loaded=false`，请求后 `true` |
| `GET /version` | `service_version=0.1.0`，`schema_version=1.0.0` |
| `POST /predict`（1 张 1920×1080） | 返回 1 个 `DetectionFrame`；检测到 1 个 `person`；`model_version=yolo11n` |
| 首次请求耗时 | 约 28.1 s（含模型加载 + CPU 推理；不是性能指标） |
| 单元测试 | `tests/unit/test_inference_service.py` 9 passed |

## 边界

- 这是 **本地容器/本地进程** 验证，不是 ModelArts 云端部署；云端证据等 S-02 完成后补。
- COCO 预训练权重没有 `forklift` 类；上图只验证返回结构，不能当作叉车检测效果。
- 首次请求耗时包含模型加载，不能写成服务稳定延迟。
