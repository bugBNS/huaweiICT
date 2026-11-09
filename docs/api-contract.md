# 智巡卫士 2.0 API / 数据契约（S-01）

`schema_version` 当前冻结为 **1.0.0**。变更必须走 PR，并同步改 `schemas/models.py`、`schemas/*.json`、`samples/*.json` 和本文件。

A 做检测/跟踪/预测，B 做场景/风险/策略/API，C 做前端，三人都只读写这些 JSON。

## 统一约定

| 字段 | 规则 |
|---|---|
| `schema_version` | 字符串，必须是 `1.0.0` |
| `run_id` / `scenario_id` | 一次运行 / 一个场景的稳定 ID |
| `model_version` / `risk_rule_version` | 可空；有结果时必须带上 |
| `timestamp_ms` | Unix 或相对视频起点，单位毫秒 |
| `class` | 只允许小写 `person` / `forklift` |
| 速度 | 字段名 `speed_mps`，单位 m/s，**仅** `GROUND_METRIC` 可出现 |
| 航向 | `heading_rad`，弧度，仅 `GROUND_METRIC` |
| 坐标模式 | `GROUND_METRIC` / `IMAGE_NORMALIZED` / `IMAGE_PIXEL` |

### 坐标模式

- `IMAGE_PIXEL`：检测框，bbox 单位必须是 `px`。
- `IMAGE_NORMALIZED`：未标定轨迹，x/y ∈ [0,1]，`position_unit=norm`。禁止 `m`、禁止 `speed_mps`。
- `GROUND_METRIC`：已标定或仿真地图，`position_unit=m`。地图、风险距离、策略路径只在这一种模式下谈米。

未标定 **不能** 输出米制距离、制动距离、`min_clearance_m`。TTC/PET 无效时返回 `null`，不要编造。

score 语义默认 `uncalibrated_model_score`，前端不要显示成事故概率。

反事实结果必须 `simulation_advice=true`，文案为仿真建议，不向真实设备发控制命令。无可行策略时：`no_feasible_strategy=true` 且 `recommended_strategy=null`。

## 样例文件（给 A/C 对齐）

| 文件 | 模型 | 谁读写 |
|---|---|---|
| `samples/detection.json` | `DetectionFrame` | A 写，C/B 读 |
| `samples/tracks.json` | `TrackSequence` | A 写 |
| `samples/prediction.json` | `PredictionBundle` | A 写，B 风险场读 |
| `samples/map.json` | `MapScenario` | B 写，A-06/C-03 读 |
| `samples/risk_field.json` | `RiskField` | B 写，C-06 读 |
| `samples/counterfactual.json` | `CounterfactualResult` | B 写，C-07 读 |
| `samples/analysis_job.json` | `AnalysisJob` | B API，C-04 读 |
| `samples/review.json` | `ReviewRecord` | C 写，B 落 RDS |

## 后续 HTTP API（B-07，字段先按上面冻结）

真接口还没有，W2 mock 时路径如下。请求/响应 body 必须能通过对应 Pydantic 模型。

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/v1/jobs` | 创建分析任务 |
| GET | `/v1/jobs/{job_id}` | 查询任务状态 |
| GET | `/v1/runs/{run_id}/detections` | 检测 |
| GET | `/v1/runs/{run_id}/tracks` | 轨迹 |
| GET | `/v1/runs/{run_id}/predictions` | 预测 |
| GET | `/v1/runs/{run_id}/risk` | 风险场 |
| GET | `/v1/runs/{run_id}/counterfactuals` | 策略对比 |
| POST | `/v1/jobs/{job_id}/reviews` | 人工复核 |
| POST | `/v1/obs/presign` | 视频上传预签名 |

非法请求返回 4xx，不要 200 里塞错误。

## 本地校验

```powershell
cd D:\Desktop\huaweiICT
python -m pip install -r requirements.txt
python -m pytest tests/unit/test_schema_validation.py
python -m schemas.export_json_schema
```
