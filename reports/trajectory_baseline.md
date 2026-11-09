# A-05 CV/CA 轨迹预测基线（smoke）

> **结论**：CV 是可用的基线，CA 在 200ms 采样上被加速度噪声放大，明显更差。单 run、同相机，不是泛化评测。

## 1. 数据与配置

| 项 | 值 |
|---|---|
| 轨迹 | `reports/tracks_run13_ground.json`（GROUND_METRIC，run_13 ceiling_01） |
| 可用轨迹 | 3 条（f1、p1、p2）；跳过 2 条（p3/p4 碎片） |
| 采样 | 200 ms（5Hz） |
| 历史/预测 | 8 步（1.6s）/ 10 步（2.0s） |
| 评估窗口 | 17 个（anchor 每 3 步） |
| 坐标 | 地面米制；速度/航向由相邻点估计 |

> 为什么不是 2.4s/4.0s：person 轨迹被跟踪拆成 0–5.3s 与 5.7–10s 两段，长窗口样本不足；先缩短窗口跑通，正式评测用 ByteTrack/更长轨迹再恢复长窗口。

## 2. 结果（均值）

| 方法 | 类别 | n | ADE (m) | FDE (m) | 物理违规率 |
|---|---|---:|---:|---:|---:|
| **CV** | forklift | 11 | **2.268** | **4.321** | 0.273 |
| **CV** | person | 6 | **0.387** | **0.767** | 0.000 |
| CA | forklift | 11 | 17.368 | 43.585 | 0.859 |
| CA | person | 6 | 1.488 | 3.646 | 0.278 |

- CV：匀速假设在短窗口/低速场景可用；person 误差 <0.4m。
- CA：二阶差分对检测抖动非常敏感，叉车 ADE 17m，**不可用**；除非加平滑/约束，不能作为推荐基线。
- `miss_rate=0` 只表示“窗口都够长”，不代表模型从不失败；p3/p4 已被前置过滤。

## 3. 局限

- 单 run、单相机、同场景；不能写“泛化到新仓库”。
- 轨迹来自 IoU 跟踪（非 ByteTrack），p1/p2 断裂；窗口 1.6s/2.0s 偏短。
- 没有真实速度/航向标签；物理违规率是预测点差分，阈值 3m/s 为配置值。
- CA 未做平滑/约束；结论只代表当前实现。
- 没有多模态/不确定性；Hetero-GRU 是 P1，未启动。

## 4. 下一步

1. 接 ByteTrack / 合并 p1+p2，恢复 2.4s/4.0s 窗口；
2. CA 加 Savitzky-Golay/卡尔曼平滑后再比较；
3. 用 A-01 独立 run 做 train/val/test，报告均值/分位数；
4. P1 Hetero-GRU 只在 P0 全绿后启动。

## 5. 文件

- `ml/predictor/baselines.py`
- `ml/predictor/metrics.py`
- `ml/predictor/run_baseline.py`
- `tests/unit/test_predictor.py`
- `reports/trajectory_baseline.json`
- `reports/predictions_run13_cv.json` / `..._ca.json`
