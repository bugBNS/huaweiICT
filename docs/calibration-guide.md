# A-04 相机标定指南（SDG → 地面坐标）

## 1. 输入

`camera_params.jsonl` 每帧一行，关键字段：

| 字段 | 含义 |
|---|---|
| `cameraProjection` | 4×4 OpenGL 投影矩阵 |
| `cameraViewTransform` | 4×4 world→camera（row-vector 约定） |
| `renderProductResolution` | `[W, H]`，SDG 为 1920×1080 |

已验证投影约定（run_13 person 3D 框中心→2D 中心误差 0.6px）：

```text
p_cam = [x, y, z, 1] @ V
clip  = p_cam @ P
u = (ndc_x * 0.5 + 0.5) * W
v = (1 - (ndc_y * 0.5 + 0.5)) * H
```

## 2. 生成地面单应

```bash
python -m ml.geometry.calibrate_run \
  --camera-params .tmp_sdg/artifacts/<run>.ceiling_00.camera_params.jsonl \
  --out reports/calibration_run13_ceiling00.json
```

- 在地面 z=0 上取 11×11 网格（±20m），投到图像，筛出画面内的点；
- `cv2.findHomography(image→ground, RANSAC)` 求 H；
- 输出 `coordinate_mode=GROUND_METRIC` 或失败时 `IMAGE_NORMALIZED`；
- 阈值：RMSE ≤ 5px 且 inliers ≥ 6，否则不输出米制。

## 3. 把轨迹落到地面

```bash
python -m ml.geometry.map_tracks \
  --tracks reports/tracks_run13_ceiling01.json \
  --calibration reports/calibration_run13_ceiling01.json \
  --out reports/tracks_run13_ground.json
```

- 用每个 `TrackPoint.foot`（bbox 底边中心）过 H；
- 输出 `GROUND_METRIC`，`x/y` 单位 m，`position_unit=m`；
- `speed_mps/heading_rad` 仍为 null（A-05 再估）。

## 4. 本次结果（run_13）

| 相机 | inliers | 自洽 RMSE | 结论 |
|---|---:|---:|---|
| ceiling_00 | 22 | 0.0 px | GROUND_METRIC |
| ceiling_01 | 10 | 0.0 px | GROUND_METRIC |

> **重要**：RMSE=0 是“网格点由同一相机参数投影、再用 H 投回”的自洽误差，不是独立标定精度。独立检查：person 3D 框中心→2D 中心 0.6px；叉车 2D 框被画面上边界截断，未用于该检查。

## 5. 局限与下一步

- 没有人工实测地面控制点；H 来自相机参数，适合本 run/相机，不要跨相机直接复用；
- 地面近似 z=0；坡道/台阶会引入误差；
- 下一步：用 3D 框在多个帧上做独立重投影误差统计；用至少 4 个实测地面点做交叉验证；
- 未标定/误差超阈值时必须回退 `IMAGE_NORMALIZED`，禁止输出米制制动距离。
