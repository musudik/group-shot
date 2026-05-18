# GroupShot — Team Photo Creator

> A stylish, mobile-responsive web app that generates professional group photos from individual team member images. Powered by AI background removal (rembg / BiRefNet) and OpenCV face detection.

---

## ✨ Full Feature List

### 📸 Image Upload
- Drag & drop or click-to-browse file picker
- Supports **JPG, PNG, WEBP** formats
- Upload up to **30 team member photos**
- Per-photo thumbnail preview with hover-to-remove (✕) button
- Per-photo **Name** and **Designation** labels (rendered below each photo in the final output)
- **Clear All** button to reset the entire session

---

### 🤖 AI Processing Pipeline (Python Backend)
Each uploaded photo is processed server-side through a 5-step pipeline:

| Step | What Happens |
|---|---|
| 1 | Decode uploaded image (JPEG/PNG/WEBP → PIL RGBA) |
| 2 | **Background removal** via `rembg` using the `birefnet-portrait` model (most accurate for people) |
| 3 | **Alpha mask cleanup** — noise removal, morphological close/open, Gaussian edge feathering |
| 4 | **Face detection** via OpenCV Haar Cascade (`haarcascade_frontalface_default`) with relaxed fallback pass |
| 5 | **Smart face-centred crop** — square crop expanded with 45% padding, shifted up to include hairline |

- Processed images are **cached in-browser** — re-generating with the same photos skips the API call
- Background removal can be toggled **On / Off** per session (Off = faster, uses original photo)

---

### 🖼 Canvas Size — Aspect Ratios
Default: **9:16 Portrait**

| Ratio | Resolution | Use Case |
|---|---|---|
| 9:16 | 1080 × 1920 | Mobile / Stories (default) |
| 16:9 | 1920 × 1080 | Desktop / YouTube banner |
| 1:1 | 1080 × 1080 | Instagram square |
| 4:5 | 1080 × 1350 | Instagram portrait |
| 5:4 | 1350 × 1080 | Instagram landscape |
| 3:2 | 1500 × 1000 | Classic photo print |
| 2:3 | 1000 × 1500 | Classic portrait print |
| 4:3 | 1440 × 1080 | Standard screen |
| 3:4 | 1080 × 1440 | Standard portrait |
| 21:9 | 2100 × 900 | Cinematic / LinkedIn banner |
| 2:1 | 1600 × 800 | Wide banner |
| 1:2 | 800 × 1600 | Tall banner |

---

### ✂️ Photo Shape
Each team member's cropped photo is masked into one of 7 shapes:

| Shape | Default |
|---|---|
| ⬤ Circle | ✅ Default |
| ⬡ Hexagon | |
| ■ Square | |
| ▣ Rounded Square | |
| ◆ Diamond | |
| ♥ Heart | |
| ★ Star | |

---

### 📐 Layout Mode

| Mode | Behaviour |
|---|---|
| **Auto Grid** *(default)* | Optimal grid columns/rows calculated automatically for any count |
| **Single Row** | All photos on a single horizontal line |
| **Pyramid** | Rows of increasing size (1 at top, expanding downward) |

- **Gap slider** — adjust spacing between photos (0.2× to 2.5×)

---

### 🎨 Background
| Option | Description |
|---|---|
| **Dark** *(default)* | Deep charcoal `#111410` with noise texture |
| **Forest Green** | Dark `#0d221a` with green band accent |
| **Red** | Deep crimson `#1a0808` with red floor |
| **Light** | Cream `#f0ead6` for light prints |
| **Gradient** | Dark green → red → navy diagonal |
| **Custom Image** | Upload your own background (JPG/PNG/WEBP) — fills entire canvas |

All built-in backgrounds include a subtle diagonal geometric accent stripe inspired by vintage sports poster design.

---

### 🏷 Logos / Watermarks
- Upload up to **4 logos** (sponsor logos, club badges, etc.)
- Each logo has an independent **position selector**:
  - ↖ Left Top · ↑ Center Top · ↗ Right Top
  - ↙ Left Bottom · ↓ Center Bottom · ↘ Right Bottom
- Logos are composited with `contain` scaling into a fixed corner zone

---

### 🔤 Title & Subtitle

Both title and subtitle support:

| Control | Options |
|---|---|
| **Text input** | Free text, max 80 chars (title) / 120 chars (subtitle) |
| **Position** | Left/Center/Right × Top/Bottom + Center Screen |
| **Font** | Bebas Neue, Anton, Oswald, Montserrat, Playfair Display, Roboto, Inter |
| **Size** | Custom numeric input (title: 16–300px, subtitle: 12–200px) |

- Title is rendered in **ALL CAPS** with a red underline accent bar
- Subtitle renders in the selected colour (red accent by default)
- Both are rendered with drop-shadows for readability over any background

---

### 📤 Export
- **Download** button produces a high-resolution **PNG**
- Filename: `groupshot-<ratio>-<timestamp>.png`
- Output resolution matches the selected aspect ratio (1080p+ base)

---

## 🗂 File Structure & Importance

```
group-shot/
├── index.html          ← 🌟 CORE APP — entire frontend UI + canvas renderer
├── server.py           ← 🔧 LOCAL DEV server — run this on Windows to test
├── api/
│   └── process.py      ← 🤖 PYTHON BACKEND — bg removal + face detection API
├── requirements.txt    ← 📦 Python dependencies for Vercel + local install
├── vercel.json         ← 🚀 DEPLOY CONFIG — routes + Python runtime settings
└── README.md           ← 📖 This file
```

### File Descriptions

#### `index.html` — *The entire frontend*
The single-page app. Contains all HTML, CSS, and JavaScript in one file. Key responsibilities:
- UI panels: upload, options, preview
- Sends each photo to `/api/process` (POST, base64 JSON)
- Caches processed results to avoid redundant API calls
- Canvas rendering: background, shape clipping, layout, logos, text
- Download trigger

#### `server.py` — *Local development server (Windows / Mac / Linux)*
A zero-dependency Python HTTP server that serves `index.html` on `localhost:3000` and handles `POST /api/process` by importing and calling the same functions as the Vercel API. Run with:
```bash
python server.py
```
This means you get **identical behaviour locally and on Vercel** — no `vercel dev` or Node.js required.

#### `api/process.py` — *The AI processing backend*
A Vercel-compatible Python HTTP handler (`class handler(BaseHTTPRequestHandler)`). Pipeline:
1. Accepts `{ image: "<base64>", size: 512 }` JSON via POST
2. Removes background using `rembg` + `birefnet-portrait` (best model for people)
3. Cleans alpha mask with OpenCV morphology + Gaussian blur
4. Detects face bounding box via Haar cascade
5. Crops to a face-centred square with configurable padding
6. Returns `{ ok, image: "<base64 PNG>", face_detected, face_box, rembg, cv2 }`

Both `rembg` and `cv2` have graceful fallbacks if not installed.

#### `requirements.txt` — *Python dependencies*
```
rembg==2.0.75              # AI background removal (U2Net / BiRefNet models)
opencv-python-headless==4.13.0.92  # Face detection + alpha mask cleanup
Pillow                     # Image I/O and manipulation
numpy                      # Array operations for mask processing
onnxruntime                # ONNX model runtime (required by rembg)
```
Vercel reads this file and installs everything automatically during deploy.

#### `vercel.json` — *Vercel deployment configuration*
- Routes `POST /api/process` → `api/process.py` (Python serverless function)
- Routes all other paths → static files
- Sets `maxLambdaSize: 50mb` to accommodate rembg ONNX models

---

## 🚀 Running Locally (Windows)

```bash
# 1. Install dependencies (one time)
pip install rembg==2.0.75 opencv-python-headless==4.13.0.92 Pillow numpy onnxruntime

# 2. Start the local server
python server.py

# 3. Open in browser
# http://localhost:3000
```

> ⚠️ First run downloads the BiRefNet model (~200MB) to `~/.u2net/` — this is normal and only happens once.

---

## 🚀 Deploying to Vercel

```bash
# Install Vercel CLI (one time)
npm install -g vercel

# Login
vercel login

# Deploy from project root
vercel --prod
```

Vercel automatically:
- Detects `api/process.py` as a Python serverless function
- Installs all `requirements.txt` packages
- Serves `index.html` as a static file
- Routes `/api/process` → the Python handler

---

## 🎨 Design Theme

Inspired by **vintage sports poster aesthetics**:

| Token | Value | Usage |
|---|---|---|
| Background | `#111410` | App background |
| Surface | `#1a1e18` | Panels |
| Forest Green | `#1b3a2d` | Header, panel headers |
| Deep Red | `#c0392b` | Accents, borders, CTA buttons |
| Cream | `#f0ead6` | Primary text |
| Gray | `#6b7066` | Secondary text, disabled |

**Fonts:** Bebas Neue (display headings) · Oswald (UI labels) · Inter (form inputs)

---

## 📱 Responsive Behaviour

- Two-column layout (controls left, preview right) on screens ≥ 860px
- Single column stacked layout on mobile
- Canvas preview scales to fit viewport width
- All controls accessible on mobile

---

## ⚙️ Technical Notes

- **No framework** — pure vanilla HTML/CSS/JS + Python stdlib
- **Canvas API** used for all rendering (no server-side image composition)
- **Processed images cached** in a `Map` keyed by `file.name + file.size + bgRemoval` — changing bg removal setting clears the cache
- **CORS headers** set on all API responses (`Access-Control-Allow-Origin: *`)
- **Vercel Python runtime** uses Node.js `BaseHTTPRequestHandler` bridge — the same `class handler` pattern works both locally (via `server.py`) and on Vercel
