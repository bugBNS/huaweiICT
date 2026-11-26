# SDG 近失样本清单

由 `python -m ml.data.select_runs` 生成，**不要手改**。

| 文件 | 行数 | 说明 |
|---|---:|---|
| `sdg_selected_runs.csv` | 16 | 1 行/run；split、seed、n_cameras、shard 路径 |
| `sdg_selected_clips.csv` | 32 | 1 行/clip；camera_alias、clip_key、hash_filename、size |

当前选择（salt=`zhixun-a01`）：

- 16 个 `forklift_human_nearmiss` 多相机 run，seed 不重复；
- 每个 run 取 `ceiling_00`、`ceiling_01` 两路；
- train/val/test = 10/3/3 个 run（20/6/6 个 clip）；
- 只含清单，不含视频；下载时只拉清单对应的 `shard_path_in_repo`。

重新生成：

```bash
python -m ml.data.select_runs \
  --runs .tmp_sdg/metadata_runs.parquet \
  --clips .tmp_sdg/metadata_clips.parquet \
  --out-dir data/manifests --max-runs 16 --cameras-per-run 2
```

许可与合成数据限制见 `docs/dataset-and-license.md`。
