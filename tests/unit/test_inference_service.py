from __future__ import annotations

import base64
import io

import numpy as np
import pytest
from PIL import Image
from pydantic import ValidationError

from schemas.models import BBoxXYXY, Detection
from services.inference.config import Settings
from services.inference.service import ImageInput, InferenceService, PredictRequest, decode_image


class FakeDetector:
    model_version = "fake-yolo"

    @property
    def is_loaded(self) -> bool:
        return True

    def predict(self, image: np.ndarray, *, conf: float, iou: float, imgsz: int) -> list[Detection]:
        height, width = image.shape[:2]
        return [
            Detection(
                **{"class": "person"},
                bbox=BBoxXYXY(x1=1, y1=2, x2=width - 1, y2=height - 1, unit="px"),
                conf=0.9,
            )
        ]


def _png_base64(width: int = 64, height: int = 48) -> str:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), (120, 120, 120)).save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _request(images: list[ImageInput], run_id: str = "run_x") -> PredictRequest:
    return PredictRequest(run_id=run_id, scenario_id="near_miss", images=images)


def _service(**overrides) -> InferenceService:
    settings = Settings(model_path="unused.pt", **overrides)
    return InferenceService(FakeDetector(), settings)


def test_predict_returns_detection_frames() -> None:
    service = _service()
    response = service.predict(
        _request([ImageInput(image_id="frame_001", image_base64=_png_base64(), timestamp_ms=120)])
    )

    assert response.n_images == 1
    frame = response.frames[0]
    assert frame.run_id == "run_x"
    assert frame.scenario_id == "near_miss"
    assert frame.coordinate_mode.value == "IMAGE_PIXEL"
    assert frame.image_id == "frame_001"
    assert frame.image_width == 64
    assert frame.image_height == 48
    assert frame.timestamp_ms == 120
    assert frame.model_version == "fake-yolo"
    assert frame.detections[0].class_name.value == "person"
    assert frame.detections[0].bbox.unit == "px"
    assert response.model_dump(by_alias=True)["frames"][0]["detections"][0]["class"] == "person"


def test_data_url_prefix_is_accepted() -> None:
    service = _service()
    data_url = f"data:image/png;base64,{_png_base64(32, 24)}"
    response = service.predict(_request([ImageInput(image_id="frame_002", image_base64=data_url)]))
    assert response.frames[0].image_width == 32
    assert response.frames[0].image_height == 24


def test_batch_limit_is_enforced() -> None:
    service = _service(max_batch_size=1)
    request = _request(
        [
            ImageInput(image_id="a", image_base64=_png_base64()),
            ImageInput(image_id="b", image_base64=_png_base64()),
        ]
    )
    with pytest.raises(ValueError, match="max is 1"):
        service.predict(request)


def test_duplicate_image_id_is_rejected() -> None:
    service = _service(max_batch_size=2)
    request = _request(
        [
            ImageInput(image_id="same", image_base64=_png_base64()),
            ImageInput(image_id="same", image_base64=_png_base64()),
        ]
    )
    with pytest.raises(ValueError, match="duplicate image_id"):
        service.predict(request)


def test_empty_batch_is_rejected_by_schema() -> None:
    with pytest.raises(ValidationError):
        PredictRequest(run_id="run_x", images=[])


def test_bad_base64_is_rejected() -> None:
    service = _service()
    with pytest.raises(ValueError, match="valid base64"):
        service.predict(_request([ImageInput(image_id="bad", image_base64="not-base64")]))


def test_image_size_limit_is_enforced() -> None:
    service = _service(max_image_mb=0.0001)
    with pytest.raises(ValueError, match="exceeds"):
        service.predict(_request([ImageInput(image_id="large", image_base64=_png_base64())]))


def test_image_pixel_limit_is_enforced() -> None:
    service = _service(max_image_pixels=100)
    with pytest.raises(ValueError, match="pixels"):
        service.predict(_request([ImageInput(image_id="large", image_base64=_png_base64())]))


def test_decode_image_rejects_non_image_bytes() -> None:
    with pytest.raises(ValueError, match="corrupted"):
        decode_image(
            base64.b64encode(b"not an image").decode("ascii"),
            max_bytes=1024,
            max_pixels=1024,
        )
