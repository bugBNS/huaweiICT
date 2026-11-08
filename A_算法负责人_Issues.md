# A 算法负责人｜Issue 清单（智巡卫士 2.0）

> 你的范围：**S-03 + A-01 ~ A-08**。代码目录：`ml/`、`services/inference/`、`reports/`、`docs/dataset-and-license.md`。
> 工作方式：每条 Issue 一个分支 `feat/A-xx-<slug>`；PR 关联 Issue；必须写“运行命令 + 结果 + 失败案例”。
> 时间基准：2026-11-08，3 周 MVP；**A-06/A-07 是 P1，W2 结束 P0 没闭环就直接砍**。

---

## 0. 你的内部顺序（不用画箭头，按这个做）

| 时间 | 做什么 | 产出 |
|---|---|---|
| Day1 | S-03 许可/开源清单；A-01 数据索引 | 许可清单、样本 manifest |
| Day2–4 | A-02 检测 smoke（单图→短视频） | 一张图/一段视频的检测 JSON |
| Day5–7 | A-02 完成；A-03 跟踪 | 检测指标、track_id 序列 |
| W2 | A-04 标定；A-05 CV/CA | 坐标模式、ADE/FDE 基线 |
| W2–W3 | A-08 ModelArts 推理封装 | 云端 `/predict` 可被 ECS 调用 |
| W3（可选） | A-06 Hetero-GRU、A-07 不确定性 | 对比/消融报告；**可砍** |

## 1. 你等谁（跨人依赖，只有这些）

| 你的 Issue | 必须先完成 | 谁提供 | 如果没完成怎么办 |
|---|---|---|---|
| A-02 | S-01 契约/Schema | B | 先按 `samples/*.json` 写适配器；Day2 没冻结就催 B |
| A-08 | S-02 华为云基座（账号/配额/ModelArts） | B | 先本地 Docker 跑通；云端证据如实标“未部署” |
| A-06（P1） | B-02 场景生成器 | B | 没数据就砍 A-06，不阻塞 |

> 其他都不需要等别人：A-01、A-03、A-04、A-05 只依赖你自己的前置。

## 2. 谁等你（你的交付是别人的前置）

| 你交付 | 谁要用 | 用途 |
|---|---|---|
| A-03 轨迹 | B-09、C-05 | 端到端流水线、3D 轨迹层 |
| A-04 坐标模式 | B-04 | 米制/归一化风险计算 |
| A-05 预测 | B-04、B-09、C-05 | 风险场、端到端、预测分支 |
| A-08 推理服务 | B-08、B-09 | 云部署、端到端 |
| A-01 manifest/许可 | S-03 | 开源与数据合规 |

---

## 3. Issue 详情

### S-03 数据许可、开源与第三方清单（A 主责）

- **优先级/阶段**：P0 / W1 启动，W3 完成
- **目标**：SDG-Warehouse/模型/3D 资产许可清楚；仓库可开源、可复现、无密钥
- **用什么实现**：数据集卡、OpenMDW-1.1 文本、RTMDet（Apache-2.0）、ByteTrack（MIT）等清单；`THIRD_PARTY_NOTICES.md`；Gitee/GitHub；LICENSE（MIT/Apache-2.0）；`.gitignore`；密钥扫描
- **华为云关系**：**OBS** 存数据清单/样例（不存全量 549GiB）；**码道** 生成 README/许可清单/测试；无运行时服务
- **交付物**：`docs/dataset-and-license.md`、`THIRD_PARTY_NOTICES.md`、`LICENSE`、`README.md`、`.gitignore`、开源链接
- **验收标准**：仓库无原始大视频/大权重/密钥；所有第三方组件有许可证与来源；干净环境按 README 能启动
- **依赖/并行**：A-01；与 S-01 并行

### A-01 SDG-Warehouse 数据索引、样本筛选与许可登记

- **优先级/阶段**：P0 / W1
- **目标**：只读 metadata，筛选 10–20 个 `forklift_human_nearmiss` run，产出可复现清单，不下载全量 549GiB
- **用什么实现**：`huggingface_hub` + `pandas` + `pyarrow` 读 `runs.parquet/clips.parquet`；WebDataset shard 流式读取；按 run/seed 分组，禁止同 run 多视角泄漏；记录 hash
- **华为云关系**：**OBS** 存筛选后的样本清单/抽帧/样例；**码道** 生成解析脚本与单测；不把全量数据搬上云
- **交付物**：`ml/data/index_sdg.py`、`select_runs.py`、`data/manifests/sdg_selected_runs.csv`、`docs/dataset-and-license.md`、运行日志
- **验收标准**：新环境按 README 生成相同清单；每条可追溯到 run/camera/shard；仓库不含原始视频
- **依赖/并行**：无前置；与 B-02、C-01/C-02 并行

### A-02 RTMDet-tiny 人员/叉车检测基线

- **优先级/阶段**：P0 / W1–W2
- **目标**：对 person/forklift 逐帧检测，跑通推理与评估；检测器不作为创新点
- **用什么实现**：MMDetection RTMDet-tiny；PyTorch/CUDA 固定版本；NMS、置信度阈值、原图坐标还原；mAP50/50-95、Precision/Recall；20 张可视化 + 失败案例
- **华为云关系**：**码道** 生成推理/评估代码与测试；**ModelArts** 在 A-08 封装为在线推理；**OBS** 存样例帧/可视化结果
- **交付物**：`ml/detector/config.*`、`infer_image.py`、`infer_video.py`、`evaluate.py`、`reports/detection_eval.md`、可视化样例
- **验收标准**：图片/短视频输出合法 JSON；框为像素坐标；无标注时明确写“仅推理验证”，不伪造 mAP
- **依赖/并行**：**S-01（B）必须先完成**；与 B-02、C-02/C-03 并行；A-08 依赖本 Issue

### A-03 ByteTrack 多目标跟踪适配

- **优先级/阶段**：P0 / W2
- **目标**：把逐帧检测关联成稳定 track，输出时序轨迹
- **用什么实现**：ByteTrack；Kalman 短时预测；`track_id/class/bbox/center/foot/conf/observed`；`timestamp_ms`；ID switch/碎片率统计
- **华为云关系**：**码道** 生成 adapter 与单测；无运行时云服务
- **交付物**：`ml/tracker/bytetrack_adapter.py`、`track_video.py`、`tests/unit/test_tracker_adapter.py`、`reports/tracking_eval.md`
- **验收标准**：短视频生成稳定 track_id；`observed=false` 与真实检测可区分；字段符合 S-01 schema
- **依赖/并行**：A-02；与 B-03、C-03 并行

### A-04 相机地面标定与像素→地面坐标

- **优先级/阶段**：P0 / W2
- **目标**：固定相机、平整地面、有标定点时输出米制坐标；否则输出归一化坐标
- **用什么实现**：OpenCV `findHomography`（≥4 组不共线点）；bbox 底边中心投影；留出点重投影误差；`coordinate_mode`
- **华为云关系**：**码道** 生成几何/单测代码；无运行时云服务
- **交付物**：`ml/geometry/homography.py`、`calibration_io.py`、`tests/unit/test_homography.py`、`docs/calibration-guide.md`、示例标定 JSON
- **验收标准**：已知点误差低于配置阈值；未标定不输出 `m` 或制动距离；标定状态可查询
- **依赖/并行**：A-03；与 B-02、C-03 并行；**B-04 依赖本 Issue 的坐标模式**

### A-05 CV/CA 轨迹预测基线

- **优先级/阶段**：P0 / W2
- **目标**：建立可比较的常速度/常加速度基线，供风险场先用
- **用什么实现**：NumPy；2.4s 观测 / 4.0s 预测、5Hz；按 track_id 独立预测；ADE/FDE/Miss Rate/物理违规率
- **华为云关系**：**码道** 生成纯函数与指标测试；无运行时云服务
- **交付物**：`ml/predictor/baselines.py`、`metrics.py`、`tests/unit/test_predictor_baselines.py`、`reports/trajectory_baseline.md`
- **验收标准**：至少 8 个历史点可预测；输出含坐标模式/版本；固定输入可复现
- **依赖/并行**：A-03；与 B-03、C-04 并行；**B-04、C-05、B-09 依赖本 Issue**

### A-06 Hetero-GRU 人机交互轨迹预测（P1，可砍）

- **优先级/阶段**：P1 / W3，仅在 P0 全部绿后启动
- **目标**：在 CV/CA 上做 person–forklift 交互的轻量多分支预测，形成自主算法点
- **用什么实现**：PyTorch GRU + pairwise MLP（不必上 GAT）；位置/速度/朝向/类别嵌入/观测掩码；K=3 分支 + score；速度/转向约束；按 seed 分组；与 CV/CA/纯 GRU 对比消融
- **华为云关系**：**ModelArts** 训练/推理（可选）；**OBS** checkpoint/日志；**码道** 生成模型/训练脚本与测试
- **交付物**：`ml/predictor/hetero_gru.py`、`dataset.py`、`train.py`、`evaluate.py`、配置、训练日志、`reports/hetero_prediction_ablation.md`
- **验收标准**：可训练/保存/加载/单场景推理；与基线同测试集比较；诚实报告失败案例
- **依赖/并行**：A-05 + **B-02（B）**；与 B-05/B-06 并行；**W2 结束 P0 未闭环就砍**

### A-07 预测不确定性输出（P1，可砍）

- **优先级/阶段**：P1 / W3
- **目标**：给每个预测分支输出可解释 score/不确定性，供 B 做风险推演
- **用什么实现**：mode score 归一化；可选 MC 采样/协方差；验证集可靠性检查；未校准标注 `score_semantics=uncalibrated_model_score`
- **华为云关系**：**码道** 生成 schema/示例；无运行时云服务
- **交付物**：`schemas/prediction.schema.json` 更新、`ml/predictor/uncertainty.py`、`docs/prediction-output-contract.md`、样例 JSON
- **验收标准**：B 不导入 A 训练代码即可读取；坐标/单位/版本/score 语义明确；不写“事故概率”
- **依赖/并行**：A-06；与 B-06 并行；**可砍**

### A-08 ModelArts 自定义推理服务封装（P0，云资格线）

- **优先级/阶段**：P0 / W2–W3
- **目标**：把检测模型封装成可被 ECS 调用的在线服务，完成华为云真实推理
- **用什么实现**：FastAPI + Docker；`POST /predict`（1–8 图/小批次）、`GET /health`、`GET /version`；模型权重从 OBS 挂载/下载；超时/错误码/批量策略；本地容器先验证
- **华为云关系**：**ModelArts** 在线推理；**OBS** 模型权重/样例；**ECS** 调用方；**码道** 生成服务/测试；**S-02（B）** 账号配额
- **交付物**：`services/inference/`、`Dockerfile`、`.env.example`、部署文档、健康检查/推理测试、ModelArts 截图/日志
- **验收标准**：本地容器可启动；一张图返回 person/forklift；ModelArts 服务可被 ECS 调用；如实记录是否云端部署
- **依赖/并行**：A-02 + **S-02（B）**；与 B-07/B-08 联调；**资格线，不能砍**

---

## 4. 每周验收（A 的 Definition of Done）

- **W1**：A-01 manifest 可复现；A-02 单图/短视频检测 JSON；S-03 许可清单；码道使用记录 ≥3 条
- **W2**：A-03 track_id 稳定；A-04 标定误差达标/明确降级；A-05 ADE/FDE 表；A-08 本地容器 `/predict` 通过
- **W3**：A-08 ModelArts 可被 ECS 调用；A-06/A-07 只有 P0 全绿才做；实验报告/失败案例
- **W4**：不再加功能，只修 P0 bug、补报告、配合演示

## 5. PR 自检

- [ ] 关联 Issue（`Closes #xx`）
- [ ] 运行命令、依赖版本、输入输出样例
- [ ] 指标注明数据集/划分/硬件/seed；没有的写“未验证”
- [ ] 没有原始大视频、模型大权重、密钥、个人信息
- [ ] 合成数据、仿真结果、实拍素材明确区分
- [ ] 码道使用记录已更新到 `docs/codearts-evidence.md`

## 6. GitHub Issue 模板

```markdown
## 目标
## 用什么实现
## 华为云关系（服务/用途/证据）
## 交付物
## 验收标准
## 依赖 / 并行
```
