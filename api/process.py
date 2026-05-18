"""
GroupShot API — /api/process
Handles:
  1. Background removal via rembg (U2Net)
  2. Face detection via OpenCV (haarcascade) with MediaPipe fallback
  3. Smart face-centered crop to a square
Returns: base64-encoded PNG (transparent bg) + face bounding box
"""

import os
import io
import json
import base64
import traceback
from http.server import BaseHTTPRequestHandler

import numpy as np
from PIL import Image

try:
    from rembg import remove as rembg_remove, new_session
    REMBG_AVAILABLE = True
except ImportError:
    REMBG_AVAILABLE = False

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

# ── CACHED SESSIONS (warm across requests on same worker) ──────────────────
_rembg_session = None
_face_cascade  = None

def get_rembg_session():
    global _rembg_session
    if _rembg_session is None and REMBG_AVAILABLE:
        # birefnet-portrait is significantly more accurate than u2net_human_seg
        # for portrait/headshot photos
        _rembg_session = new_session("birefnet-portrait")
    return _rembg_session

def get_face_cascade():
    global _face_cascade
    if _face_cascade is None and CV2_AVAILABLE:
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        _face_cascade = cv2.CascadeClassifier(cascade_path)
    return _face_cascade


# ── ALPHA MASK CLEANUP ────────────────────────────────────────────────────
def clean_alpha_mask(img_rgba: Image.Image) -> Image.Image:
    """
    Post-process the alpha channel for cleaner cutouts:
    1. Hard-threshold noise (near-transparent → fully transparent)
    2. Morphological close to fill small holes in the subject
    3. Morphological open to remove isolated background specks
    4. Slight Gaussian blur for natural edge feathering
    """
    arr = np.array(img_rgba, dtype=np.uint8)
    alpha = arr[:, :, 3].copy()

    if CV2_AVAILABLE:
        # Hard threshold: clip noise at both ends
        _, alpha = cv2.threshold(alpha, 10, 255, cv2.THRESH_TOZERO)
        _, alpha = cv2.threshold(alpha, 240, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Close small holes inside the person
        close_k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        alpha = cv2.morphologyEx(alpha, cv2.MORPH_CLOSE, close_k)

        # Remove tiny isolated background specks
        open_k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        alpha = cv2.morphologyEx(alpha, cv2.MORPH_OPEN, open_k)

        # Soft feather the edges for a natural look
        alpha = cv2.GaussianBlur(alpha, (3, 3), sigmaX=0.8)
    else:
        # Fallback: simple numpy threshold
        alpha = np.where(alpha < 10, 0, np.where(alpha > 240, 255, alpha)).astype(np.uint8)

    arr[:, :, 3] = alpha
    return Image.fromarray(arr)


# ── FACE DETECTION ─────────────────────────────────────────────────────────
def detect_face_box(img_pil: Image.Image):
    """
    Returns (x, y, w, h) of the best face bounding box, or None.
    Tries OpenCV first; falls back to whole-image center crop.
    """
    if not CV2_AVAILABLE:
        return None

    img_rgb = np.array(img_pil.convert("RGB"))
    img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
    cascade = get_face_cascade()

    faces = cascade.detectMultiScale(
        img_gray,
        scaleFactor=1.05,
        minNeighbors=4,
        minSize=(30, 30),
        flags=cv2.CASCADE_SCALE_IMAGE,
    )

    if len(faces) == 0:
        # Try with more relaxed params
        faces = cascade.detectMultiScale(
            img_gray, scaleFactor=1.1, minNeighbors=2, minSize=(20, 20)
        )

    if len(faces) == 0:
        return None

    # Pick the largest face
    faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
    x, y, w, h = faces[0]
    return (int(x), int(y), int(w), int(h))


# ── SMART CROP (face-centered square) ─────────────────────────────────────
def smart_face_crop(img_pil: Image.Image, face_box, padding_ratio=0.35):
    """
    Crops a square region centered on the face with padding.
    If no face box is given, crops center square.
    Returns PIL Image (RGBA, square).
    """
    W, H = img_pil.size

    if face_box:
        fx, fy, fw, fh = face_box
        cx = fx + fw // 2
        cy = fy + fh // 2

        # Expand to include forehead + shoulders
        head_size = max(fw, fh)
        crop_size = int(head_size * (1 + padding_ratio * 2))

        # Shift center UP so ~65% of face height sits above fy (hair room).
        # Haar cascade boxes start at eyebrow level, not hairline.
        cy_adj = int(cy - fh * 0.25)
    else:
        # Center crop
        cx, cy_adj = W // 2, H // 2
        crop_size = min(W, H)

    half = crop_size // 2
    x1 = max(0, cx - half)
    y1 = max(0, cy_adj - half)
    x2 = min(W, x1 + crop_size)
    y2 = min(H, y1 + crop_size)

    # Adjust if we hit edges
    if x2 - x1 < crop_size:
        x1 = max(0, x2 - crop_size)
    if y2 - y1 < crop_size:
        y1 = max(0, y2 - crop_size)

    cropped = img_pil.crop((x1, y1, x2, y2))

    # Ensure it's actually square (minor pixel differences)
    cw, ch = cropped.size
    s = min(cw, ch)
    left = (cw - s) // 2
    top  = (ch - s) // 2
    cropped = cropped.crop((left, top, left + s, top + s))

    return cropped


# ── MAIN HANDLER ──────────────────────────────────────────────────────────
class handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        pass  # Suppress default access log noise

    def send_json(self, status: int, data: dict):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_length)
            payload = json.loads(raw_body)

            # ── 1. Decode incoming image ──────────────────────────────────
            img_b64 = payload.get("image", "")
            if "," in img_b64:
                img_b64 = img_b64.split(",", 1)[1]
            img_bytes = base64.b64decode(img_b64)
            img_pil = Image.open(io.BytesIO(img_bytes)).convert("RGBA")

            # ── 2. Background removal ─────────────────────────────────────
            if REMBG_AVAILABLE:
                session = get_rembg_session()
                img_nobg = rembg_remove(img_pil, session=session).convert("RGBA")
                img_nobg = clean_alpha_mask(img_nobg)
            else:
                # Fallback: return original with no bg removal
                img_nobg = img_pil

            # ── 3. Face detection ─────────────────────────────────────────
            face_box = detect_face_box(img_nobg)

            # ── 4. Face-centered crop ─────────────────────────────────────
            cropped = smart_face_crop(img_nobg, face_box, padding_ratio=0.45)

            # ── 5. Resize to consistent output size ───────────────────────
            out_size = int(payload.get("size", 512))
            out_size = max(128, min(1024, out_size))
            cropped = cropped.resize((out_size, out_size), Image.LANCZOS)

            # ── 6. Encode result ──────────────────────────────────────────
            buf = io.BytesIO()
            cropped.save(buf, format="PNG", optimize=False)
            result_b64 = base64.b64encode(buf.getvalue()).decode()

            self.send_json(200, {
                "ok": True,
                "image": f"data:image/png;base64,{result_b64}",
                "face_detected": face_box is not None,
                "face_box": face_box,
                "rembg": REMBG_AVAILABLE,
                "cv2": CV2_AVAILABLE,
            })

        except Exception as e:
            self.send_json(500, {
                "ok": False,
                "error": str(e),
                "trace": traceback.format_exc(),
            })
