"""检测类别与默认参数（A-02）。"""

from __future__ import annotations

CLASSES: tuple[str, str] = ("person", "forklift")
CLASS_TO_ID = {name: idx for idx, name in enumerate(CLASSES)}

DEFAULT_CONF = 0.25
DEFAULT_IOU = 0.5
DEFAULT_IMGSZ = 640

# Ultralytics/COCO 预训练模型没有 forklift 类；只有微调后的权重才能输出两类。
# 这里只保留 person/forklift，不把 truck 等类别强行映射成 forklift。
TARGET_CLASSES = set(CLASSES)
