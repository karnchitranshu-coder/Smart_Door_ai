"""Face embedding generator: ArcFace 512-d (InsightFace) or CLAHE+HOG+DCT 512-d (OpenCV fallback)."""
import numpy as np
from .similarity import normalize


def embed(face, crop_bgr=None) -> np.ndarray:
    """Return 512-d L2-normalised face embedding vector."""
    if getattr(face, "embedding", None) is not None:
        return normalize(face.embedding)
    if crop_bgr is not None and crop_bgr.size > 0:
        return _opencv_embed_512(crop_bgr)
    return normalize(np.zeros(512, dtype=np.float32))


def _opencv_embed_512(crop_bgr: np.ndarray) -> np.ndarray:
    """Compute a 512-d illumination-normalized facial descriptor using OpenCV.
    Combines:
      1) 256-d spatial gradient orientation histogram (8x8 cells x 4 orientation bins)
      2) 128-d 2D DCT low-frequency structural coefficients (excluding DC illumination term)
      3) 128-d multi-scale CLAHE spatial appearance grid (8x8 mean + 8x8 local std)
    """
    import cv2

    gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
    # Crop inner 80% to reduce background noise around the face box
    h, w = gray.shape
    mx, my = int(w * 0.1), int(h * 0.1)
    if w - 2 * mx >= 32 and h - 2 * my >= 32:
        gray = gray[my : h - my, mx : w - mx]

    aligned = cv2.resize(gray, (128, 128), interpolation=cv2.INTER_AREA)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    norm_img = clahe.apply(aligned).astype(np.float32) / 255.0

    # 1) 256-d spatial gradient orientation histogram (8x8 grid of 16x16 cells, 4 bins)
    gx = cv2.Sobel(norm_img, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(norm_img, cv2.CV_32F, 0, 1, ksize=3)
    mag, ang = cv2.cartToPolar(gx, gy, angleInDegrees=False)
    bins = np.int32((ang / (2.0 * np.pi)) * 4) % 4
    hog_feats = []
    for cy in range(0, 128, 16):
        for cx in range(0, 128, 16):
            cell_m = mag[cy : cy + 16, cx : cx + 16]
            cell_b = bins[cy : cy + 16, cx : cx + 16]
            hist = [float(cell_m[cell_b == b].sum()) for b in range(4)]
            hog_feats.extend(hist)
    hog_vec = normalize(np.array(hog_feats, dtype=np.float32))  # 256-d

    # 2) 128-d 2D DCT low-frequency facial geometry coefficients
    dct_full = cv2.dct(norm_img)
    dct_low = dct_full[:12, :12].flatten()[1:129]  # skip [0,0] DC lighting component -> 128-d
    dct_vec = normalize(dct_low.astype(np.float32))

    # 3) 128-d spatial grid (8x8 local mean + 8x8 local standard deviation)
    small_8 = cv2.resize(norm_img, (8, 8), interpolation=cv2.INTER_AREA).flatten()
    std_grid = []
    for cy in range(0, 128, 16):
        for cx in range(0, 128, 16):
            std_grid.append(float(norm_img[cy : cy + 16, cx : cx + 16].std()))
    grid_vec = normalize(np.concatenate([small_8 - small_8.mean(), np.array(std_grid, dtype=np.float32)]))  # 128-d

    combined = np.concatenate([hog_vec * 0.50, dct_vec * 0.30, grid_vec * 0.20]).astype(np.float32)
    return normalize(combined)
