# A-08 推理服务（本地容器 / ModelArts）

## 当前状态

- **本地服务已实现并通过单元测试**：`POST /predict`、`GET /health`、`GET /version`。
- **ModelArts 云端部署未完成**：依赖 B 的 S-02 基座（`cn-east-3` 的 ModelArts 配额、同区域 OBS 桶、ECS 调用方）。在 S-02 完成前，报告里只能写“本地容器验证通过”，不能写“已上 ModelArts”。
- 检测后端是 **YOLO11n fallback**，不是 RTMDet；COCO 预训练权重没有 `forklift` 类，必须换微调权重才能输出叉车。

## 接口

### `GET /health`

```json
{"status": "ok", "model_loaded": false, "model_version": "yolo11n-sdg", "device": "cpu"}
```

模型是懒加载的：第一次 `/predict` 才加载，所以启动后 `model_loaded` 可能先是 `false`。

### `GET /version`

```json
{"service_version": "0.1.0", "schema_version": "1.0.0", "model_version": "yolo11n-sdg"}
```

### `POST /predict`

一次 1–8 张图，JSON 传 base64（支持 `data:image/png;base64,...` 前缀）：

```json
{
  "run_id": "run_13",
  "scenario_id": "near_miss",
  "images": [
    {
      "image_id": "frame_001",
      "timestamp_ms": 0,
      "image_base64": "<base64>"
    }
  ]
}
```

返回每个输入一张 S-01 `DetectionFrame`：

```json
{
  "schema_version": "1.0.0",
  "service_version": "0.1.0",
  "model_version": "yolo11n-sdg",
  "n_images": 1,
  "elapsed_ms": 42.1,
  "frames": [
    {
      "schema_version": "1.0.0",
      "run_id": "run_13",
      "scenario_id": "near_miss",
      "model_version": "yolo11n-sdg",
      "risk_rule_version": null,
      "coordinate_mode": "IMAGE_PIXEL",
      "timestamp_ms": 0,
      "image_id": "frame_001",
      "image_width": 1920,
      "image_height": 1080,
      "detections": [
        {
          "class": "person",
          "bbox": {"x1": 10.0, "y1": 20.0, "x2": 100.0, "y2": 300.0, "unit": "px"},
          "conf": 0.91
        }
      ]
    }
  ]
}
```

错误码：`400` 参数/图片/base64 问题，`503` 模型文件不存在，`500` 推理异常。

## 环境变量

见 [`.env.example`](.env.example)。关键项：

| 变量 | 默认 | 说明 |
|---|---|---|
| `MODEL_PATH` | `yolo11n.pt` | 权重路径；ModelArts 上放 OBS 挂载/下载路径 |
| `MODEL_VERSION` | 文件名 stem | 写进 `DetectionFrame.model_version` |
| `INFERENCE_DEVICE` | `cpu` | `cpu` 或 `0` |
| `INFERENCE_CONF` / `INFERENCE_IOU` | `0.25` / `0.5` | 检测阈值 |
| `INFERENCE_IMGSZ` | `640` | 不要默认 1280；A-02 实测 1280 会掉点 |
| `INFERENCE_MAX_BATCH` | `8` | 单次最多图片数 |
| `INFERENCE_MAX_IMAGE_MB` | `10` | 单图解码后原始字节上限 |

## 本地运行

```bash
# 仓库根目录
pip install -r services/inference/requirements.txt
export MODEL_PATH=yolo11n.pt
export INFERENCE_DEVICE=cpu
uvicorn services.inference.app:app --host 0.0.0.0 --port 8000
```

另开终端：

```bash
python - <<'PY'
import base64, json, urllib.request
b64 = base64.b64encode(open('frame.jpg','rb').read()).decode()
req = urllib.request.Request(
    'http://127.0.0.1:8000/predict',
    data=json.dumps({'run_id':'run_13','scenario_id':'near_miss',
                     'images':[{'image_id':'frame_001','timestamp_ms':0,'image_base64':b64}]}).encode(),
    headers={'Content-Type':'application/json'},
)
print(urllib.request.urlopen(req).read().decode())
PY
```

单元测试不加载权重：

```bash
python -m pytest -q tests/unit/test_inference_service.py
```

## Docker

构建上下文是仓库根目录；权重不打进镜像，运行时挂载：

```bash
docker build -f services/inference/Dockerfile -t zhixun-inference:0.1 .
docker run --rm -p 8000:8000 \
  -v "$PWD/yolo11n.pt:/models/yolo11n.pt:ro" \
  -e MODEL_PATH=/models/yolo11n.pt \
  -e INFERENCE_DEVICE=cpu \
  zhixun-inference:0.1
```

## ModelArts 部署（等 S-02）

区域统一 **华东-上海一 `cn-east-3`**。A-08 需要 B 先提供：

1. ModelArts 配额/工作空间（`cn-east-3`）；
2. 同区域 OBS 桶（模型权重、样例图）；
3. 同区域 SWR 镜像仓库（自定义镜像）；
4. ECS 调用方（同 VPC，内网调用）。

建议顺序：

```text
本地 Docker /predict 通过
  -> SWR 推镜像（cn-east-3）
  -> OBS 放权重（同区域）
  -> ModelArts 创建自定义在线服务，挂载/下载 OBS 权重
  -> ECS 内网调用 /predict
  -> 保存服务配置、请求响应、日志截图到 S-02 证据链
```

在拿到上述资源前，不要写“已上 ModelArts”；最多写“本地容器验证通过，云端部署待 S-02”。

## 边界

- 输入是 base64 JSON，不是 multipart；单次 1–8 张，适合 ECS 小批量调用。
- YOLO11n 是 fallback；没有微调权重时只能可靠检测 COCO 的 `person`，不能把 `truck` 当 `forklift`。
- `DetectionFrame` 只输出 `IMAGE_PIXEL`；米制轨迹由 A-04 标定模块负责，不在本服务里伪造 `m`。
