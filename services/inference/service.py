"""Batch image inference with S-01 DetectionFrame output.

The HTTP layer is intentionally thin; this module owns validation, image
decoding, batching, and conversion to the shared schema.  It can be tested
without FastAPI or model weights.
"""

from __future__ import annotations

import base64
import binascii
import io
import time

import numpy as np
from PIL import Image, UnidentifiedImageError
from pydantic import Field

from schemas.models import DetectionFrame, SCHEMA_VERSION, StrictModel
from services.inference.config import SERVICE_VERSION, Settings
from services.inference.detector import Detector, YoloDetector


class ImageInput(StrictModel):
    image_id: str = Field(min_length=1, max_length=128)
    image_base64: str = Field(min_length=1)
    timestamp_ms: int = Field(default=0, ge=0)


class PredictRequest(StrictModel):
    run_id: str = Field(min_length=1, max_length=128)
    scenario_id: str | None = Field(default=None, max_length=128)
    images: list[ImageInput] = Field(min_length=1, max_length=8)


class PredictResponse(StrictModel):
    schema_version: str = SCHEMA_VERSION
    service_version: str = SERVICE_VERSION
    model_version: str
    n_images: int
    elapsed_ms: float
    frames: list[DetectionFrame]


def decode_image(image_base64: str, *, max_bytes: int, max_pixels: int) -> np.ndarray:
    """Decode a data URL or raw base64 string into an RGB uint8 array."""
    raw = image_base64.strip()
    if raw.startswith("data:"):
        if "," not in raw:
            raise ValueError("invalid data URL: missing comma")
        raw = raw.split(",", 1)[1]
    raw = "".join(raw.split())
    if not raw:
        raise ValueError("image_base64 is empty")

    try:
        payload = base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("image_base64 is not valid base64") from exc
    if len(payload) > max_bytes:
        raise ValueError(f"image exceeds {max_bytes} bytes")
    if not payload:
        raise ValueError("image_base64 decodes to zero bytes")

    try:
        with Image.open(io.BytesIO(payload)) as img:
            width, height = img.size
            if width <= 0 or height <= 0:
                raise ValueError("image has invalid dimensions")
            if width * height > max_pixels:
                raise ValueError(f"image exceeds {max_pixels} pixels")
            img.load()
            rgb = np.asarray(img.convert("RGB"))
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError("unsupported or corrupted image") from exc

    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError("decoded image is not RGB")
    return rgb


class InferenceService:
    def __init__(self, detector: Detector, settings: Settings):
        settings.validate()
        self.detector = detector
        self.settings = settings

    def health(self) -> dict:
        return {
            "status": "ok",
            "model_loaded": self.detector.is_loaded,
            "model_version": self.detector.model_version,
            "model_path": self.settings.model_path,
            "device": self.settings.device,
        }

    def version(self) -> dict:
        return {
            "service_version": SERVICE_VERSION,
            "schema_version": SCHEMA_VERSION,
            "model_version": self.detector.model_version,
        }

    def predict(self, request: PredictRequest) -> PredictResponse:
        if len(request.images) > self.settings.max_batch_size:
            raise ValueError(
                f"batch has {len(request.images)} images; max is {self.settings.max_batch_size}"
            )

        seen: set[str] = set()
        frames: list[DetectionFrame] = []
        started = time.perf_counter()
        for item in request.images:
            if item.image_id in seen:
                raise ValueError(f"duplicate image_id: {item.image_id}")
            seen.add(item.image_id)

            image = decode_image(
                item.image_base64,
                max_bytes=self.settings.max_image_bytes,
                max_pixels=self.settings.max_image_pixels,
            )
            detections = self.detector.predict(
                image,
                conf=self.settings.conf,
                iou=self.settings.iou,
                imgsz=self.settings.imgsz,
            )
            height, width = image.shape[:2]
            frames.append(
                DetectionFrame(
                    run_id=request.run_id,
                    scenario_id=request.scenario_id,
                    model_version=self.detector.model_version,
                    risk_rule_version=None,
                    coordinate_mode="IMAGE_PIXEL",
                    timestamp_ms=item.timestamp_ms,
                    image_id=item.image_id,
                    image_width=int(width),
                    image_height=int(height),
                    detections=detections,
                )
            )

        elapsed_ms = round((time.perf_counter() - started) * 1000.0, 2)
        return PredictResponse(
            model_version=self.detector.model_version,
            n_images=len(frames),
            elapsed_ms=elapsed_ms,
            frames=frames,
        )


def build_default_service() -> InferenceService:
    settings = Settings.from_env()
    detector = YoloDetector(
        settings.model_path,
        device=settings.device,
        model_version=settings.model_version,
    )
    return InferenceService(detector, settings)
