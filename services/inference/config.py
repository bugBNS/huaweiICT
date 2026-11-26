"""A-08 inference service settings.

All values are read from environment variables so the same image can run
locally, on ECS, and on ModelArts without code changes.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

SERVICE_VERSION = "0.1.0"
DEFAULT_MODEL_PATH = "yolo11n.pt"


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    return int(raw) if raw not in (None, "") else default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    return float(raw) if raw not in (None, "") else default


@dataclass(frozen=True)
class Settings:
    model_path: str = DEFAULT_MODEL_PATH
    model_version: str | None = None
    device: str = "cpu"
    conf: float = 0.25
    iou: float = 0.5
    imgsz: int = 640
    max_batch_size: int = 8
    max_image_mb: float = 10.0
    max_image_pixels: int = 20_000_000

    @classmethod
    def from_env(cls) -> "Settings":
        model_version = os.getenv("MODEL_VERSION") or None
        return cls(
            model_path=os.getenv("MODEL_PATH", DEFAULT_MODEL_PATH),
            model_version=model_version,
            device=os.getenv("INFERENCE_DEVICE", "cpu"),
            conf=_env_float("INFERENCE_CONF", 0.25),
            iou=_env_float("INFERENCE_IOU", 0.5),
            imgsz=_env_int("INFERENCE_IMGSZ", 640),
            max_batch_size=_env_int("INFERENCE_MAX_BATCH", 8),
            max_image_mb=_env_float("INFERENCE_MAX_IMAGE_MB", 10.0),
            max_image_pixels=_env_int("INFERENCE_MAX_IMAGE_PIXELS", 20_000_000),
        )

    @property
    def max_image_bytes(self) -> int:
        return int(self.max_image_mb * 1024 * 1024)

    def validate(self) -> None:
        if self.max_batch_size < 1:
            raise ValueError("INFERENCE_MAX_BATCH must be >= 1")
        if self.max_image_mb <= 0 or self.max_image_pixels <= 0:
            raise ValueError("image size limits must be positive")
        if not 0.0 <= self.conf <= 1.0 or not 0.0 <= self.iou <= 1.0:
            raise ValueError("INFERENCE_CONF/INFERENCE_IOU must be in [0, 1]")
        if self.imgsz <= 0:
            raise ValueError("INFERENCE_IMGSZ must be positive")
