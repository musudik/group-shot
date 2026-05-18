"""
Local development server for GroupShot.
Serves index.html and handles /api/process.
Usage: python server.py
"""

import sys
import os
import io
import json
import base64
import traceback
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

PORT = 3000

# Import processing functions directly (lazy model loading)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from api.process import (
    get_rembg_session, get_face_cascade,
    detect_face_box, smart_face_crop,
    REMBG_AVAILABLE, CV2_AVAILABLE,
)
from PIL import Image


def handle_process(rfile, headers):
    """Run the image processing pipeline. Returns (status, dict)."""
    try:
        content_length = int(headers.get("Content-Length", 0))
        raw_body = rfile.read(content_length)
        payload = json.loads(raw_body)

        img_b64 = payload.get("image", "")
        if "," in img_b64:
            img_b64 = img_b64.split(",", 1)[1]
        img_bytes = base64.b64decode(img_b64)
        img_pil = Image.open(io.BytesIO(img_bytes)).convert("RGBA")

        if REMBG_AVAILABLE:
            from rembg import remove as rembg_remove
            session = get_rembg_session()
            img_nobg = rembg_remove(img_pil, session=session).convert("RGBA")
        else:
            img_nobg = img_pil

        face_box = detect_face_box(img_nobg)
        cropped = smart_face_crop(img_nobg, face_box, padding_ratio=0.4)

        out_size = max(128, min(1024, int(payload.get("size", 512))))
        cropped = cropped.resize((out_size, out_size), Image.LANCZOS)

        buf = io.BytesIO()
        cropped.save(buf, format="PNG", optimize=False)
        result_b64 = base64.b64encode(buf.getvalue()).decode()

        return 200, {
            "ok": True,
            "image": f"data:image/png;base64,{result_b64}",
            "face_detected": face_box is not None,
            "face_box": face_box,
            "rembg": REMBG_AVAILABLE,
            "cv2": CV2_AVAILABLE,
        }
    except Exception as e:
        return 500, {"ok": False, "error": str(e), "trace": traceback.format_exc()}


class LocalHandler(SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"  {self.command} {self.path}")

    def _send_json(self, status, data):
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
        if self.path == "/api/process":
            status, result = handle_process(self.rfile, self.headers)
            self._send_json(status, result)
        else:
            self.send_error(405)

    def do_GET(self):
        if self.path == "/":
            self.path = "/index.html"
        super().do_GET()


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    server = ThreadingHTTPServer(("", PORT), LocalHandler)
    print(f"\n  GroupShot running at http://localhost:{PORT}")
    print("  Press Ctrl+C to stop.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server stopped.")
        sys.exit(0)
