"""SDG-Warehouse metadata 读取、近失场景筛选与摘要（A-01）。

只读 metadata（runs.parquet / clips.parquet），不下载 549 GiB RGB 全量。
真实字段来自 NVIDIA PhysicalAI SDG-Warehouse：
  runs:  run_id, scenario, hf_dir, source_kind, seed, n_cameras, total_bytes,
         source_run_s3, shard_name, shard_path_in_repo, clip_keys
  clips: clip_key, run_id, scenario, hf_dir, source_kind, seed, camera_alias,
         camera_source, source_rgb_s3, hash_filename, size, shard_name,
         shard_path_in_repo

近失场景用 `hf_dir == "forklift_human_nearmiss"` 识别（`scenario` 为 `nearmiss`）。
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

NEAR_MISS_DIR = "forklift_human_nearmiss"

RUN_COLUMNS = {
    "run_id",
    "scenario",
    "hf_dir",
    "source_kind",
    "seed",
    "n_cameras",
    "total_bytes",
    "shard_name",
    "shard_path_in_repo",
}
CLIP_COLUMNS = {
    "clip_key",
    "run_id",
    "scenario",
    "hf_dir",
    "source_kind",
    "seed",
    "camera_alias",
    "hash_filename",
    "size",
    "shard_name",
    "shard_path_in_repo",
}


def _require_columns(df: pd.DataFrame, required: set[str], name: str) -> None:
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"{name} 缺少字段: {missing}")


def load_metadata(runs_path: str | Path, clips_path: str | Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """读取 runs/clips metadata，并校验必需字段。"""
    runs = pd.read_parquet(runs_path)
    clips = pd.read_parquet(clips_path)
    _require_columns(runs, RUN_COLUMNS, "runs.parquet")
    _require_columns(clips, CLIP_COLUMNS, "clips.parquet")
    return runs, clips


def filter_near_miss(
    runs: pd.DataFrame, clips: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """只保留叉车-行人近失场景；不修改入参。"""
    r = runs.loc[runs["hf_dir"] == NEAR_MISS_DIR].copy()
    c = clips.loc[clips["hf_dir"] == NEAR_MISS_DIR].copy()
    if r.empty or c.empty:
        raise ValueError(f"没有找到 hf_dir={NEAR_MISS_DIR} 的 run/clip")
    return r, c


def summarize(runs: pd.DataFrame, clips: pd.DataFrame) -> dict:
    """生成数据集摘要，供文档/日志使用。"""
    per_run = clips.groupby("run_id").size()
    return {
        "near_miss_runs": int(len(runs)),
        "near_miss_clips": int(len(clips)),
        "unique_seeds": int(runs["seed"].nunique()),
        "multi_camera_runs": int((runs["n_cameras"] >= 10).sum()),
        "total_bytes_gb": round(float(runs["total_bytes"].sum()) / 1e9, 2),
        "clips_per_run_min": int(per_run.min()) if len(per_run) else 0,
        "clips_per_run_median": float(per_run.median()) if len(per_run) else 0,
        "clips_per_run_max": int(per_run.max()) if len(per_run) else 0,
        "camera_aliases": clips["camera_alias"].value_counts().head(12).to_dict(),
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="读取 SDG metadata 并输出近失场景摘要")
    parser.add_argument("--runs", required=True, help="runs.parquet 路径")
    parser.add_argument("--clips", required=True, help="clips.parquet 路径")
    parser.add_argument("--json-out", default=None, help="可选：摘要写入 JSON")
    args = parser.parse_args()

    runs, clips = load_metadata(args.runs, args.clips)
    nm_runs, nm_clips = filter_near_miss(runs, clips)
    summary = summarize(nm_runs, nm_clips)
    text = json.dumps(summary, ensure_ascii=False, indent=2)
    print(text)
    if args.json_out:
        Path(args.json_out).write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
