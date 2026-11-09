from __future__ import annotations

import numpy as np

from ml.geometry.homography import pixel_to_ground


def test_pixel_to_ground_roundtrip_identity() -> None:
    H = np.eye(3)
    pts = np.array([[100.0, 200.0], [300.0, 400.0]])
    out = pixel_to_ground(H, pts)
    assert np.allclose(out, pts)


def test_pixel_to_ground_affine() -> None:
    # ground = (u-100)/10, (v-50)/10
    H = np.array([[0.1, 0.0, -10.0], [0.0, 0.1, -5.0], [0.0, 0.0, 1.0]])
    out = pixel_to_ground(H, [[100.0, 50.0], [200.0, 150.0]])
    assert np.allclose(out, [[0.0, 0.0], [10.0, 10.0]])
