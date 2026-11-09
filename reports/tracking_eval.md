# A-03 跟踪评估（smoke）

> **结论**：跟踪链路可跑，输出符合 S-01 `TrackSequence`；但当前是 **IoU 跟踪兜底，不是 ByteTrack**，且存在轨迹碎片。ByteTrack 目标未在本机跑通（Ultralytics `model.track` 挂起 >300s，已停止）。

## 1. 数据与配置

| 项 | 值 |
|---|---|
| 视频 | SDG run_13 `ceiling_01.rgb.mp4`，1920×1080，30fps，10s，300 帧 |
| 检测 | YOLO11n smoke 权重，conf=0.25，imgsz=640 |
| 跟踪 | `IoUTracker`，IoU 阈值 0.1，max_age=100（约 10s） |
| 输出 | `reports/tracks_run13_ceiling01.json`（IMAGE_NORMALIZED） |

## 2. 结果

| track_id | 类别 | 点数 | observed 点数 | 说明 |
|---|---|---:|---:|---|
| f1 | forklift | 300 | 154 | 主叉车轨迹，覆盖全段 |
| p1 | person | 300 | 137 | 主行人轨迹，0–5.3s |
| p2 | person | 130 | 85 | 行人轨迹后段，5.7–10s（与 p1 断开） |
| p3 | person | 110 | 3 | 静止碎片/误检，应过滤 |
| f2 | forklift | 52 | 21 | 叉车碎片 |
| p4 | person | 28 | 1 | 碎片 |

- `TrackSequence` 校验通过：`coordinate_mode=IMAGE_NORMALIZED`、`position_unit=norm`、bbox 单位 px；`observed=false` 仅用于丢失帧，不伪造检测。
- 主轨迹 f1/p1 可用；p3/p4 应过滤。

## 3. 局限

- **不是 ByteTrack**：目标跟踪器未跑通；IoU 贪心在高遮挡/交叉时容易 ID switch。
- 轨迹碎片：同一行人被拆成 p1/p2，影响 A-05 的长窗口预测。
- 未计算 IDF1/HOTA/ID switches；只做了点数与 observed 统计。
- 单 run、单相机；不能当泛化评测。
- `max_age` 的“帧/毫秒”换算目前按 100ms/单位近似，需在 ByteTrack 版本统一。

## 4. 下一步

1. 在兼容环境接 ByteTrack（`bytetrack.yaml` 或 `boxmot`），先跑 100 帧 smoke；
2. 加轨迹合并/过滤：按类别 + 时空距离合并 p1/p2，过滤 observed 比例低/点数少的碎片；
3. 计算 IDF1、ID switches、碎片率；
4. 用 A-01 的独立 run 重跑。

## 5. 文件

- `ml/tracker/iou_tracker.py`（兜底）
- `ml/tracker/track_video.py`（视频→TrackSequence）
- `tests/unit/test_tracker.py`（IoU/ID/observed/schema）
- `reports/tracks_run13_ceiling01.json`
