# 数据集与许可（S-03 / A-01）

## 1. 数据集

| 项 | 内容 |
|---|---|
| 名称 | NVIDIA PhysicalAI-WorldModel-Synthetic-Warehouse-Operations-Scenes |
| 主页 | <https://huggingface.co/datasets/nvidia/PhysicalAI-WorldModel-Synthetic-Warehouse-Operations-Scenes> |
| 生成方式 | Isaac Sim / Replicator 合成，不是真实工厂拍摄 |
| 总规模 | 29,195 runs / 122,967 clips（metadata 实测） |
| 近失子集 | `scenario=nearmiss`、`hf_dir=forklift_human_nearmiss`：13,410 runs / 27,939 clips |
| 近失 RGB 体积 | 约 549 GiB（数据集卡口径）；本仓库**不下载全量** |
| 相机 | 近失子集中 1,566 个 run 为 10 相机（`ceiling_00..04`、`eye_00..04`），其余多为单相机 `cam_00` |
| 许可 | **OpenMDW-1.1**（当前数据集卡）；早期 revision 曾标 CC BY 4.0，使用前以当前卡为准 |

> 合成数据的边界：行为、近失距离、相机参数都是仿真生成；不能把实验结果写成“真实工厂事故率下降”。域差异需在报告中明确。

## 2. 选择策略（A-01）

- 只选 `hf_dir == forklift_human_nearmiss`；
- 只选 `n_cameras >= 10` 的多相机 run，优先 `ceiling_*` 俯视相机；
- 同一 `seed` 只保留一个 run，避免近重复场景跨 split；
- 按 `run_id` 稳定 hash 排序后切分，**同一 run 的所有相机只进一个 split**；
- 默认 16 个 run × 2 路 ceiling 相机 = 32 个 clip；train/val/test = 10/3/3 个 run（20/6/6 个 clip）。

生成命令：

```bash
python -m ml.data.select_runs \
  --runs .tmp_sdg/metadata_runs.parquet \
  --clips .tmp_sdg/metadata_clips.parquet \
  --out-dir data/manifests \
  --max-runs 16 --cameras-per-run 2
```

## 3. 清单文件

| 文件 | 粒度 | 关键字段 |
|---|---|---|
| `data/manifests/sdg_selected_runs.csv` | 1 行/run | `split, run_id, seed, scenario, hf_dir, n_cameras, total_bytes, shard_path_in_repo` |
| `data/manifests/sdg_selected_clips.csv` | 1 行/clip | `split, run_id, seed, camera_alias, clip_key, hash_filename, size_bytes, shard_path_in_repo` |

- `shard_path_in_repo` 是下载 tar 分片的相对路径；`hash_filename` 是 tar 内的视频文件名；
- 本仓库只提交清单（CSV），不提交视频、tar 分片或全量 metadata parquet；
- 下载时只拉清单涉及的 shard，放到 `data/raw/` 或 OBS，`.gitignore` 已忽略 `data/raw/`。

## 4. 许可与再分发

- 使用/分发数据集时保留 OpenMDW-1.1 协议与来源说明；不要改写成 CC BY 4.0。
- 代码仓库的 MIT LICENSE 只覆盖本项目代码，不覆盖数据集。
- 对外演示/开源时，引用数据集主页与 NVIDIA 的 dataset card。
- 若后续使用 RTMDet/ByteTrack 等第三方代码，见根目录 `THIRD_PARTY_NOTICES.md`。

## 5. 已知限制

- 合成数据的行为模式比真实仓库简单，不能替代现场数据；
- 近失标签来自仿真参数（last-moment dodge distance），不是人工事故判定；
- 单相机 `cam_00` 的 run 没有 ceiling 视角，默认不选，避免视角分布不一致；
- `seed` 是仿真种子，不是随机划分种子；本仓库的 split salt 固定为 `zhixun-a01`，可复现。
