"""Master orchestrator: decode -> detect -> quality -> embed (-> liveness)."""
import hashlib
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from django.conf import settings

from . import detector, liveness as live
from .similarity import normalize


@dataclass
class FaceResult:
    face_found: bool = False
    quality_ok: bool = False
    reason: Optional[str] = None
    quality: float = 0.0
    embedding: Optional[np.ndarray] = None
    bbox: Optional[list] = None
    ear: Optional[float] = None
    crop: Optional[np.ndarray] = field(default=None, repr=False)
    image: Optional[np.ndarray] = field(default=None, repr=False)


def active_ai_backend() -> str:
    """Return effective AI backend ('insightface', 'opencv', or 'mock')."""
    configured = getattr(settings, "AI_BACKEND", "auto")
    if configured == "mock":
        return "mock"
    if configured in ("auto", "insightface") and detector.has_insightface():
        return "insightface"
    if detector.has_opencv():
        return "opencv"
    return "mock"


class FacePipeline:
    def analyze(self, data: bytes) -> FaceResult:
        mode = active_ai_backend()
        if mode == "mock":
            return self._mock(data)
        return self._real(data, mode=mode)

    # ---- deterministic fake backend: same bytes -> same embedding (tests / no-GPU demo) ----
    @staticmethod
    def _mock(data: bytes) -> FaceResult:
        if not data:
            return FaceResult(reason="empty_image")
        seed = int(hashlib.sha256(data).hexdigest()[:8], 16)
        emb = normalize(np.random.default_rng(seed).standard_normal(512))
        return FaceResult(True, True, None, 0.9, emb, [0, 0, 200, 200])

    @staticmethod
    def _real(data: bytes, mode: str = "auto") -> FaceResult:
        import cv2
        from . import quality, recognizer

        if not data:
            return FaceResult(reason="empty_image")
        img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            return FaceResult(reason="bad_image")
        faces = detector.detect(img, backend=mode)
        if not faces:
            return FaceResult(reason="no_face")
        f = faces[0]
        q = quality.assess(img, f.bbox)
        x1, y1, x2, y2 = [int(max(0, v)) for v in f.bbox]
        crop = img[y1:y2, x1:x2]
        lm = getattr(f, "landmark_3d_68", None)
        ear_val = (
            live.eye_aspect_ratio(lm)
            if lm is not None
            else getattr(f, "ear", None)
        )
        return FaceResult(
            face_found=True,
            quality_ok=q["ok"],
            reason=q["reason"],
            quality=q["score"],
            embedding=recognizer.embed(f, crop_bgr=crop),
            bbox=[x1, y1, x2, y2],
            ear=ear_val,
            crop=crop,
            image=img,
        )

    def liveness(self, results) -> tuple:
        if active_ai_backend() == "mock":
            return True, "mock"
        return live.check(results)


pipeline = FacePipeline()
