"""CV hazard detection: YOLOv8 inference, preprocessing, crack severity.

`cv2` and `ultralytics` are imported lazily so the API and tests run without the
heavy ML stack installed. When the model or image is unavailable, detect() returns [].
"""
import os

from ..config import Config

_model = None
_model_loaded = False


def _get_model():
    global _model, _model_loaded
    if _model_loaded:
        return _model
    _model_loaded = True
    try:
        from ultralytics import YOLO  # type: ignore
    except ImportError:
        return None
    if os.path.exists(Config.YOLO_WEIGHTS):
        _model = YOLO(Config.YOLO_WEIGHTS)
    return _model


def preprocess(image_bgr):
    """Resize to 640x640 and apply CLAHE in LAB space to reveal surface detail."""
    import cv2  # type: ignore
    import numpy as np  # type: ignore

    img = cv2.resize(image_bgr, (640, 640))
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    return cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)


def _severity_for(hazard_class, bbox):
    """Crack severity heuristic from box size; defaults low for other classes."""
    if hazard_class != "crack":
        return "low"
    x1, y1, x2, y2 = bbox
    w, h = max(1.0, x2 - x1), max(1.0, y2 - y1)
    ratio = max(w, h) / max(1.0, min(w, h))
    area = w * h
    if ratio >= 8 and area >= 2000:
        return "high"
    if ratio >= 4 or area >= 1000:
        return "medium"
    return "low"


def detect(image_path, threshold=None, class_weights=None):
    """Run detection on one image. Returns a list of hazard detection dicts."""
    threshold = Config.DETECTION_CONFIDENCE_THRESHOLD if threshold is None else threshold
    class_weights = class_weights or Config.CLASS_WEIGHTS
    model = _get_model()
    if model is None or not image_path or not os.path.exists(image_path):
        return []

    try:
        import cv2  # type: ignore
        image = cv2.imread(image_path)
        if image is None:
            return []
        results = model.predict(preprocess(image), verbose=False)
    except Exception:
        return []

    detections = []
    for result in results:
        names = getattr(result, "names", {})
        boxes = getattr(result, "boxes", None)
        if boxes is None:
            continue
        for box in boxes:
            conf = float(box.conf[0])
            if conf < threshold:
                continue
            cls_id = int(box.cls[0])
            hazard_class = names.get(cls_id, str(cls_id))
            if hazard_class not in class_weights:
                continue
            bbox = [float(v) for v in box.xyxy[0]]
            severity = _severity_for(hazard_class, bbox)
            detections.append(
                {
                    "hazard_class": hazard_class,
                    "confidence": conf,
                    "bbox": bbox,
                    "severity": severity,
                    "severity_weight": Config.SEVERITY_WEIGHTS.get(severity, 1),
                    "class_weight": class_weights[hazard_class],
                }
            )
    return detections
