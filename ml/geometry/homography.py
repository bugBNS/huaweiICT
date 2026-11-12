"""相机参数 → 地面单应矩阵（A-04）。

SDG 的 `camera_params.jsonl` 是 Isaac Sim/USD 格式：
- `cameraProjection` 4x4（OpenGL 投影）
- `cameraViewTransform` 4x4（world→camera，row-vector 约定）
- `renderProductResolution` [W, H]

已验证的投影约定（run_13 person 3D→2D 误差 0.6px）：
  p_cam = [x,y,z,1] @ V
  clip  = p_cam @ P
  u = (ndc_x*0.5+0.5)*W, v = (1-(ndc_y*0.5+0.5))*H

本模块只用地面 z=0 上的网格点求单应；不拿未来帧/真值轨迹调参。
"""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np


def load_camera_params(path: str | Path, frame_index: int = 0) -> tuple[np.ndarray, np.ndarray, int, int]:
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i == frame_index:
                data = json.loads(line)
                break
        else:
            raise IndexError(f"frame_index={frame_index} 超出范围")
    P = np.array(data["cameraProjection"], dtype=float).reshape(4, 4)
    V = np.array(data["cameraViewTransform"], dtype=float).reshape(4, 4)
    W, H = data.get("renderProductResolution", [1920, 1080])
    return P, V, int(W), int(H)


def project_world(P: np.ndarray, V: np.ndarray, points: np.ndarray, W: int, H: int) -> np.ndarray:
    """world (N,3) → pixel (N,2)；row-vector 约定。"""
    pts = np.asarray(points, dtype=float)
    if pts.ndim == 1:
        pts = pts[None, :]
    homo = np.c_[pts, np.ones(len(pts))]
    cam = homo @ V
    clip = cam @ P
    w = clip[:, 3:4]
    if np.any(np.abs(w) < 1e-9):
        raise ValueError("投影 w≈0，点可能落在相机平面")
    ndc = clip[:, :3] / w
    u = (ndc[:, 0] * 0.5 + 0.5) * W
    v = (1.0 - (ndc[:, 1] * 0.5 + 0.5)) * H
    return np.stack([u, v], axis=1)


def ground_homography(
    P: np.ndarray,
    V: np.ndarray,
    W: int,
    H: int,
    bound_m: float = 20.0,
    grid_n: int = 11,
    ransac_px: float = 3.0,
) -> tuple[np.ndarray | None, float, int, np.ndarray]:
    """用地面 z=0 的网格点求 pixel→ground 单应。

    返回 (H, rmse_px, inliers, used_ground_points)。H 为 None 表示标定失败。
    """
    xs = np.linspace(-bound_m, bound_m, grid_n)
    ys = np.linspace(-bound_m, bound_m, grid_n)
    grid = np.array([[x, y, 0.0] for y in ys for x in xs], dtype=float)
    img = project_world(P, V, grid, W, H)
    inside = (img[:, 0] >= 0) & (img[:, 0] < W) & (img[:, 1] >= 0) & (img[:, 1] < H)
    img_in = img[inside]
    ground_in = grid[inside, :2]
    if len(img_in) < 6:
        return None, float("inf"), 0, ground_in
    Hmat, mask = cv2.findHomography(img_in.reshape(-1, 1, 2), ground_in.reshape(-1, 1, 2),
                                    cv2.RANSAC, ransac_px)
    if Hmat is None:
        return None, float("inf"), 0, ground_in
    back = cv2.perspectiveTransform(img_in.reshape(-1, 1, 2), Hmat).reshape(-1, 2)
    err = np.linalg.norm(back - ground_in, axis=1)
    inliers = int(mask.sum()) if mask is not None else len(err)
    rmse = float(np.sqrt(np.mean(np.square(err))))
    return Hmat, rmse, inliers, ground_in


def pixel_to_ground(Hmat: np.ndarray, points: np.ndarray) -> np.ndarray:
    pts = np.asarray(points, dtype=np.float32).reshape(-1, 1, 2)
    out = cv2.perspectiveTransform(pts, Hmat.astype(np.float64))
    return out.reshape(-1, 2)
