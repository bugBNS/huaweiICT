FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    MODEL_PATH=/models/yolo11n.pt \
    INFERENCE_DEVICE=cpu

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY services/inference/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY schemas /app/schemas
COPY ml /app/ml
COPY services /app/services

EXPOSE 8000

# The model is mounted at /models/yolo11n.pt (or downloaded from OBS by the
# deployment platform). It is intentionally not baked into the image.
CMD ["uvicorn", "services.inference.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
