"""CV/CA 轨迹预测基线（A-05）。

输入是 S-01 GROUND_METRIC TrackSequence；先按 200ms 重采样，再用最后 2/3 个
历史点估计速度/加速度。只用 observed=true 的点插值，不把补点当观测。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from schemas.models import (
    AgentPrediction,
    PredictionBranch,
    PredictionBundle,
    TrajectorySample,
    Track,
)


@dataclass
class TrackSeries:
    track_id: str
    class_name: str
    t_ms: np.ndarray
    x: np.ndarray
    y: np.ndarray
    observed: np.ndarray


def to_series(track: Track, min_observed_ratio: float = 0.3) -> TrackSeries | None:
    pts = [p for p in track.points if p.observed]
    if len(pts) < 6:
        return None
    if len(pts) / max(len(track.points), 1) < min_observed_ratio:
        return None
    t = np.array([p.timestamp_ms for p in pts], dtype=float)
    x = np.array([p.x for p in pts], dtype=float)
    y = np.array([p.y for p in pts], dtype=float)
    return TrackSeries(track.track_id, track.class_name, t, x, y, np.ones(len(pts), dtype=bool))


def resample(series: TrackSeries, dt_ms: int = 200) -> TrackSeries:
    t0, t1 = float(series.t_ms[0]), float(series.t_ms[-1])
    grid = np.arange(t0, t1 + 1e-6, dt_ms)
    # 去重时间戳，np.interp 要求递增
    t_unique, idx = np.unique(series.t_ms, return_index=True)
    x = np.interp(grid, t_unique, series.x[idx])
    y = np.interp(grid, t_unique, series.y[idx])
    return TrackSeries(series.track_id, series.class_name, grid, x, y,
                       np.ones(len(grid), dtype=bool))


def cv_predict(t: np.ndarray, x: np.ndarray, y: np.ndarray,
               anchor_idx: int, horizon_steps: int, dt_ms: int) -> np.ndarray:
    i = anchor_idx
    if i < 1:
        raise ValueError("CV 需要至少 2 个历史点")
    vx = (x[i] - x[i - 1]) / max(t[i] - t[i - 1], 1e-9)
    vy = (y[i] - y[i - 1]) / max(t[i] - t[i - 1], 1e-9)
    ts = t[i] + dt_ms * np.arange(1, horizon_steps + 1)
    return np.stack([x[i] + vx * (ts - t[i]), y[i] + vy * (ts - t[i])], axis=1)


def ca_predict(t: np.ndarray, x: np.ndarray, y: np.ndarray,
               anchor_idx: int, horizon_steps: int, dt_ms: int) -> np.ndarray:
    i = anchor_idx
    if i < 2:
        raise ValueError("CA 需要至少 3 个历史点")
    dt1 = max(t[i] - t[i - 1], 1e-9)
    dt2 = max(t[i - 1] - t[i - 2], 1e-9)
    vx = (x[i] - x[i - 1]) / dt1
    vy = (y[i] - y[i - 1]) / dt1
    vx_prev = (x[i - 1] - x[i - 2]) / dt2
    vy_prev = (y[i - 1] - y[i - 2]) / dt2
    ax = (vx - vx_prev) / max((dt1 + dt2) / 2, 1e-9)
    ay = (vy - vy_prev) / max((dt1 + dt2) / 2, 1e-9)
    ts = t[i] + dt_ms * np.arange(1, horizon_steps + 1)
    d = ts - t[i]
    return np.stack([x[i] + vx * d + 0.5 * ax * d * d,
                     y[i] + vy * d + 0.5 * ay * d * d], axis=1)


def _sample(ts: np.ndarray, xy: np.ndarray, vx: float, vy: float) -> list[TrajectorySample]:
    speed = float(np.hypot(vx, vy))
    heading = float(np.arctan2(vy, vx))
    return [
        TrajectorySample(timestamp_ms=int(round(t)), x=float(p[0]), y=float(p[1]),
                         position_unit="m", speed_mps=speed, heading_rad=heading)
        for t, p in zip(ts, xy)
    ]


def build_bundle(series: TrackSeries, anchor_idx: int, method: str = "cv",
                 history_steps: int = 12, horizon_steps: int = 20,
                 dt_ms: int = 200, model_version: str | None = None,
                 run_id: str = "run_x", scenario_id: str = "near_miss") -> PredictionBundle:
    if anchor_idx < history_steps - 1:
        raise ValueError("anchor 之前历史不足")
    start = anchor_idx - history_steps + 1
    hist_t = series.t_ms[start:anchor_idx + 1]
    hist_xy = np.stack([series.x[start:anchor_idx + 1], series.y[start:anchor_idx + 1]], axis=1)
    if method == "cv":
        pred = cv_predict(series.t_ms, series.x, series.y, anchor_idx, horizon_steps, dt_ms)
    elif method == "ca":
        pred = ca_predict(series.t_ms, series.x, series.y, anchor_idx, horizon_steps, dt_ms)
    else:
        raise ValueError(method)
    pred_t = series.t_ms[anchor_idx] + dt_ms * np.arange(1, horizon_steps + 1)
    # 历史速度/航向用相邻点估计
    vx = (hist_xy[-1, 0] - hist_xy[-2, 0]) / max(hist_t[-1] - hist_t[-2], 1e-9)
    vy = (hist_xy[-1, 1] - hist_xy[-2, 1]) / max(hist_t[-1] - hist_t[-2], 1e-9)
    history = _sample(hist_t, hist_xy, vx, vy)
    branch = PredictionBranch(
        branch_id=0, score=1.0, score_semantics="uncalibrated_model_score",
        samples=_sample(pred_t, pred, vx, vy),
    )
    agent = AgentPrediction(**{"class": series.class_name}, track_id=series.track_id,
                            history=history, branches=[branch])
    return PredictionBundle(
        run_id=run_id, scenario_id=scenario_id,
        model_version=model_version or f"{method}-baseline",
        risk_rule_version=None, coordinate_mode="GROUND_METRIC",
        timestamp_ms=int(series.t_ms[anchor_idx]), dt_ms=dt_ms, agents=[agent],
    )
