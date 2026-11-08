# B 仿真/后端/云负责人｜Issue 清单（智巡卫士 2.0）

> 你的范围：**S-01、S-02、B-02 ~ B-09**。代码目录：`sim/`、`services/api/`、`services/worker/`、`infra/`、`schemas/`、`tests/`。
> 你是全队的“接口 + 云基座 + 关键路径”负责人：S-01 和 S-02 必须在 W1 打通，不能拖到 W4。
> 时间基准：2026-11-08，3 周 MVP；B-09 的 500 场景跑批是国奖核心证据，最晚 W4 启动。

---

## 0. 你的内部顺序

| 时间 | 做什么 | 产出 |
|---|---|---|
| Day1 | S-01 契约/Schema/仓库骨架 | `schemas/`、`samples/`、`docs/api-contract.md` |
| Day1–3 | S-02 华为云基座（账号/配额/OBS/RDS/Redis/ECS） | 云资源清单、连通性截图 |
| Day2–5 | B-02 场景生成器 | 100 场景样例、map JSON |
| W2 | B-03 运动学；B-04 风险场初版；B-07 mock API | 轨迹/风险/API mock |
| W3 | B-05 策略；B-06 排序；B-07 真接 RDS/Redis；B-08 部署 | 4 策略、云端链路 |
| W4 | B-09 端到端 + 500 场景跑批 | 实验报告、Pareto/消融 |

## 1. 你等谁（跨人依赖，只有这些）

| 你的 Issue | 必须先完成 | 谁提供 | 如果没完成怎么办 |
|---|---|---|---|
| B-04 风险场 | A-04 坐标模式、A-05 预测基线 | A | 先用归一化坐标 + CV 基线跑通；不要伪造米制 |
| B-08 云部署 | A-08 ModelArts 推理服务 | A | 先用 ECS 容器推理，如实标注；不要写“已上 ModelArts” |
| B-09 端到端 | A-03 轨迹、A-05 预测、A-08 推理 | A | 先用 mock/固定样例串 pipeline，再替换真实输出 |
| B-07 API 字段 | C-01 UI 字段清单 | C | 先按 S-01 sample JSON 做；C-01 出来后对齐，不阻塞 |

> B-02、B-03、B-05、B-06 不依赖别人；S-01/S-02 是你自己的，必须最先做。

## 2. 谁等你（你的交付是别人的前置）

| 你交付 | 谁要用 | 用途 |
|---|---|---|
| S-01 Schema/样例 | A-02/A-03/A-05、C-02 | 全队接口 |
| S-02 云基座 | A-08、C-04 | ModelArts/OBS/ECS 权限 |
| B-02 地图/场景 | A-06、C-03 | 训练数据、3D 场景 |
| B-04 风险网格 | C-06 | 风险热力场 |
| B-05/B-06 策略/排序 | C-07 | 策略对比/推荐 |
| B-07 API | C-04、C-07 | 视频任务、策略/复核 |
| B-09 端到端 | C-08 | 演示闭环 |

---

## 3. Issue 详情

### S-01 接口契约、Schema 与仓库骨架（B 主责）

- **优先级/阶段**：P0 / W1 Day1–2 冻结
- **目标**：三人用同一份 schema 和样例 JSON 开发；接口变更走 PR
- **用什么实现**：目录骨架；Pydantic + JSON Schema；坐标模式 `GROUND_METRIC / IMAGE_NORMALIZED`；统一时间戳 ms、速度 m/s、航向 rad、类别小写；版本字段 `schema_version/model_version/risk_rule_version/scenario_id/run_id`
- **华为云关系**：**码道** 生成 Pydantic/Schema/测试；无运行时服务
- **交付物**：`schemas/*.json`、`schemas/models.py`、`docs/api-contract.md`、`samples/*.json`、`tests/unit/test_schema_validation.py`、`.env.example`、`README.md`
- **验收标准**：A/B/C 用同一份 sample JSON 能读写；非法字段/单位被测试拦截；未标定不能出现 `m`
- **依赖/并行**：无前置；A-01、B-02、C-01/C-02 并行；**Day2 三人评审冻结**

### S-02 华为云基座与合规证据链（B 主责，资格线）

- **优先级/阶段**：P0 / W1 打通，W3 补齐证据
- **目标**：W1 验证账号/区域/配额/代金券，打通 OBS→RDS→Redis→ECS；W2 接 ModelArts
- **用什么实现**：IAM 子用户（不共用 root）；VPC + 安全组；ECS；RDS MySQL；DCS Redis；OBS 私有桶；ModelArts 自定义推理；预算告警；资源标签 `project=zhixun/env=dev`；费用/清理清单
- **华为云关系**：**码道、RDS、Redis、OBS、ECS、ModelArts、VPC/EIP**；CES/LTS 可选
- **交付物**：`infra/huaweicloud/deploy.md`、部署脚本、`cost-and-cleanup.md`、`evidence/`（截图/日志/对象路径/服务配置）、`docs/cloud-evidence.md`
- **验收标准**：OBS 上传下载成功；RDS CRUD 成功；Redis 入队/出队成功；ModelArts `/predict` 返回检测结果；ECS 公网可访问 API；码道记录可追溯；仓库无 AK/SK
- **依赖/并行**：S-01；A-08（W2 接入）；B-07（W2 接入）；账号/配额/OBS/RDS/Redis 可在 W1 并行启动
- **止损**：W1 结束拿不到 ModelArts 配额 → 先 ECS 容器推理，**如实标注**，文档写阻塞点；不要伪称云端推理

### B-02 仓库地图与可控交互场景生成器

- **优先级/阶段**：P0 / W1
- **目标**：生成可复现场景，为轨迹训练、风险计算、反事实推演提供可控数据
- **用什么实现**：Python/NumPy + YAML；30m×20m 地图、货架/通道/交叉口/等待线；person/forklift 起点/目标/速度/反应时间/行为脚本；seed + train/val/test 分组；输出轨迹与 TTC/PET/碰撞标签
- **华为云关系**：**OBS** 场景数据/样例；**RDS** 场景元数据（可选）；**码道** 生成器/测试
- **交付物**：`sim/scenario/*`、`configs/scenario_defaults.yaml`、`tests/scenarios/test_scenario_reproducibility.py`、`docs/simulation-data.md`、100 场景样例
- **验收标准**：同 seed 同输出；轨迹不穿障碍；字段符合 S-01；参数/seed 全记录
- **依赖/并行**：S-01；与 A-01/A-02、C-01/C-02 并行；**A-06、C-03 依赖本 Issue**

### B-03 叉车/行人简化运动学引擎

- **优先级/阶段**：P0 / W2
- **目标**：可重复的 2D 运动学模拟器，为每种策略提供公平的未来轨迹
- **用什么实现**：NumPy；dt=0.1s；叉车 unicycle/bicycle-lite（速度/加速度/角速度约束）；行人 waypoint/减速/停止/绕行；边界/障碍约束；同一初始状态复制多实例
- **华为云关系**：**码道** 生成动力学/单测；无运行时服务
- **交付物**：`sim/dynamics/forklift.py`、`pedestrian.py`、`engine.py`、`tests/unit/test_dynamics.py`、`reports/dynamics_validation.md`
- **验收标准**：固定初始状态/动作/seed 确定性；停车不瞬移、绕行不穿墙；碰撞/越界可检测
- **依赖/并行**：B-02；与 A-03/A-05、C-03 并行；**B-04/B-05 依赖本 Issue**

### B-04 几何冲突、TTC/PET 与动态风险场

- **优先级/阶段**：P0 / W2–W3
- **目标**：把预测轨迹变成可解释的时空风险指标和地面风险网格
- **用什么实现**：叉车矩形/行人圆-椭圆几何相交；制动包络；TTC/PET/最小间距（无冲突返回 null）；0–1 场景内风险指数；`(x,y,t,risk)` 网格；权重/阈值配置化 + 敏感性分析
- **华为云关系**：**RDS** 风险事件/指标；**OBS** 风险栅格 JSON；**码道** 生成几何/风险测试
- **交付物**：`sim/risk/geometry.py`、`ttc_pet.py`、`braking_envelope.py`、`risk_field.py`、`configs/risk_defaults.yaml`、`tests/unit/test_risk_metrics.py`、`reports/risk-model-assumptions.md`
- **验收标准**：迎面/平行/交叉/静止手工场景方向正确；TTC/PET 无效返回 null；输出含坐标模式/规则版本/参数快照
- **依赖/并行**：B-03 + **A-04/A-05（A）**；A-06 可选增强；**C-06 依赖本 Issue**

### B-05 反事实干预动作库与多策略仿真

- **优先级/阶段**：P0 / W3
- **目标**：同一初始状态下模拟 KEEP/减速/停车/等待/绕行，输出可比较结果
- **用什么实现**：策略 ID：KEEP、F_SLOW_75、F_SLOW_50、F_STOP、P_YIELD（可选 DETOUR）；动作参数/触发时机/持续时间/约束；同一 initial_state 独立仿真；记录轨迹/风险/延误/路径/约束状态
- **华为云关系**：**RDS** counterfactual_runs/strategy_results；**OBS** 轨迹 JSON；**码道** 生成动作库/测试
- **交付物**：`sim/interventions/actions.py`、`runner.py`、`schemas/counterfactual.schema.json`、`tests/scenarios/test_strategy_comparison.py`、KEEP vs STOP vs SLOW 样例
- **验收标准**：≥4 策略完整可比较；同初始状态/seed/参数；不可行状态明确返回
- **依赖/并行**：B-03、B-04；与 A-06/C-05 并行；**B-06、C-07 依赖本 Issue**

### B-06 安全约束下的风险—效率排序

- **优先级/阶段**：P0 / W3
- **目标**：在安全约束优先下比较策略风险降低与效率代价，输出推荐与理由
- **用什么实现**：风险上限约束 + 加权目标；CVaR（可选）；枚举候选策略；`NO_FEASIBLE_STRATEGY`；权重/阈值敏感性分析；KEEP 保留作对照
- **华为云关系**：**RDS** 排序结果/推荐理由；**码道** 生成目标函数/测试
- **交付物**：`sim/optimizer/objective.py`、`ranker.py`、`cvar.py`（可选）、`configs/optimizer_defaults.yaml`、`reports/strategy-optimization.md`、`tests/unit/test_optimizer.py`
- **验收标准**：高风险策略不会在硬约束下被推荐；无可行解明确返回；排序可复现、可解释
- **依赖/并行**：B-04、B-05；与 A-07/C-06 并行；**C-07 依赖本 Issue**

### B-07 FastAPI、RDS MySQL、Redis 与任务流（P0，资格线）

- **优先级/阶段**：P0 / W2 mock，W3 真接
- **目标**：为前端提供稳定 API，保存视频/任务/场景/结果/复核；Redis 真做队列与状态
- **用什么实现**：FastAPI + Pydantic；SQLAlchemy + Alembic；MySQL 表 users/videos/analysis_jobs/scenarios/tracks/predictions/risk_events/counterfactual_runs/strategy_results/reviews；Redis List/Stream 队列 + 状态 key；OBS 预签名 URL；mock 模式
- **华为云关系**：**ECS** API/Worker；**RDS for MySQL** 业务库；**DCS Redis** 队列/缓存；**OBS** 视频/证据；**码道** 生成 API/迁移/测试
- **交付物**：`services/api/`、`services/worker/`、`infra/db/migrations/`、OpenAPI JSON、`tests/integration/test_api_flow.py`、`docs/api-contract.md` 更新
- **验收标准**：创建任务→查询结果 mock 闭环；非法请求 4xx；前端可集成；RDS/Redis 真实读写截图；无密钥泄漏
- **依赖/并行**：S-01；mock 可先做；完整联调依赖 A/B；**C-04/C-07 依赖本 Issue**

### B-08 华为云部署与证据链

- **优先级/阶段**：P0 / W3
- **目标**：把 API/Worker/RDS/Redis/OBS/ModelArts 部署成可演示、可复现的云端链路
- **用什么实现**：Docker Compose；VPC/安全组；ECS；RDS/Redis 仅内网；OBS 私有桶；ModelArts 服务调用；EIP；CES/LTS 可选；停止/释放脚本
- **华为云关系**：**ECS/RDS/Redis/OBS/ModelArts/VPC/EIP**；**码道** 部署脚本/文档；CES/LTS 可选
- **交付物**：`infra/docker/`、`docker-compose.yml`、`infra/huaweicloud/deploy.md`、部署脚本、`cost-and-cleanup.md`、健康检查/调用日志/架构图
- **验收标准**：干净环境按文档启动；API 可访问并调用 ModelArts；RDS 不暴露公网；OBS 私有；密钥不入库；费用可控
- **依赖/并行**：B-07 + **A-08（A）** + S-02；与 C-08 并行；**B-09 依赖本 Issue**

### B-09 端到端流水线与 500 场景实验跑批

- **优先级/阶段**：P0 / W3–W4
- **目标**：串起“视频/场景→感知→预测→风险→策略→结果”，并跑出可复现实验数字
- **用什么实现**：Worker 状态机 + 重试；run manifest（输入 hash、seed、模型/规则版本、参数快照）；批量跑 500 hold-out 场景；风险/延误/Pareto/消融统计
- **华为云关系**：**OBS/RDS/Redis/ModelArts** 全链路；**码道** 生成 pipeline/实验脚本
- **交付物**：`services/worker/pipeline.py`、`docs/e2e-runbook.md`、`tests/integration/test_end_to_end.py`、`reports/e2e-experiment.md`、500 场景结果
- **验收标准**：同输入/配置可复现；UI 可查任务状态；所有结果可追溯；实验报告含均值/分位数/失败案例
- **依赖/并行**：**A-03/A-05/A-08（A）** + B-04/B-06/B-07；与 C-08 并行；**国奖核心证据**

---

## 4. 每周验收（B 的 Definition of Done）

- **W1**：S-01 冻结；S-02 OBS/RDS/Redis/ECS 连通；B-02 100 场景可复现；码道记录 ≥3 条
- **W2**：B-03 确定性；B-04 手工场景通过；B-07 mock API；A-04/A-05 已接入
- **W3**：B-05 四策略；B-06 排序；B-07 真接 RDS/Redis；B-08 云端可访问
- **W4**：B-09 500 场景/Pareto/消融；所有云证据归档；不再加功能

## 5. PR 自检

- [ ] 关联 Issue；schema 变更同步 `docs/api-contract.md`
- [ ] 仿真参数/阈值/权重配置化并随结果保存
- [ ] 不向真实设备发控制命令；页面/接口标注“仿真建议”
- [ ] 无可行策略返回明确状态；TTC/PET 无效返回 null，不补造
- [ ] RDS/Redis/OBS/ModelArts 调用有日志/截图
- [ ] 没有大视频/大权重/密钥入库

## 6. GitHub Issue 模板

```markdown
## 目标
## 用什么实现
## 华为云关系（服务/用途/证据）
## 交付物
## 验收标准
## 依赖 / 并行
```
