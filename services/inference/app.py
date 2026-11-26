"""FastAPI entrypoint for A-08.

Run locally:
  uvicorn services.inference.app:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException

from services.inference.config import SERVICE_VERSION
from services.inference.service import (
    InferenceService,
    PredictRequest,
    PredictResponse,
    build_default_service,
)

logger = logging.getLogger(__name__)


def create_app(service: InferenceService | None = None) -> FastAPI:
    svc = service or build_default_service()
    app = FastAPI(title="智巡卫士推理服务", version=SERVICE_VERSION)

    @app.get("/health")
    def health() -> dict:
        return svc.health()

    @app.get("/version")
    def version() -> dict:
        return svc.version()

    @app.post("/predict", response_model=PredictResponse)
    def predict(request: PredictRequest) -> PredictResponse:
        try:
            return svc.predict(request)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=503, detail=f"model not found: {exc}") from exc
        except Exception as exc:  # pragma: no cover - defensive boundary
            logger.exception("inference failed")
            raise HTTPException(status_code=500, detail="inference failed") from exc

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("services.inference.app:app", host="0.0.0.0", port=8000)
