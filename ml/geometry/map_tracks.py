"""把 IMAGE_NORMALIZED 轨迹的 foot 点映射到 GROUND_METRIC（A-04）。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ml.geometry.homography import pixel_to_ground
from schemas.models import BBoxXYXY, Track, TrackPoint, TrackSequence


def main() -> None:
    parser = argparse.ArgumentParser(description="轨迹 foot → 地面米制坐标")
    parser.add_argument("--tracks", required=True, help="S-01 TrackSequence JSON")
    parser.add_argument("--calibration", required=True, help="calibrate_run.py 输出 JSON")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    seq = TrackSequence.model_validate(json.loads(Path(args.tracks).read_text(encoding="utf-8")))
    cal = json.loads(Path(args.calibration).read_text(encoding="utf-8"))
    if cal["coordinate_mode"] != "GROUND_METRIC" or not cal.get("homography_pixel_to_ground"):
        raise ValueError("标定未通过，不能输出米制轨迹")
    import numpy as np
    H = np.array(cal["homography_pixel_to_ground"], dtype=float)

    tracks: list[Track] = []
    for tr in seq.tracks:
        points: list[TrackPoint] = []
        for p in tr.points:
            if p.foot is None:
                continue
            gx, gy = pixel_to_ground(H, [p.foot])[0]
            points.append(TrackPoint(
                timestamp_ms=p.timestamp_ms,
                x=float(gx),
                y=float(gy),
                position_unit="m",
                speed_mps=None,
                heading_rad=None,
                bbox=p.bbox,
                center=p.center,
                foot=p.foot,
                conf=p.conf,
                observed=p.observed,
            ))
        if points:
            tracks.append(Track(**{"class": tr.class_name}, track_id=tr.track_id, points=points))

    out = TrackSequence(
        run_id=seq.run_id,
        scenario_id=seq.scenario_id,
        model_version=f"{seq.model_version}+ground",
        risk_rule_version=None,
        coordinate_mode="GROUND_METRIC",
        timestamp_ms=seq.timestamp_ms,
        tracks=tracks,
    )
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(
        json.dumps(out.model_dump(by_alias=True, mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"tracks={len(tracks)} -> {args.out}")


if __name__ == "__main__":
    main()
