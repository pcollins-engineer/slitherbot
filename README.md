# 🐍 Slither.io Color Filter + Eyedropper GUI + YOLO Precursor Tool

## 🎯 Project Goal

Build a Python GUI tool that helps prepare training data for a YOLO‑backboned neural net to detect Slither.io entities (snake heads, bodies, pellets, etc.).
This precursor tool focuses on color‑based filtering, pixel sampling, and visual inspection of screenshots before moving to full YOLO annotation and training.

---

## 🧩 Components Overview

- Color Filter Engine
  Applies HSV/RGB thresholding to Slither.io screenshots to isolate target objects (snake head, pellets, etc.).

- Eyedropper Tool
  GUI lets you hover/click pixels to read RGB/HSV values, helping you tune filters.

- Screenshot Loader
  Loads PNG/JPG frames from disk for inspection.

- Preview Panel
  Shows original and filtered image side‑by‑side.

- Export Settings
  Saves chosen HSV/RGB ranges to JSON for later YOLO preprocessing.

---

## 🏗️ Tech Stack

- Python 3.10+
- OpenCV (cv2)
- Tkinter (standard library)
- Pillow (PIL) for image → Tk conversion
- NumPy
- JSON for saving filter configs

---

## 🔧 Features (Spec)

### 1. Color Eyedropper

- Click on the image to sample a pixel.
- Display:
  - RGB
  - HSV
  - Hex
  - Pixel coordinates
- Maintain a small “recent colors” list.

### 2. Color Filter Controls

- HSV sliders:
  - H min/max
  - S min/max
  - V min/max
- Real‑time preview:
  - Mask view (binary)
  - Mask‑applied view (original × mask)
- Toggle between views with radio buttons.

### 3. Screenshot Browser

- Folder picker dialog.
- Next/Prev buttons.
- Keyboard shortcuts: Left/Right arrows to change image.

### 4. Export

- Save current HSV ranges to JSON files in `filters/`:
  - `slither_body.json` — the snake bodies (and heads; see note)
  - `slither_pellet.json` — the food dots
  - `slither_head.json` — *optional* (see note)
- JSON format:
  ```json
  {
    "h_min": 0,
    "h_max": 20,
    "s_min": 120,
    "s_max": 255,
    "v_min": 150,
    "v_max": 255
  }
  ```
- The auto-labeler infers each filter's **entity kind from its filename** (`body`, `pellet`, `head`, or `boost`/`orb`), so keep those words in the names.
- **Note on heads:** a snake's head is usually the *same color* as its body, so it generally can't be isolated by color alone. In practice you export a `body` filter and the pipeline derives head/tail geometrically from the body skeleton. A separate `head` filter only helps if heads are visually distinct (e.g. a different skin) — otherwise skip it.
- **Note on pellets:** food dots come in many hues, so the most robust pellet filter is **full hue (0–179) gated by saturation + value** rather than one filter per color. Keep the saturation floor above the snakes' saturation so the filter doesn't grab the snake bodies.

---

## 📁 Project Structure

The single‑file skeleton has been factored into runnable modules:

```
slither-io-feature-extraction/
│
├── main.py                  # GUI entry point: `python main.py`
├── preprocess.py            # auto-labeler CLI: `python preprocess.py`
├── demo_annotate.py         # draw labeled boxes per object (visual demo)
├── dd_capture_test.py       # Desktop Duplication capture smoke test (DPI-aware)
├── requirements.txt
│
├── gui/                     # Tkinter color-filter + eyedropper tool
│   ├── __init__.py
│   ├── main_gui.py          # SlitherColorToolApp — wires everything together
│   ├── eyedropper.py        # pixel sampling + canvas→image coordinate mapping
│   ├── sliders.py           # reusable labeled HSV slider widget
│   └── preview_panel.py     # OpenCV image → Tk PhotoImage conversion
│
├── core/                    # GUI-independent logic
│   ├── __init__.py
│   ├── color_filter.py      # ColorFilter (HSV thresholding)
│   ├── screenshot_loader.py # ScreenshotLoader (folder navigation)
│   └── export_json.py       # FilterExporter (save HSV ranges to JSON)
│
├── pipeline/                # auto-label preprocessing (used by preprocess.py)
│   ├── __init__.py
│   ├── config.py            # class map, Settings, filter loading
│   ├── blobs.py             # connected components → pellet/head/orb boxes
│   ├── body.py              # body sausage → centerline circle-chain + head/tail
│   ├── skeleton.py          # Zhang-Suen thinning + centerline path walk
│   ├── grid.py              # background-lattice pitch estimation (FFT)
│   ├── screen_model.py      # parametric per-frame scene summary
│   ├── yolo_export.py       # write YOLO labels + data.yaml
│   └── overlay.py           # debug visualization
│
├── filters/                 # exported JSON filter configs (gitignored)
├── screenshots/             # *.png / *.jpg frames to inspect
├── dataset/                 # auto-labeler output (images/labels/overlays/...)
└── README.md
```

The `pipeline/` package depends only on `opencv-python` + `numpy` (skeletonization is implemented in-house, so no `scikit-image` / `opencv-contrib` is required).

---

## 🚀 How to Run

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
   (equivalently: `pip install opencv-python pillow numpy`)

2. Put some Slither.io screenshots into the `screenshots/` folder (PNG/JPG).

3. Run from the project root:
   ```
   python main.py
   ```

   > Run from the project root so the `core`, `gui`, and `pipeline` packages resolve.

4. Tune filters in the GUI (eyedropper + sliders), export them to `filters/`, then run the auto-labeler:
   ```
   python preprocess.py
   ```
   See [Running the auto-labeler](#running-the-auto-labeler) for the full workflow.

**Two-phase workflow:** `main.py` (interactive) is where you *tune and export* color filters; `preprocess.py` (batch) *consumes* those filters to auto-label frames into a YOLO dataset.

---

## 📸 Capturing Gameplay Screenshots

### To test the feature extractors: one rich frame is enough

You don't need a labeled dataset to validate the color-filter / extraction pipeline — you need **one information-dense frame** that contains every entity type at once. Drop it in `screenshots/` and tune the HSV filters against it. A good "rich" frame has:

- **Your own snake** — head, full visible trail, and tail in view.
- **At least one enemy snake** in view. (Heads-up: snakes often share a color — e.g. two cyan snakes — so don't rely on hue alone to tell snakes apart; see "Lessons" below.)
- **A dense pellet field** — lots of small food dots in a variety of colors.
- **A boost orb / dead-snake remains** if one is on screen (optional class).
- **The background lattice clearly visible** (the faint hexagonal pattern, used for scale/localization).

That single frame exercises body skeletonization, head/tail estimation, pellet blob detection, the size estimator, and lattice-pitch estimation. No bounding boxes needed at this stage — the color filters are tuned by eye with the eyedropper.

> **Crop to the game viewport.** A full-screen capture includes the browser chrome and the OS taskbar, whose colorful icons cause false detections. Crop to just the game canvas before saving the frame (the saturation-gated pellet filter will otherwise pick up taskbar/tab icons).

### For actual YOLO training: scale up via auto-labeling

- **~1 rich frame** to validate the extractors work.
- **~50–200 varied frames** for a usable v0 model — but these get *auto-labeled* by the pipeline (color filter → connected components → YOLO labels), so you only hand-correct mistakes rather than label from scratch. Then retrain (active learning).
- Vary zoom level, snake density, and color themes across frames so the model generalizes.

### Realtime capture (later): Windows Desktop Duplication API

For live frames instead of static screenshots, plan to use the **DXGI Desktop Duplication API** (`IDXGIOutputDuplication`).

> ⚠️ **Gotcha — enable high-DPI mode first.** The capturing process **must be DPI-aware** before it duplicates the desktop. On a scaled display, a non-DPI-aware process sees a virtualized/offset desktop and the captured frame comes back **all black (or shifted) due to the coordinate offset**. Call `SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2)` (or `SetProcessDpiAwareness(PROCESS_PER_MONITOR_DPI_AWARE)`) at startup, before creating the duplication.

**Smoke test:** `dd_capture_test.py` is a single-file check — it sets DPI awareness, grabs one full-desktop frame via the Desktop Duplication API, saves it to `dd_capture_test.png`, and prints the mean brightness so you can confirm it isn't black:

```bash
pip install dxcam            # wraps the DXGI Desktop Duplication API (Windows only)
python dd_capture_test.py    # -> "captured WxH, mean brightness = N (looks OK)"
```

If it ever prints `LIKELY BLACK`, the DPI-awareness call isn't taking effect early enough.

---

## 🤖 YOLO Fine‑Tuning Plan

This precursor tool produces the color filters and auto‑proposed labels that feed a fine‑tuned YOLO model. The plan below targets **Ultralytics YOLOv8x** (the largest v8 model — best accuracy, and the variant we've had good results with on a prior project).

### Model choice & task

Slither.io has three structurally different targets, and a single plain‑detection model is a poor fit for all of them:

| Target | Shape | Best YOLOv8 task |
| --- | --- | --- |
| Snake head | small, compact blob | detection (tight bbox) |
| Pellets / food | small circles | detection (tight bbox) |
| Snake body | long, curved, variable‑length "sausage" | **segmentation** (or pose/keypoints along the spine) |

Recommended setup: **`yolov8x-seg`** (instance segmentation). Heads and pellets train fine as detection boxes, and segmentation captures the curved body mask exactly — which a single axis‑aligned box cannot. If you'd rather keep it pure‑detection, model the body as a *chain of short segment boxes* rather than one giant box (see below).

### Should the bounding box be the whole snake or just the head?

**Just the head — plus the body as its own thing.** Here's the reasoning:

- **One bbox around an entire snake is useless.** A long snake's axis‑aligned box covers most of the screen, is mostly empty, and overlaps every other snake's box → terrible IoU, terrible NMS behavior, terrible training signal.
- **The head is the high‑value, well‑defined target.** It's compact, roughly circular, and is what you actually need for collision avoidance and targeting. Detect it as a tight box and give it its own class (`snake_head`). (Splitting `snake_head` into enemy-vs-self by *color* won't work when snakes share a color — use the minimap or camera-center cue instead.)
- **The body is a "sausage," so represent it as one.** Your instinct is right: the body is the head circle plus an effectively infinite trail of overlapping circles down to the tail. Two good ways to encode that:
  1. **Segmentation mask (recommended):** YOLOv8‑seg outputs the polygon/mask of the whole trail. This *is* the sausage — no need to discretize it.
  2. **Capsule / circle chain (detection‑only fallback):** sample the body centerline (head → tail) as a polyline of circle centers with a **minimum spacing** (e.g. ≥ 0.5–1× body radius between samples) so circles overlap into a continuous capsule but you don't emit a detection for every pixel. Each sample becomes a small `body_segment` box of the snake's local thickness. The tail gets its own `snake_tail` class so length/orientation are recoverable.

### Proposed classes

```
0  snake_head        # tight box, compact
1  snake_tail        # endpoint of the trail
2  body_segment      # circle/capsule link between head and tail (detection mode)
3  pellet            # food dots
4  boost_orb         # the larger glowing remains of a dead snake (optional)
```

In segmentation mode, classes 0/1/3/4 stay as above and the body becomes a single `snake_body` mask instance per snake instead of class 2.

### Auto‑label pipeline (how this tool feeds YOLO)

The exported HSV filters drive `preprocess.py` (implemented — this is the v0 auto-labeler in `pipeline/`):

1. **Color filter** each frame with the saved `filters/*.json` ranges. Each filter's entity kind is read from its filename. Pellets are best caught by one **full-hue, saturation/value-gated** filter (food comes in many colors); each snake-body filter targets one snake color.
2. **Connected components** on each mask:
   - pellet / head / boost-orb masks → one tight box per blob;
   - body mask → snake-body instances (after a morphological *close* so anti-aliased gaps don't split one snake into several).
3. **Body → centerline:** skeletonize the body blob (in-house Zhang-Suen thinning), walk the skeleton end→end, and emit circle centers at a minimum spacing tied to local thickness. The distance-transform value at each center gives the **circle radius = body thickness** → this doubles as a **size estimator** (snake length ≈ Σ spacing; girth ≈ radius, which correlates with score).
4. **Head / tail:** the two skeleton endpoints become `snake_head` and `snake_tail`. ⚠️ Because the head is the *same color* as the body, orientation (which end is the head) can't be decided by the body color alone — if a `head` filter or an eye detector is available the pipeline orients toward it, otherwise the head/tail assignment is a best guess. **Distinguishing head from tail (e.g. by detecting the eyes) is a known TODO.**
5. **Lattice pitch for localization:** the faint background is a fixed-pitch **hexagonal** lattice (not a square grid). `grid.py` estimates its dominant spatial period via FFT to recover an approximate pixels-per-world-unit scale. A hex-aware (Hough / phase-correlation) refinement is a TODO; the current value is approximate.
6. **Physics / parametric screen model (OpenSCAD‑style):** each frame gets a compact `screen_model/*.json` — image size, lattice pitch, entity counts and poses — as a geometric scene summary that's easy to sanity-check and feed downstream agents. Zoom/minimap/self-snake solvers extend the model's `extra` field (TODO).
7. **Export YOLO labels:** writes `dataset/images/` + `dataset/labels/*.txt` (normalized `cls cx cy w h`), a `dataset/data.yaml` listing the classes, plus `dataset/overlays/` (visual QA) and `dataset/screen_model/`.

### Running the auto-labeler

```bash
# defaults: filters/ + screenshots/ -> dataset/
python preprocess.py
python preprocess.py --no-grid              # skip lattice estimation
python preprocess.py --out runs/v0          # choose output dir
python preprocess.py --min-pellet-area 12   # tune noise thresholds
```

The emitted labels are **v0 proposals** — open `dataset/overlays/` to eyeball them, load `dataset/` into a YOLO labeling tool, correct mistakes, then train.

### Quick visual demo

For a human-readable picture of what's detected (one labeled box per whole object, instead of the YOLO body-segment chain):

```bash
python demo_annotate.py                         # annotate everything in screenshots/
python demo_annotate.py screenshots/blue_enemy.png
```

This writes `dataset/demo/<name>_annotated.png` with red boxes labeled `snake` / `pellet` / `orb`. It applies a roundness filter so thin UI text (leaderboard, score) isn't mistaken for pellets, and requires a snake-sized blob so stray fragments aren't labeled snakes. Snakes are labeled just `snake` — mine-vs-enemy isn't resolved yet (see the controller plan).

**Results on the first real frame (`blue_enemy.png`):** both snakes boxed perfectly, plus most pellets — a clean proof the color-filter perception works end to end.

**Known limitation — dim / purple pellets are under-detected.** Some pellets (notably purple/violet ones, and faint ones) fall below the pellet filter's saturation/value floor and get missed. This is a filter-tuning gap, not a pipeline bug — options:
- lower `s_min` / `v_min` in `filters/slither_pellet.json` (watch for more UI/background noise creeping in), or
- run a **second pellet filter** tuned for the dim/purple hue band (the auto-labeler merges detections from all `*pellet*` filters), or
- once trained, the YOLO model should pick these up from labeled examples better than a fixed threshold.

### Lessons from the first real frame

Tuning against a real screenshot changed a few earlier assumptions — captured here so the plan stays honest:

- **Snakes can share a color.** The first frame had two cyan snakes (player + enemy). Color filtering finds *snake-colored pixels*, not *individual snakes*; same-color snakes are only separated when they don't touch. Telling player from enemy needs another cue (the minimap, or "the snake centered under the camera is you").
- **Heads aren't color-separable** from their own body → head/tail come from skeleton geometry, and orientation needs the eyes (TODO). The earlier "color-filter the head" idea only works for visually distinct heads.
- **The background is hexagonal**, so "grid" means a hex lattice; pitch is estimated by FFT and is approximate.
- **Bodies fragment** under anti-aliasing/shading; a morphological close before component labeling was needed to keep one snake as one instance.
- **Full-screen captures leak UI** (browser chrome, taskbar) into the saturated-pellet filter → crop to the game canvas.

### Training (sketch)

```bash
# data.yaml points at images/ + labels/ and lists the class names
yolo detect train  model=yolov8x.pt     data=data.yaml epochs=100 imgsz=1280  # boxes-only
# or, recommended for the sausage body:
yolo segment train model=yolov8x-seg.pt data=data.yaml epochs=100 imgsz=1280
```

Notes:
- Start from COCO‑pretrained `yolov8x*.pt` and fine‑tune; the auto‑proposed labels get you a v0 model fast, then hand‑correct its mistakes and retrain (active learning).
- Use a larger `imgsz` (1024–1280): pellets are tiny and shrink under downscaling.
- Heavy augmentation hurts here (the game has a consistent look) — keep color jitter modest so it doesn't fight the hue‑based class separation.

---

## 🎮 Autonomous Controller (Plan — not yet implemented)

The end goal: a simple **reactive** bot that hunts pellets and avoids enemy snake heads. Deliberately start dumb — **no localization / world map** — just react to what's on screen.

### Loop: perceive → decide → act

```
            ┌───────────────────────── Python ─────────────────────────┐
  Chrome    │  Desktop Duplication API → frame → perception (color      │
 (slither)  │  filters / YOLO) → policy (seek pellets, avoid heads)      │
     ▲      │                              │                             │
     │      └──────────────────────────────┼─────────────────────────────┘
     │                                      │  WebSocket  { angle, boost }
     │   synthetic in-page input            ▼
     └──────────  injected JS in the game page (devtools / userscript) ◀──
```

1. **Capture (Python).** Desktop Duplication API grabs the Chrome window framebuffer. ⚠️ make the process DPI-aware first (see [capture section](#realtime-capture-later-windows-desktop-duplication-api)) or frames come back black.
2. **Perceive (Python).** Run the color filters (later the YOLO model) on each frame → pellet positions, enemy snake-head positions, and **your own head**. Own-head heuristic: it's the snake nearest **screen center** — slither.io keeps your head centered, so this needs *no* localization.
3. **Decide (Python).** A reactive policy outputs a desired heading + boost flag, all relative to screen center:
   - attraction vector toward the nearest / densest pellet cluster (reward),
   - repulsion vector away from any enemy head inside a danger radius (avoid),
   - `boost` only when safe and chasing — boosting burns length.
   - desired heading = weighted sum(attraction, repulsion).
4. **Act (WebSocket → in-page JS).** Python sends `{angle, boost}` over a WebSocket to a small JS client injected into the game page. The JS drives the game's **own input inside the page** — it does **not** move your real OS mouse/keyboard, so you can watch and override.

### Why WebSocket + in-page JS (not OS-level input emulation)

- Doesn't hijack your physical mouse/keyboard — the browser stays usable and you can take over instantly.
- Runs inside the page, so it sets exactly what the game reads.
- slither.io steers toward the mouse position **relative to your (centered) head** and boosts on mouse-down / space. Cleanest hook: each tick, set the game's internal mouse-target globals (commonly `window.xm` / `window.ym` = target offset from screen center) and toggle the boost state — rather than dispatching low-level OS events. Fall back to synthetic `mousemove` / `mousedown` events on the game canvas if those globals aren't reachable.

### Components to build

- `capture/` — DPI-aware Desktop Duplication frame grabber.
- `agent/policy.py` — pure function `detections → {angle, boost}` (the seek/avoid logic; unit-testable offline).
- `bridge/server.py` — Python WebSocket server pushing commands at the frame rate.
- `bridge/inject.js` — paste-into-console / userscript client: connect to the WS and apply `{angle, boost}` to the game every animation frame.

### Phasing

1. **Offline perception (now).** ✅ Validate detection on static frames (this repo: `preprocess.py`, `demo_annotate.py`).
2. **Read-only live.** Capture + perceive live and draw an overlay, **no control** — confirm own-head + pellet/head detection hold up in motion.
3. **Closed loop.** Add the WebSocket bridge + in-page input; start with **pellet-seeking only**.
4. **Avoidance.** Add enemy-head repulsion, then opportunistic boosting.
5. **Later.** Swap color filters for the YOLO model; add real localization (hex lattice / minimap) for path planning.

> ⚖️ This automates a third-party browser game — keep it to personal experimentation / research and respect the game's terms of service.

---

> **Status:**
> - ✅ GUI color-filter + eyedropper tool (`main.py`)
> - ✅ Auto-label preprocessing pipeline (`preprocess.py`) → YOLO labels, overlays, screen model
> - ✅ Labeled visual demo (`demo_annotate.py`)
> - ⬜ Head/tail orientation via eye detection; mine-vs-enemy via camera-center cue
> - ⬜ Hex-aware lattice solver + world-coordinate tracking across frames
> - ⬜ Realtime capture (Desktop Duplication API) + WebSocket/in-page-JS control bridge
> - ⬜ Reactive controller (seek pellets, avoid heads) and YOLO training scripts
