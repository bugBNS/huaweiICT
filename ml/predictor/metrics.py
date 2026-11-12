"""轨迹预测指标（A-05）。"""

from __future__ import annotations

import numpy as np


def ade(pred: np.ndarray, gt: np.ndarray) -> float:
    return float(np.mean(np.linalg.norm(pred - gt, axis=1)))


def fde(pred: np.ndarray, gt: np.ndarray) -> float:
    return float(np.linalg.norm(pred[-1] - gt[-1]))


def physical_violation(pred: np.ndarray, dt_s: float = 0.2, max_speed_mps: float = 3.0) -> float:
    if len(pred) < 2:
        return 0.0
    speeds = np.linalg.norm(np.diff(pred, axis=0), axis=1) / dt_s
    return float((speeds > max_speed_mps).mean())


def miss_rate(n_evaluated: int, n_skipped: int) -> float:
    total = n_evaluated + n_skipped
    return float(n_skipped / total) if total else 0.0
