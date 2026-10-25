"""Face detector supporting both InsightFace (RetinaFace + ArcFace) and OpenCV Haar/Cascade fallback."""
import importlib.util
import threading
from dataclasses import dataclass
from typing import Optional
import numpy as np

_app = None
_cascade_face = None
_cascade_eye = None
_lock = threading.Lock()


@dataclass
class OpenCVFace:
    bbox: np.ndarray
    embedding: Optional[np.ndarray] = None
    landmark_3d_68: Optional[np.ndarray] = None
    ear: Optional[float] = None


def has_insightface() -> bool:
    return (
        importlib.util.find_spec("insightface") is not None
        and importlib.util.find_spec("onnxruntime") is not None
    )


def has_opencv() -> bool:
    return importlib.util.find_spec("cv2") is not None


def get_app():
    global _app
    if _app is None:
        with _lock:
            if _app is None:
                from insightface.app import FaceAnalysis  # imported lazily
                app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
                app.prepare(ctx_id=-1, det_size=(640, 640))
                _app = app
    return _app


def _get_cascades():
    global _cascade_face, _cascade_eye
    if _cascade_face is None:
        with _lock:
            if _cascade_face is None:
                import cv2
                _cascade_face = cv2.CascadeClassifier(
                    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
                )
                _cascade_eye = cv2.CascadeClassifier(
                    cv2.data.haarcascades + "haarcascade_eye.xml"
                )
    return _cascade_face, _cascade_eye


def detect(img_bgr, backend="auto"):
    """Return Face objects sorted by bbox area (largest first)."""
    use_if = (backend == "insightface" and has_insightface()) or (
        backend == "auto" and has_insightface()
    )
    if use_if:
        faces = get_app().get(img_bgr)
        return sorted(
            faces,
            key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]),
            reverse=True,
        )
    return detect_opencv(img_bgr)


def detect_opencv(img_bgr):
    """Real OpenCV face & eye detection fallback when InsightFace C++ wheels are unavailable."""
    import cv2
    face_cascade, eye_cascade = _get_cascades()
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    gray_eq = cv2.equalizeHist(gray)
    rects = face_cascade.detectMultiScale(
        gray_eq, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60)
    )
    if len(rects) == 0:
        # Try slightly more permissive parameters for angled faces
        rects = face_cascade.detectMultiScale(
            gray_eq, scaleFactor=1.08, minNeighbors=3, minSize=(50, 50)
        )
    faces = []
    for (x, y, w, h) in rects:
        bbox = np.array([x, y, x + w, y + h], dtype=np.float32)
        roi_upper = gray_eq[y : y + int(h * 0.65), x : x + w]
        eyes = eye_cascade.detectMultiScale(roi_upper, scaleFactor=1.1, minNeighbors=3, minSize=(14, 14))
        # Estimate effective EAR from eye detection count/height ratio for blink liveness
        if len(eyes) >= 1:
            avg_eh = float(np.mean([eh / max(ew, 1) for (_, _, ew, eh) in eyes]))
            ear_val = float(np.clip(0.24 + 0.12 * min(avg_eh, 1.0), 0.22, 0.35))
        else:
            ear_val = 0.17  # Eyes closed / blinking
        faces.append(OpenCVFace(bbox=bbox, ear=ear_val))
    return sorted(
        faces,
        key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]),
        reverse=True,
    )
