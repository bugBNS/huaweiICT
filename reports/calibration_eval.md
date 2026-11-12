# A-04 标定评估（run_13）

## 结果

| 相机 | 地面网格内点 | 自洽 RMSE | 坐标模式 | 独立检查 |
|---|---:|---:|---|---|
| ceiling_00 | 22 | 0.0 px | GROUND_METRIC | person 3D→2D 0.6px |
| ceiling_01 | 10 | 0.0 px | GROUND_METRIC | 用于轨迹落地 |

- 输出：`reports/calibration_run13_ceiling00.json`、`..._ceiling01.json`
- 地面轨迹：`reports/tracks_run13_ground.json`，6 条；主轨迹 f1 x∈[-3.75,1.38]m、y∈[-3.04,-0.17]m；p1 x∈[-0.18,0.17]m、y∈[-1.0,-0.1]m。
- p3（x≈0.47, y≈1.55，110 点仅 3 observed）是静止碎片，A-05 已过滤。

## 诚实边界

- `RMSE=0` 是**自洽误差**（同一相机参数生成网格点再投回），不是独立标定精度；
- 独立检查只用了 person 3D 框中心（0.6px）；叉车 2D 框被上边界截断，未纳入；
- 未使用人工实测控制点；H 不跨相机复用；
- 地面假设 z=0，坡道/台阶会破坏假设。

## 文件

- `ml/geometry/homography.py`
- `ml/geometry/calibrate_run.py`
- `ml/geometry/map_tracks.py`
- `tests/unit/test_homography.py`
- `docs/calibration-guide.md`
