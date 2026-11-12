from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from ml.data.index_sdg import filter_near_miss, load_metadata, summarize
from ml.data.select_runs import assign_split, build_manifest, choose_clips, choose_runs


def _make_metadata(tmp_path: Path) -> tuple[Path, Path]:
    runs = []
    clips = []
    # 4 个多相机近失 run + 1 个单相机近失 run + 1 个 fire run
    for i in range(6):
        is_near = i < 5
        hf_dir = "forklift_human_nearmiss" if is_near else "warehouse_fire"
        scenario = "nearmiss" if is_near else "fire"
        n_cameras = 10 if i != 4 else 1
        run_id = f"run_{i}"
        runs.append({
            "run_id": run_id, "scenario": scenario, "hf_dir": hf_dir,
            "source_kind": "multi_camera_run", "seed": 100 + i,
            "n_cameras": n_cameras, "total_bytes": 1000 * n_cameras,
            "shard_name": "shard.tar", "shard_path_in_repo": f"rgb/{hf_dir}/shard.tar",
        })
        if n_cameras == 10:
            cameras = [f"ceiling_{j:02d}" for j in range(3)] + [f"eye_{j:02d}" for j in range(7)]
        else:
            cameras = ["cam_00"]
        for cam in cameras:
            clips.append({
                "clip_key": f"{run_id}.{cam}", "run_id": run_id, "scenario": scenario,
                "hf_dir": hf_dir, "source_kind": "multi_camera_run", "seed": 100 + i,
                "camera_alias": cam, "hash_filename": f"{cam}_rgb.mp4", "size": 1024,
                "shard_name": "shard.tar", "shard_path_in_repo": f"rgb/{hf_dir}/shard.tar",
            })
    runs_path = tmp_path / "runs.parquet"
    clips_path = tmp_path / "clips.parquet"
    pd.DataFrame(runs).to_parquet(runs_path, index=False)
    pd.DataFrame(clips).to_parquet(clips_path, index=False)
    return runs_path, clips_path


def test_load_and_filter(tmp_path: Path) -> None:
    runs_path, clips_path = _make_metadata(tmp_path)
    runs, clips = load_metadata(runs_path, clips_path)
    nm_runs, nm_clips = filter_near_miss(runs, clips)
    assert len(nm_runs) == 5
    assert len(nm_clips) == 41  # 4 个 10 相机 run + 1 个单相机 run
    assert set(nm_runs["hf_dir"]) == {"forklift_human_nearmiss"}
    summary = summarize(nm_runs, nm_clips)
    assert summary["near_miss_runs"] == 5
    assert summary["multi_camera_runs"] == 4


def test_choose_runs_prefers_multi_camera_and_unique_seed(tmp_path: Path) -> None:
    runs_path, clips_path = _make_metadata(tmp_path)
    runs, clips = load_metadata(runs_path, clips_path)
    nm_runs, _ = filter_near_miss(runs, clips)
    selected = choose_runs(nm_runs, max_runs=3, min_cameras=10)
    assert len(selected) == 3
    assert (selected["n_cameras"] >= 10).all()
    assert selected["seed"].is_unique
    assert "run_4" not in set(selected["run_id"])


def test_choose_clips_takes_ceiling_cameras(tmp_path: Path) -> None:
    runs_path, clips_path = _make_metadata(tmp_path)
    runs, clips = load_metadata(runs_path, clips_path)
    nm_runs, nm_clips = filter_near_miss(runs, clips)
    selected = choose_runs(nm_runs, max_runs=2, min_cameras=10)
    chosen = choose_clips(nm_clips, selected["run_id"].tolist(), cameras_per_run=2)
    assert len(chosen) == 4
    assert chosen["camera_alias"].str.startswith("ceiling_").all()
    assert chosen["clip_key"].is_unique


def test_assign_split_is_disjoint_and_complete() -> None:
    run_ids = [f"run_{i}" for i in range(16)]
    split = assign_split(run_ids)
    assert set(split) == set(run_ids)
    values = list(split.values())
    assert values.count("train") == 10
    assert values.count("val") == 3
    assert values.count("test") == 3


def test_build_manifest_consistency(tmp_path: Path) -> None:
    runs_path, clips_path = _make_metadata(tmp_path)
    runs, clips = load_metadata(runs_path, clips_path)
    nm_runs, nm_clips = filter_near_miss(runs, clips)
    runs_out, clips_out = build_manifest(nm_runs, nm_clips, max_runs=3, cameras_per_run=2)
    assert len(runs_out) == 3
    assert len(clips_out) == 6
    assert runs_out["run_id"].is_unique
    assert clips_out["clip_key"].is_unique
    assert set(runs_out["split"]) == {"train", "val", "test"}
    assert set(clips_out["run_id"]) == set(runs_out["run_id"])
    assert (clips_out["camera_alias"].str.startswith("ceiling_")).all()


def test_missing_column_raises(tmp_path: Path) -> None:
    runs_path, clips_path = _make_metadata(tmp_path)
    bad = pd.read_parquet(runs_path).drop(columns=["seed"])
    bad_path = tmp_path / "bad_runs.parquet"
    bad.to_parquet(bad_path, index=False)
    with pytest.raises(ValueError, match="runs.parquet"):
        load_metadata(bad_path, clips_path)
