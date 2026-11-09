from __future__ import annotations

import numpy as np

from ml.predictor.baselines import TrackSeries, build_bundle, ca_predict, cv_predict
from ml.predictor.metrics import ade, fde, physical_violation


def test_cv_constant_velocity() -> None:
    t = np.array([0.0, 200.0])
    x = np.array([0.0, 1.0])
    y = np.array([0.0, 0.0])
    pred = cv_predict(t, x, y, anchor_idx=1, horizon_steps=2, dt_ms=200)
    assert np.allclose(pred, [[2.0, 0.0], [3.0, 0.0]])


def test_ca_constant_acceleration() -> None:
    t = np.array([0.0, 200.0, 400.0])
    x = np.array([0.0, 1.0, 2.5])
    y = np.array([0.0, 0.0, 0.0])
    pred = ca_predict(t, x, y, anchor_idx=2, horizon_steps=2, dt_ms=200)
    assert np.allclose(pred, [[4.25, 0.0], [6.5, 0.0]])


def test_ade_fde() -> None:
    pred = np.array([[1.0, 0.0], [2.0, 0.0]])
    gt = np.array([[0.0, 0.0], [0.0, 0.0]])
    assert ade(pred, gt) == 1.5
    assert fde(pred, gt) == 2.0


def test_physical_violation() -> None:
    pred = np.array([[0.0, 0.0], [1.0, 0.0]])  # 5 m/s in 0.2s
    assert physical_violation(pred, dt_s=0.2, max_speed_mps=3.0) == 1.0


def test_build_bundle_schema() -> None:
    n = 40
    t = np.arange(n, dtype=float) * 200
    x = np.arange(n, dtype=float) * 0.1
    y = np.zeros(n)
    series = TrackSeries("p1", "person", t, x, y, np.ones(n, dtype=bool))
    bundle = build_bundle(series, anchor_idx=12, method="cv", history_steps=12,
                          horizon_steps=20, dt_ms=200, run_id="run_x", scenario_id="sc_x")
    assert bundle.coordinate_mode.value == "GROUND_METRIC"
    assert len(bundle.agents[0].history) == 12
    assert len(bundle.agents[0].branches[0].samples) == 20
