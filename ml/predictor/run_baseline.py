"""在 GROUND_METRIC 轨迹上跑 CV/CA 基线，输出指标与示例 PredictionBundle（A-05）。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from ml.predictor.baselines import build_bundle, resample, to_series
from ml.predictor.metrics import ade, fde, miss_rate, physical_violation
from schemas.models import TrackSequence


def main() -> None:
    parser = argparse.ArgumentParser(description="CV/CA 轨迹预测基线")
    parser.add_argument("--tracks", required=True, help="GROUND_METRIC TrackSequence JSON")
    parser.add_argument("--out-metrics", default="reports/trajectory_baseline.json")
    parser.add_argument("--out-bundle", default="reports/predictions_run13_cv.json")
    parser.add_argument("--dt-ms", type=int, default=200)
    parser.add_argument("--history-steps", type=int, default=12)
    parser.add_argument("--horizon-steps", type=int, default=20)
    parser.add_argument("--anchor-step", type=int, default=5)
    parser.add_argument("--min-observed-ratio", type=float, default=0.3)
    args = parser.parse_args()

    seq = TrackSequence.model_validate(json.loads(Path(args.tracks).read_text(encoding="utf-8")))
    series = []
    skipped_tracks = 0
    for tr in seq.tracks:
        s = to_series(tr, min_observed_ratio=args.min_observed_ratio)
        if s is None:
            skipped_tracks += 1
            continue
        s = resample(s, args.dt_ms)
        if len(s.t_ms) >= args.history_steps + args.horizon_steps + 1:
            series.append(s)

    results: dict[str, dict] = {}
    for method in ("cv", "ca"):
        per_class: dict[str, list[tuple[float, float, float]]] = {}
        n_eval = 0
        n_skip = 0
        saved = False
        for s in series:
            last_anchor = len(s.t_ms) - args.horizon_steps - 1
            for anchor in range(args.history_steps - 1, last_anchor + 1, args.anchor_step):
                try:
                    bundle = build_bundle(
                        s, anchor, method=method, history_steps=args.history_steps,
                        horizon_steps=args.horizon_steps, dt_ms=args.dt_ms,
                        model_version=f"{method}-baseline-0.1",
                        run_id=seq.run_id, scenario_id=seq.scenario_id or "near_miss",
                    )
                except ValueError:
                    n_skip += 1
                    continue
                pred = np.array([[p.x, p.y] for p in bundle.agents[0].branches[0].samples])
                gt = np.stack([s.x[anchor + 1:anchor + 1 + args.horizon_steps],
                               s.y[anchor + 1:anchor + 1 + args.horizon_steps]], axis=1)
                if len(gt) != len(pred):
                    n_skip += 1
                    continue
                per_class.setdefault(s.class_name, []).append(
                    (ade(pred, gt), fde(pred, gt), physical_violation(pred, args.dt_ms / 1000)))
                n_eval += 1
                if not saved:
                    base = Path(args.out_bundle)
                    bundle_path = base.with_name(f"{base.stem}_{method}{base.suffix}")
                    bundle_path.parent.mkdir(parents=True, exist_ok=True)
                    bundle_path.write_text(
                        json.dumps(bundle.model_dump(by_alias=True, mode="json"),
                                   ensure_ascii=False, indent=2), encoding="utf-8")
                    saved = True
        summary = {
            "n_evaluated": n_eval,
            "n_skipped": n_skip,
            "miss_rate": round(miss_rate(n_eval, n_skip), 4),
            "by_class": {},
        }
        for cls, vals in per_class.items():
            arr = np.array(vals)
            summary["by_class"][cls] = {
                "n": len(vals),
                "ade_m": round(float(arr[:, 0].mean()), 4),
                "fde_m": round(float(arr[:, 1].mean()), 4),
                "physical_violation_rate": round(float(arr[:, 2].mean()), 4),
            }
        results[method] = summary

    out = {
        "run_id": seq.run_id,
        "coordinate_mode": seq.coordinate_mode,
        "n_tracks_used": len(series),
        "n_tracks_skipped": skipped_tracks,
        "history_steps": args.history_steps,
        "horizon_steps": args.horizon_steps,
        "dt_ms": args.dt_ms,
        "methods": results,
        "note": "Single-run smoke; same-run camera split, not a generalization benchmark.",
    }
    Path(args.out_metrics).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_metrics).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
