"""从 SDG-Warehouse metadata 选择近失 run/clip，按 run/seed 分组切分并写出清单（A-01）。

设计要点：
- 只选 `hf_dir == forklift_human_nearmiss`；
- 优先 `n_cameras >= 10` 的多相机 run（默认 ceiling 相机 2 路/run）；
- 按 run/seed 分组切分，禁止同一 run 的不同视角跨 train/val/test；
- 输出两个 CSV：run 级清单 + clip 级清单；不下载视频。
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import pandas as pd

from ml.data.index_sdg import filter_near_miss, load_metadata

SPLIT_ORDER = {"train": 0, "val": 1, "test": 2}


def _stable_key(value: str, salt: str) -> str:
    return hashlib.sha1(f"{salt}:{value}".encode("utf-8")).hexdigest()


def choose_runs(
    runs: pd.DataFrame,
    max_runs: int = 16,
    min_cameras: int = 10,
    salt: str = "zhixun-a01",
) -> pd.DataFrame:
    """选多相机、seed 不重复的 run；用稳定 hash 排序保证可复现。"""
    if max_runs < 1:
        raise ValueError("max_runs 必须 >= 1")
    candidates = runs.loc[runs["n_cameras"] >= min_cameras].copy()
    if candidates.empty:
        raise ValueError(f"没有 n_cameras >= {min_cameras} 的近失 run")
    # 同一 seed 只保留一个 run，避免近重复场景跨 split
    candidates["_rank"] = candidates["run_id"].map(lambda x: _stable_key(str(x), salt))
    candidates = candidates.sort_values("_rank")
    candidates = candidates.drop_duplicates("seed", keep="first")
    selected = candidates.head(max_runs).copy()
    if len(selected) < max_runs:
        raise ValueError(f"只找到 {len(selected)} 个满足条件的 run，少于 max_runs={max_runs}")
    return selected.drop(columns=["_rank"]).reset_index(drop=True)


def choose_clips(
    clips: pd.DataFrame,
    run_ids: list[str],
    cameras_per_run: int = 2,
    prefer_prefix: str = "ceiling_",
) -> pd.DataFrame:
    """每个 run 选 N 路相机，优先 ceiling_*，不足时用其他相机补齐。"""
    if cameras_per_run < 1:
        raise ValueError("cameras_per_run 必须 >= 1")
    chunks: list[pd.DataFrame] = []
    for run_id in run_ids:
        group = clips.loc[clips["run_id"] == run_id].copy()
        if group.empty:
            raise ValueError(f"run {run_id} 没有 clip")
        group = group.dropna(subset=["camera_alias"])
        preferred = group.loc[group["camera_alias"].str.startswith(prefer_prefix)]
        preferred = preferred.sort_values("camera_alias")
        chosen = preferred.head(cameras_per_run)
        if len(chosen) < cameras_per_run:
            rest = group.loc[~group["clip_key"].isin(chosen["clip_key"])].sort_values("camera_alias")
            chosen = pd.concat([chosen, rest.head(cameras_per_run - len(chosen))], ignore_index=True)
        chunks.append(chosen)
    out = pd.concat(chunks, ignore_index=True)
    if out["clip_key"].duplicated().any():
        raise ValueError("选出的 clip_key 有重复")
    return out


def assign_split(
    run_ids: list[str],
    train_ratio: float = 0.625,
    val_ratio: float = 0.1875,
    salt: str = "zhixun-a01",
) -> dict[str, str]:
    """按 run_id 稳定 hash 排序后切分；同一 run 只进一个 split。"""
    if not run_ids:
        raise ValueError("run_ids 为空")
    if train_ratio <= 0 or val_ratio < 0 or train_ratio + val_ratio >= 1:
        raise ValueError("比例非法")
    ordered = sorted(run_ids, key=lambda x: _stable_key(str(x), salt + ":split"))
    n = len(ordered)
    n_train = max(1, int(round(n * train_ratio)))
    n_val = max(1, int(round(n * val_ratio))) if n >= 3 else 0
    n_train = min(n_train, n - n_val)
    n_test = n - n_train - n_val
    if n_test < 1:
        n_train = max(1, n_train - 1)
        n_test = n - n_train - n_val
    split: dict[str, str] = {}
    for i, run_id in enumerate(ordered):
        if i < n_train:
            split[run_id] = "train"
        elif i < n_train + n_val:
            split[run_id] = "val"
        else:
            split[run_id] = "test"
    return split


def build_manifest(
    runs: pd.DataFrame,
    clips: pd.DataFrame,
    max_runs: int = 16,
    cameras_per_run: int = 2,
    min_cameras: int = 10,
    salt: str = "zhixun-a01",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """生成 run 级与 clip 级清单，并做基本一致性校验。"""
    selected_runs = choose_runs(runs, max_runs=max_runs, min_cameras=min_cameras, salt=salt)
    run_ids = selected_runs["run_id"].astype(str).tolist()
    selected_clips = choose_clips(
        clips, run_ids, cameras_per_run=cameras_per_run, prefer_prefix="ceiling_"
    )
    split = assign_split(run_ids, salt=salt)

    runs_out = selected_runs.copy()
    runs_out["seed"] = runs_out["seed"].astype("int64")
    runs_out["split"] = runs_out["run_id"].map(split)
    runs_out = runs_out[
        ["split", "run_id", "seed", "scenario", "hf_dir", "n_cameras", "total_bytes",
         "shard_name", "shard_path_in_repo", "source_kind"]
    ].sort_values(["split", "run_id"], key=lambda s: s.map(SPLIT_ORDER) if s.name == "split" else s)

    clips_out = selected_clips.copy()
    clips_out["seed"] = clips_out["seed"].astype("int64")
    clips_out["size_bytes"] = clips_out["size"].astype("int64")
    clips_out["split"] = clips_out["run_id"].map(split)
    clips_out = clips_out[
        ["split", "run_id", "seed", "camera_alias", "clip_key", "hash_filename",
         "size_bytes", "shard_name", "shard_path_in_repo", "hf_dir", "source_kind"]
    ].sort_values(["split", "run_id", "camera_alias"], key=lambda s: s.map(SPLIT_ORDER) if s.name == "split" else s)

    # 一致性校验
    if set(runs_out["run_id"]) != set(clips_out["run_id"]):
        raise ValueError("run 清单与 clip 清单的 run_id 不一致")
    if runs_out["run_id"].duplicated().any():
        raise ValueError("run 清单有重复 run_id")
    if clips_out["clip_key"].duplicated().any():
        raise ValueError("clip 清单有重复 clip_key")
    if (runs_out.groupby("seed").size() > 1).any():
        raise ValueError("同一 seed 被分到多个 run")
    if runs_out.groupby("split").size().to_dict().get("test", 0) < 1:
        raise ValueError("没有 test split")
    return runs_out, clips_out


def main() -> None:
    parser = argparse.ArgumentParser(description="选择 SDG 近失 run/clip 并生成清单")
    parser.add_argument("--runs", required=True, help="runs.parquet 路径")
    parser.add_argument("--clips", required=True, help="clips.parquet 路径")
    parser.add_argument("--out-dir", default="data/manifests", help="输出目录")
    parser.add_argument("--max-runs", type=int, default=16)
    parser.add_argument("--cameras-per-run", type=int, default=2)
    parser.add_argument("--min-cameras", type=int, default=10)
    parser.add_argument("--salt", default="zhixun-a01")
    args = parser.parse_args()

    runs, clips = load_metadata(args.runs, args.clips)
    nm_runs, nm_clips = filter_near_miss(runs, clips)
    runs_out, clips_out = build_manifest(
        nm_runs, nm_clips,
        max_runs=args.max_runs,
        cameras_per_run=args.cameras_per_run,
        min_cameras=args.min_cameras,
        salt=args.salt,
    )

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    runs_path = out_dir / "sdg_selected_runs.csv"
    clips_path = out_dir / "sdg_selected_clips.csv"
    runs_out.to_csv(runs_path, index=False)
    clips_out.to_csv(clips_path, index=False)

    print(f"runs:  {len(runs_out)} -> {runs_path}")
    print(f"clips: {len(clips_out)} -> {clips_path}")
    print("split:", runs_out.groupby("split").size().to_dict())
    print("cameras:", clips_out["camera_alias"].value_counts().to_dict())


if __name__ == "__main__":
    main()
