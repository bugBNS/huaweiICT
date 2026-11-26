# A-01 SDG 数据索引与样本选择

只读 SDG-Warehouse 的 `metadata/runs.parquet` 与 `metadata/clips.parquet`，筛选近失场景并输出清单；**不下载 549 GiB RGB 全量**。

## 文件

| 文件 | 作用 |
|---|---|
| `index_sdg.py` | 读取 metadata、校验字段、过滤 `forklift_human_nearmiss`、输出摘要 |
| `select_runs.py` | 选多相机/唯一 seed 的 run，按 run 稳定切分，写 run/clip 清单 |

## 用法

```bash
# 1) 摘要（可选）
python -m ml.data.index_sdg \
  --runs .tmp_sdg/metadata_runs.parquet \
  --clips .tmp_sdg/metadata_clips.parquet

# 2) 生成清单
python -m ml.data.select_runs \
  --runs .tmp_sdg/metadata_runs.parquet \
  --clips .tmp_sdg/metadata_clips.parquet \
  --out-dir data/manifests \
  --max-runs 16 --cameras-per-run 2
```

- metadata 从数据集主页的 `metadata/` 目录获取；`.tmp_sdg/` 已在 `.gitignore` 中，不入库。
- 输出：`data/manifests/sdg_selected_runs.csv`、`sdg_selected_clips.csv`。
- 默认 16 run × 2 ceiling 相机 = 32 clip；train/val/test 按 run 切分，同一 run 不跨 split。

## 测试

```bash
python -m pytest tests/unit/test_sdg_selection.py -q
```

测试用合成 parquet，不依赖网络或真实数据。

## 边界

- `scenario=nearmiss`、`hf_dir=forklift_human_nearmiss` 才是近失场景；
- 单相机 `cam_00` run 默认不选；
- 合成数据，非真实工厂；报告里必须标注。
