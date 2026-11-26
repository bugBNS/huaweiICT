"""Detector backends for the A-08 inference service.

The service depends on the small ``Detector`` protocol, not on Ultralytics
directly.  This keeps unit tests fast and makes a future RTMDet backend a
drop-in replacement.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

import numpy as np

from ml.detector.config import TARGET_CLASSES
from schemas.models import BBoxXYXY, Detection


class Detector(Protocol):
    """Minimal detector interface used by InferenceService."""

    model_version: str

    @property
    def is_loaded(self) -> bool:
        ...

    def predict(
        self,
        image: np.ndarray,
        *,
        conf: float,
        iou: float,
        imgsz: int,
    ) -> list[Detection]:
        """Return person/forklift detections in IMAGE_PIXEL coordinates."""
        ...


class YoloDetector:
    """Ultralytics YOLO backend.

    The model is loaded lazily on the first request.  Loading at import time
    would make ``/health`` slow and would break tests/environments without
    weights.
    """

    def __init__(self, model_path: str, device: str = "cpu", model_version: str | None = None):
        self.model_path = model_path
        self.device = device
        self.model_version = model_version or Path(model_path).stem or "yolo"
        self._model = None

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def _load(self):
        if self._model is None:
            from ultralytics import YOLO

            self._model = YOLO(self.model_path)
        return self._model

    @staticmethod
    def _class_name(names, cls_id: int) -> str:
        if isinstance(names, dict):
            return str(names.get(cls_id, cls_id))
        if isinstance(names, (list, tuple)) and 0 <= cls_id < len(names):
            return str(names[cls_id])
        return str(cls_id)

    def predict(
        self,
        image: np.ndarray,
        *,
        conf: float,
        iou: float,
        imgsz: int,
    ) -> list[Detection]:
        model = self._load()
        height, width = image.shape[:2]
        # Ultralytics treats numpy arrays as BGR; the service decodes RGB.
        source = np.ascontiguousarray(image[:, :, ::-1])
        results = model.predict(
            source=source,
            conf=conf,
            iou=iou,
            imgsz=imgsz,
            device=self.device,
            verbose=False,
        )
        if not results:
            return []
        result = results[0]
        boxes = result.boxes
        if boxes is None:
            return []

        names = getattr(model, "names", {})
        detections: list[Detection] = []
        for box in boxes:
            name = self._class_name(names, int(box.cls.item()))
            if name not in TARGET_CLASSES:
                continue
            x1, y1, x2, y2 = (float(v) for v in box.xyxy[0].tolist())
            # Keep boxes inside the image and drop degenerate rectangles;
            # DetectionFrame/BBoxXYXY rejects x2<=x1 or y2<=y1.
            x1 = min(max(x1, 0.0), max(width - 1.0, 0.0))
            y1 = min(max(y1, 0.0), max(height - 1.0, 0.0))
            x2 = min(max(x2, 0.0), max(width - 1.0, 0.0))
            y2 = min(max(y2, 0.0), max(height - 1.0, 0.0))
            if x2 <= x1 or y2 <= y1:
                continue
            score = min(max(float(box.conf.item()), 0.0), 1.0)
            detections.append(
                Detection(
                    **{"class": name},
                    bbox=BBoxXYXY(x1=x1, y1=y1, x2=x2, y2=y2, unit="px"),
                    conf=score,
                )
            )
        return detections
