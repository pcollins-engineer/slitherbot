"""YOLOv8 debug overlay — run a stock COCO-pretrained YOLOv8 on the live frame
and paint whatever it fires, so you can see how (un)useful the default classes
are on slither. Spammy on purpose.

This is the "before" picture motivating fine-tuning: a COCO model only knows
person/car/dog/etc., so on slither it'll mostly mis-fire or stay quiet — which
is the point. Later we swap in a slither-trained model.

Setup:  pip install ultralytics   (already present here)
Run:    python yolov8_debug.py --conf 0.25
        python yolov8_debug.py --model yolov8x.pt --conf 0.15   # bigger / spammier

Keys: Ctrl+C to stop.
"""

import argparse
import asyncio
import colorsys
import ctypes
import threading
import time
from collections import Counter

from bridge import draw_server


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


def cls_color(i: int) -> str:
    r, g, b = colorsys.hsv_to_rgb((i * 0.61803398875) % 1.0, 0.85, 1.0)
    return "#{:02X}{:02X}{:02X}".format(int(r * 255), int(g * 255), int(b * 255))


def extract_dets(result, w, h):
    """Detections as dicts in normalized (0..1) center form."""
    names = result.names
    out = []
    for box in result.boxes:
        cls = int(box.cls[0])
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        out.append({"cls": cls, "name": names[cls], "conf": float(box.conf[0]),
                    "x": (x1 + x2) / 2 / w, "y": (y1 + y2) / 2 / h,
                    "w": (x2 - x1) / w, "h": (y2 - y1) / h})
    return out


def dets_to_shapes(dets):
    return [{
        "kind": "rect", "x": d["x"], "y": d["y"], "w": d["w"], "h": d["h"],
        "color": cls_color(d["cls"]), "label": f"{d['name']} {d['conf']:.2f}", "lineWidth": 2,
    } for d in dets]


class Smoother:
    """EMA-smooths detections frame-to-frame so boxes stop jittering/pulsing.

    Capturing the screen includes our own overlay, which creates a feedback
    loop (the box drifts then snaps back). Smoothing toward a stable estimate
    gives the loop a fixed point and kills the oscillation.
    """

    def __init__(self, alpha=0.35, match=0.06, max_missed=5):
        self.alpha = alpha
        self.match = match            # max normalized center distance to match a track
        self.max_missed = max_missed
        self.tracks = []

    def update(self, dets):
        for t in self.tracks:
            t["seen"] = False
        for d in dets:
            best, bd = None, self.match
            for t in self.tracks:
                if t["cls"] != d["cls"] or t["seen"]:
                    continue
                dist = ((t["x"] - d["x"]) ** 2 + (t["y"] - d["y"]) ** 2) ** 0.5
                if dist < bd:
                    bd, best = dist, t
            if best is None:
                self.tracks.append({**d, "missed": 0, "seen": True})
            else:
                a = self.alpha
                for k in ("x", "y", "w", "h"):
                    best[k] = a * d[k] + (1 - a) * best[k]
                best["conf"], best["name"], best["missed"], best["seen"] = d["conf"], d["name"], 0, True
        for t in self.tracks:
            if not t["seen"]:
                t["missed"] += 1
        self.tracks = [t for t in self.tracks if t["missed"] <= self.max_missed]
        return [t for t in self.tracks if t["missed"] == 0]


def capture_loop(region, fps, model_name, conf, smooth, stop_evt):
    enable_high_dpi()
    import dxcam
    from ultralytics import YOLO

    print(f"loading {model_name} ...")
    model = YOLO(model_name)  # downloads on first use
    print(f"classes the model knows: {len(model.names)} (COCO by default)")

    cam = dxcam.create(output_color="BGR")
    cam.start(region=region, target_fps=fps, video_mode=True)
    smoother = Smoother() if smooth else None
    last = time.perf_counter()
    seen = Counter()
    frames = 0
    hz = 0.0
    try:
        while not stop_evt.is_set():
            frame = cam.get_latest_frame()
            if frame is None:
                continue
            h, w = frame.shape[:2]
            t0 = time.perf_counter()
            result = model.predict(frame, conf=conf, verbose=False)[0]
            dt = time.perf_counter() - t0
            inst = 1.0 / dt if dt > 0 else 0.0
            hz = inst if hz == 0 else 0.9 * hz + 0.1 * inst  # smoothed inference rate
            dets = extract_dets(result, w, h)
            if smoother is not None:
                dets = smoother.update(dets)
            shapes = dets_to_shapes(dets)
            shapes.append({"kind": "text", "x": 0.01, "y": 0.045,
                           "text": f"YOLO {hz:.1f} Hz | {len(dets)} det",
                           "color": "#00ff66", "font": "18px monospace"})
            draw_server.set_shapes(shapes)
            frames += 1
            for d in dets:
                seen[d["name"]] += 1
            if time.perf_counter() - last > 2.0:
                top = ", ".join(f"{n}:{c}" for n, c in seen.most_common(8)) or "(nothing)"
                print(f"  {frames} frames | classes seen so far: {top}")
                last = time.perf_counter()
    finally:
        cam.stop()


def main():
    ap = argparse.ArgumentParser(description="Run stock YOLOv8 on the game and overlay detections.")
    ap.add_argument("--model", default="yolov8n.pt", help="weights (yolov8n/s/m/l/x.pt)")
    ap.add_argument("--conf", type=float, default=0.02,
                    help="confidence threshold (low by default so you can see COCO mis-fire)")
    ap.add_argument("--fps", type=int, default=15)
    ap.add_argument("--region", type=int, nargs=4, metavar=("L", "T", "R", "B"),
                    default=[0, 155, 1920, 1000])
    ap.add_argument("--no-smooth", action="store_true",
                    help="disable temporal smoothing (boxes may pulse due to capture feedback)")
    args = ap.parse_args()

    region = tuple(args.region)
    stop_evt = threading.Event()
    threading.Thread(target=capture_loop,
                     args=(region, args.fps, args.model, args.conf, not args.no_smooth, stop_evt),
                     daemon=True).start()

    print(f"yolov8 debug: {args.model} @ conf {args.conf}, region {region}")
    try:
        asyncio.run(draw_server.serve())
    except KeyboardInterrupt:
        stop_evt.set()
        print("\nstopped.")


if __name__ == "__main__":
    main()
