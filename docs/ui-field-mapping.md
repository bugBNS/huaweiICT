# 智巡卫士 2.0｜UI 字段映射（C-01）

> 给谁看：A（算法输出）、B（API/Schema）、C（前端）。
> 用途：把页面上每个可见字段落到数据来源、单位、空值规则，避免 S-01 冻结后返工。
> 状态：**已按 S-01 1.0.0 对齐**（2026-11-12）：`class`、`GROUND_METRIC`/`IMAGE_NORMALIZED`/`IMAGE_PIXEL`、单 `model_version`；后续 schema 变更仍需同步本表。
> 原则：页面只展示后端/算法给的值，**不在前端计算或伪造算法结果**。

图例：`必填` = 页面依赖该字段才能渲染；`可空` = 缺失时走空状态文案，不报错。

---

## 0. 全局字段（每个页面底部状态栏）

| UI 字段 | schema 字段（建议） | 来源 | 类型 | 单位 | 空值规则 |
|---|---|---|---|---|---|
| 模型版本 | `model_version` | A-08 / B-04 各自文档 | string | — | 缺失显示「版本未知」 |
| 坐标模式 | `coordinate_mode` | A-04 标定 / B-02 场景 | enum `GROUND_METRIC` / `IMAGE_NORMALIZED` / `IMAGE_PIXEL` | — | 未标定强制 `IMAGE_NORMALIZED`（检测为 `IMAGE_PIXEL`），禁用一切米制字段 |
| 风险模型版本 | `model_version` | B-04 风险文档 | string | — | 缺失显示「—」 |
| 连接状态 | —（前端连接态） | 前端 | enum | — | 断线显示重连中，不缓存旧结果当新结果 |

---

## 1. 视频（`/videos`）

| UI 字段 | schema 字段（建议） | 来源 | 类型 | 单位 | 必填 | 空值规则 |
|---|---|---|---|---|---|---|
| 视频 ID | `video.id` | B-07 | string | — | 是 | — |
| 视频名称 | `video.name` | 用户 | string | — | 是 | — |
| 时长 | `video.duration_s` | OBS 元数据 | number | 秒 | 否 | 解析失败显示「—」 |
| 分辨率 | `video.width` / `video.height` | OBS 元数据 | int | 像素 | 否 | 显示「未知」 |
| 上传时间 | `video.uploaded_at` | B-07 | datetime | — | 是 | — |
| 标定状态 | `video.calibration_status` | B-02 | enum `uncalibrated`/`calibrated`/`invalid` | — | 是 | 默认 `uncalibrated` |
| 分析状态 | `task.status` | B-07 | enum 见 §6 | — | 是 | 无任务显示「未分析」 |
| 缩略图 | `video.thumbnail_url` | OBS | url | — | 否 | 占位图 |

上传走 OBS 预签名 URL，前端只拿 `upload_url` + `video_id`，不经后端转发文件。

---

## 2. 场景标定（`/calibration`）

| UI 字段 | schema 字段（建议） | 来源 | 类型 | 单位 | 空值规则 |
|---|---|---|---|---|---|
| 参考点像素坐标 | `calibration.points[].pixel` | 用户点选 | `[x, y]` | 像素 | 少于 4 点禁用保存 |
| 参考点实际坐标 | `calibration.points[].world` | 用户输入 | `[x, y]` | 米 | 同上 |
| 摄像头高度 | `calibration.camera_height_m` | 用户 | number | 米 | 可空，空则不参与外参 |
| 俯仰角 | `calibration.pitch_deg` | 计算/用户 | number | 度 | 可空 |
| 重投影误差 | `calibration.reprojection_error_px` | B-02 | number | 像素 | 未计算显示「待计算」 |
| 坐标模式 | `coordinate_mode` | A-04 / B-02 | enum | — | 标定未通过保持 `IMAGE_NORMALIZED`（检测为 `IMAGE_PIXEL`） |

标定未通过时，分析页所有米制字段（速度、TTC 米值、距离）一律不渲染，改显示像素值并加提示。

---

## 3. 检测与轨迹（`/analysis`，A-03）

| UI 字段 | schema 字段（建议） | 来源 | 类型 | 单位 | 空值规则 |
|---|---|---|---|---|---|
| 对象 ID | `tracks[].track_id` | A-03 | string | — | — |
| 对象类型 | `tracks[].class` | A-02/A-03 | enum `forklift`/`person` | — | 未知类型灰色显示 |
| 历史轨迹点 | `tracks[].history[].position` | A-03 | `[x, y, t]` | 米或像素 | 跟随坐标模式 |
| 速度 | `tracks[].points[].speed_mps` | A-03 | number | m/s | 非 `GROUND_METRIC` 不显示 |
| 观测标记 | `tracks[].history[].observed` | A-03 | bool | — | `false` 用虚线/淡色，文案「观测缺失」 |

---

## 4. 预测分支（`/analysis`，A-05）

| UI 字段 | schema 字段（建议） | 来源 | 类型 | 单位 | 空值规则 |
|---|---|---|---|---|---|
| 预测时域 | `prediction.horizon_s` | A-05 | number | 秒 | — |
| 分支数 K | `prediction.modes.length` | A-05 | int | — | 与后端数组长度一致，前端不补分支 |
| 分支轨迹 | `prediction.modes[].trajectory` | A-05 | `[[x, y, t]]` | 米/像素 | — |
| 分支得分 | `prediction.modes[].score` | A-05 | number 0–1 | — | 标注「未校准得分，非概率」 |
| 预测模型 | `model_version` | A-08 预测文档 | string | — | — |

得分是未校准的 mode score，UI 文案用「得分」不用「概率」。

---

## 5. 风险（`/analysis`、`/simulation`，B-04）

| UI 字段 | schema 字段（建议） | 来源 | 类型 | 单位 | 空值规则 |
|---|---|---|---|---|---|
| 风险网格 | `risk.grid` | B-04 | 二维 number 数组 | 指数 0–1 | 缺失不画热力图 |
| 网格原点/分辨率 | `risk.origin` / `risk.cell_size_m` | B-04 | number | 米 | 非 `GROUND_METRIC` 不渲染 |
| 时间切片 | `risk.slices[].t` | B-04 | number | 秒 | 与时间轴对齐 |
| TTC | `risk.metrics.ttc_s` | B-04 | number | 秒 | `null` 显示「不适用」 |
| PET | `risk.metrics.pet_s` | B-04 | number | 秒 | 同上 |
| 风险指数 | `risk.metrics.risk_index` | B-04 | number 0–1 | — | 文案用「风险指数」，禁止写「事故概率」 |

风险指数不是概率，面板固定加注「风险指数，非事故发生概率」。

---

## 6. 任务状态（B-07）

`task.status` 枚举，前端只识别这五个值，其余归入「未知」并显示原始值：

| 值 | UI 文案 | 颜色 |
|---|---|---|
| `queued` | 队列中 | 灰 |
| `running` | 分析中 | 蓝 |
| `succeeded` | 已完成 | 绿 |
| `failed` | 失败 | 红 |
| `paused` | 暂停 | 橙 |

失败时展示 `task.error_message`（后端给的人读文案），不展示堆栈。

---

## 7. 策略对比（`/simulation`，B-05 / B-06）

| UI 字段 | schema 字段（建议） | 来源 | 类型 | 单位 | 空值规则 |
|---|---|---|---|---|---|
| 策略类型 | `strategies[].type` | B-05 | enum `keep`/`slow_down`/`stop`/`reroute` | — | — |
| 策略参数 | `strategies[].params` | B-05 | object | — | 如目标速度 m/s |
| 可行性 | `strategies[].feasible` | B-05 | bool | — | `false` 置灰，不显示指标 |
| 不可行原因 | `strategies[].infeasible_reason` | B-05 | string | — | 可行时为空 |
| 风险指数 | `strategies[].metrics.risk_index` | B-04 | number | — | 同 §5 |
| 延误 | `strategies[].metrics.delay_s` | B-05 | number | 秒 | — |
| 绕路 | `strategies[].metrics.detour_m` | B-05 | number | 米 | 非 `GROUND_METRIC` 不显示 |
| 推荐策略 | `recommendation.strategy_type` | B-06 | enum | — | 无可行解时为空，UI 显示「无可行策略」 |
| 推荐理由 | `recommendation.reason` | B-06 | string | — | 后端生成，前端不拼装 |

推荐卡片固定带标签「仿真建议，需人工确认」。无 `recommendation` 时不显示推荐，不允许前端自行挑一个。

---

## 8. 人工复核（`/events`，B-07 写 RDS）

| UI 字段 | schema 字段（建议） | 方向 | 类型 | 规则 |
|---|---|---|---|---|
| 事件 ID | `event.id` | 读 | string | — |
| 复核状态 | `review.status` | 读 | enum `pending`/`confirmed`/`rejected` | — |
| 复核动作 | `review.action` | 写 | enum `confirm`/`reject` | — |
| 驳回理由 | `review.reason` | 写 | string | `reject` 时必填，前端校验 |
| 复核人 | `review.reviewer` | 写 | string | 取当前登录用户 |
| 复核时间 | `review.reviewed_at` | 读 | datetime | 后端生成 |

确认/驳回是唯一由前端写入的业务数据，其余全部只读。

---

## 9. 实验对比（`/experiments`，B-09）

| UI 字段 | schema 字段（建议） | 来源 | 单位 | 备注 |
|---|---|---|---|---|
| ADE / FDE | `experiment.metrics.ade_m` / `fde_m` | A 实验报告 | 米 | 未标定场景集不展示 |
| 风险降低率 | `experiment.metrics.risk_reduction` | B-09 | 比例 | 标注为仿真统计 |
| 策略采纳率 | `experiment.metrics.adoption_rate` | B-09 | 比例 | — |
| 推理耗时 | `experiment.metrics.latency_ms` | A-08 | 毫秒 | — |
| 场景数 | `experiment.scenario_count` | B-09 | — | 如实显示，不凑整 |

演示材料若用的是 mock 或小样本，页面和录屏都标注「演示数据」。

---

## 10. 待 B/A 确认（S-01 评审用）

- [ ] 上面「schema 字段」列的命名是否与 `schemas/` 一致，不一致以 schema 为准回改。
- [ ] `coordinate_mode` 由谁下发：视频级还是任务级。
- [ ] `prediction.modes[].score` 是否保证未校准，UI 文案依赖这一点。
- [ ] `risk.metrics` 的 `null` 语义：不适用 vs 计算失败，两者 UI 文案不同。
- [ ] 策略枚举是否固定为 `keep`/`slow_down`/`stop`/`reroute` 四个。
- [ ] 复核写入接口的字段与 RDS 表是否一一对应。
