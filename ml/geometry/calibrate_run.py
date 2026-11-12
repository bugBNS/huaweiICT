"""用真实 camera_params 生成地面单应 JSON（A-04）。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ml.geometry.homography import ground_homography, load_camera_params

MAX_RMSE_PX = 5.0


def main() -> None:
    parser = argparse.ArgumentParser(description="camera_params → 地面单应")
    parser.add_argument("--camera-params", required=True)
    parser.add_argument("--frame-index", type=int, default=0)
    parser.add_argument("--bound-m", type=float, default=20.0)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    P, V, W, H = load_camera_params(args.camera_params, args.frame_index)
    Hmat, rmse, inliers, _ = ground_homography(P, V, W, H, bound_m=args.bound_m)
    ok = Hmat is not None and rmse <= MAX_RMSE_PX and inliers >= 6
    result = {
        "coordinate_mode": "GROUND_METRIC" if ok else "IMAGE_NORMALIZED",
        "image_size": [W, H],
        "camera_params": str(args.camera_params),
        "frame_index": args.frame_index,
        "homography_pixel_to_ground": Hmat.tolist() if Hmat is not None else None,
        "reprojection_rmse_px": None if Hmat is None else round(rmse, 3),
        "inliers": inliers,
        "threshold_rmse_px": MAX_RMSE_PX,
        "note": "H maps pixel (u,v) to ground (x,y) metres at z=0; failure falls back to IMAGE_NORMALIZED",
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("coordinate_mode", "reprojection_rmse_px", "inliers")},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
