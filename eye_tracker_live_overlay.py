"""Eye-tracking live overlay — find snake HEADS by their eyes and draw a
labeled box + a gaze arrow over each, on the live game.

Like live_overlay.py, but heads only (no pellets). For each head it draws:
  - a bounding box, colored with the snake's own color,
  - an arrow inside the box pointing in the eye/heading direction,
  - a label: snake color name + a size estimate.

Why eyes: a snake's eyes are white on EVERY snake, so detecting them finds
heads regardless of the snake's body color (no per-color filter needed). The
snake's color is then sampled from the pixels around the head for the label.

Run:
    python eye_tracker_live_overlay.py --region 0 155 1920 1000

Keys: Ctrl+C to stop.
"""

import argparse
import asyncio
import ctypes
import math
import threading
import time

import cv2
import numpy as np

from bridge import draw_server

# ---- tunables ----
EYE_V_MIN = 210       # eyes are bright (white sclera)
EYE_S_MAX = 20        # ...and low saturation
EYE_AREA_MIN = 3
EYE_AREA_MAX = 140
EYE_MIN_SEP = 5       # px between the two eyes of one head
EYE_MAX_SEP = 60
BG_LEVEL = 60         # grayscale below this is treated as dark background


def enable_high_dpi():
    for call in (
        lambda: ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)),
        lambda: ctypes.windll.shcore.SetProcessDpiAwareness(2),
        lambda: ctypes.windll.user32.SetProcessDPIAware(),
    ):
        try:
            call(); return
        except Exception:
            continue


def color_name(b, g, r):
    h, s, v = cv2.cvtColor(np.uint8([[[b, g, r]]]), cv2.COLOR_BGR2HSV)[0][0]
    if v < 60:
        return "black"
    if s < 40:
        return "white" if v > 170 else "gray"
    hue = int(h)
    table = [(8, "red"), (22, "orange"), (33, "yellow"), (78, "green"),
             (100, "cyan"), (130, "blue"), (150, "purple"), (167, "pink"), (179, "red")]
    for hi, name in table:
        if hue <= hi:
            return name
    return "red"


def find_eyes(hsv):
    """Return list of (cx, cy, area) for eye-like bright low-sat blobs."""
    white = cv2.inRange(hsv, (0, 0, EYE_V_MIN), (179, EYE_S_MAX, 255))
    n, _l, stats, cent = cv2.connectedComponentsWithStats(white, connectivity=8)
    eyes = []
    for i in range(1, n):
        a = int(stats[i, cv2.CC_STAT_AREA])
        if not (EYE_AREA_MIN <= a <= EYE_AREA_MAX):
            continue
        w = int(stats[i, cv2.CC_STAT_WIDTH]); h = int(stats[i, cv2.CC_STAT_HEIGHT])
        if w == 0 or h == 0 or max(w, h) / min(w, h) > 2.2:
            continue
        eyes.append((float(cent[i][0]), float(cent[i][1]), a))
    return eyes


def pair_eyes(eyes):
    """Greedily pair nearby eyes into heads. Returns [(mx, my, sep, (e1, e2))]."""
    cand = []
    for i in range(len(eyes)):
        for j in range(i + 1, len(eyes)):
            d = math.hypot(eyes[i][0] - eyes[j][0], eyes[i][1] - eyes[j][1])
            if EYE_MIN_SEP <= d <= EYE_MAX_SEP:
                ar = eyes[i][2] / max(1, eyes[j][2])
                if 0.4 <= ar <= 2.5:  # similar-sized eyes
                    cand.append((d, i, j))
    cand.sort()
    used = set()
    heads = []
    for d, i, j in cand:
        if i in used or j in used:
            continue
        used.add(i); used.add(j)
        mx = (eyes[i][0] + eyes[j][0]) / 2
        my = (eyes[i][1] + eyes[j][1]) / 2
        heads.append((mx, my, d, (eyes[i], eyes[j])))
    return heads


def forward_direction(gray, mx, my, sep, eye_vec):
    """Heading = perpendicular to the eye line, pointing AWAY from the body.

    The body trail is brighter than the dark background; sample a ring around
    the head, find the direction of the body mass, and face the opposite way,
    snapped to the eye-line perpendicular.
    """
    H, W = gray.shape
    R = max(8.0, sep * 2.2)
    sx = sy = 0.0
    for k in range(16):
        a = 2 * math.pi * k / 16
        px = int(mx + R * math.cos(a)); py = int(my + R * math.sin(a))
        if 0 <= px < W and 0 <= py < H:
            wgt = max(0, int(gray[py, px]) - BG_LEVEL)
            sx += wgt * math.cos(a); sy += wgt * math.sin(a)
    body_ang = math.atan2(sy, sx) if (sx or sy) else 0.0
    fwd = body_ang + math.pi  # away from body

    # snap to the two perpendiculars of the eye line; pick the closer one
    base = math.atan2(eye_vec[1], eye_vec[0])
    best, bestd = fwd, 9
    for perp in (base + math.pi / 2, base - math.pi / 2):
        d = abs(math.atan2(math.sin(perp - fwd), math.cos(perp - fwd)))
        if d < bestd:
            bestd, best = d, perp
    return best


def sample_color(bgr, mx, my, sep):
    """Median snake color near the head, excluding eyes (white) and bg (dark)."""
    H, W = bgr.shape[:2]
    r = int(max(6, sep * 1.3))
    x0, x1 = max(0, int(mx) - r), min(W, int(mx) + r)
    y0, y1 = max(0, int(my) - r), min(H, int(my) + r)
    patch = bgr[y0:y1, x0:x1].reshape(-1, 3)
    if len(patch) == 0:
        return (200, 200, 200)
    br = patch.max(axis=1).astype(int)
    mn = patch.min(axis=1).astype(int)
    keep = (br > BG_LEVEL) & ((br - mn) > 25)  # not background, not gray/white
    sel = patch[keep] if keep.any() else patch
    b, g, r_ = np.median(sel, axis=0).astype(int)
    return int(b), int(g), int(r_)


def perceive_heads(bgr):
    """Return overlay shapes (rect + arrow) for every detected head."""
    H, W = bgr.shape[:2]
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    heads = pair_eyes(find_eyes(hsv))

    shapes = []
    for mx, my, sep, (e1, e2) in heads:
        eye_vec = (e2[0] - e1[0], e2[1] - e1[1])
        ang = forward_direction(gray, mx, my, sep, eye_vec)
        b, g, r = sample_color(bgr, mx, my, sep)
        hexc = "#{:02X}{:02X}{:02X}".format(r, g, b)
        name = color_name(b, g, r)

        box = sep * 2.4          # head box size in px
        size_px = int(sep * 2.0)  # crude size estimate (head girth)

        shapes.append({
            "kind": "rect",
            "x": mx / W, "y": my / H, "w": box / W, "h": box / H,
            "color": hexc, "label": f"{name} ~{size_px}px", "lineWidth": 2,
        })
        L = box * 0.75
        shapes.append({
            "kind": "arrow",
            "x1": mx / W, "y1": my / H,
            "x2": (mx + L * math.cos(ang)) / W, "y2": (my + L * math.sin(ang)) / H,
            "color": hexc, "lineWidth": 2,
        })
    return shapes


def capture_loop(region, fps, stop_evt):
    enable_high_dpi()
    import dxcam
    cam = dxcam.create(output_color="BGR")
    cam.start(region=region, target_fps=fps, video_mode=True)
    last = time.perf_counter()
    try:
        while not stop_evt.is_set():
            frame = cam.get_latest_frame()
            if frame is None:
                continue
            shapes = perceive_heads(frame)
            draw_server.set_shapes(shapes)
            if time.perf_counter() - last > 2.0:
                print(f"  heads: {sum(1 for s in shapes if s['kind']=='rect')}")
                last = time.perf_counter()
    finally:
        cam.stop()


def main():
    ap = argparse.ArgumentParser(description="Eye-tracking head overlay.")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--region", type=int, nargs=4, metavar=("L", "T", "R", "B"),
                    default=[0, 155, 1920, 1000], help="on-screen gameplay rect")
    args = ap.parse_args()

    region = tuple(args.region)
    stop_evt = threading.Event()
    threading.Thread(target=capture_loop, args=(region, args.fps, stop_evt), daemon=True).start()

    print(f"eye-tracker overlay: capturing {region} @ {args.fps}fps")
    try:
        asyncio.run(draw_server.serve())
    except KeyboardInterrupt:
        stop_evt.set()
        print("\nstopped.")


if __name__ == "__main__":
    main()
