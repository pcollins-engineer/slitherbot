"""Live overlay producer: capture the game, perceive it, paint real boxes.

Captures the screen (Desktop Duplication), runs the color-filter perceiver,
converts the detections to overlay shapes, and pushes them to the draw server
so the in-page extension overlay paints them on the live game.

This replaces the demo center box. Run THIS instead of bridge/draw_server.py
(it starts the same WS/HTTP transports itself).

    python live_overlay.py --region 0 110 1919 970   # match the game canvas

Coordinate mapping: detection pixels are normalized by the captured region
size, and the overlay maps 0..1 onto the browser viewport. So set --region to
the on-screen rectangle of the game canvas (the browser content area) for the
boxes to line up. Tune it until the boxes sit on the pellets/snakes.

Keys: Ctrl+C to stop.
"""

import argparse
import asyncio
import ctypes
import threading
import time

from bridge import draw_server
from perception.color_filter_perceiver import ColorFilterPerceiver


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


def perception_to_shapes(per, w: int, h: int):
    """Convert a Perception into relative (0..1) overlay rects."""
    shapes = []
    for p in per.pellets:
        shapes.append({"kind": "rect", "x": p.cx / w, "y": p.cy / h,
                       "w": (2 * p.r) / w, "h": (2 * p.r) / h,
                       "color": "#00ff00", "lineWidth": 1})
    for s in per.snakes:
        cx, cy = (s.x + s.w / 2) / w, (s.y + s.h / 2) / h
        if s.is_self:
            shapes.append({"kind": "rect", "x": cx, "y": cy, "w": s.w / w, "h": s.h / h,
                           "color": "#ffff00", "label": "YOU", "lineWidth": 3})
            if s.head is not None:
                hx, hy = s.head
                shapes.append({"kind": "rect", "x": hx / w, "y": hy / h,
                               "w": 26 / w, "h": 26 / h,
                               "color": "#ff00ff", "label": "head", "lineWidth": 2})
        else:
            shapes.append({"kind": "rect", "x": cx, "y": cy, "w": s.w / w, "h": s.h / h,
                           "color": "#ff3030", "label": "enemy", "lineWidth": 3})
    return shapes


def capture_loop(region, filters_dir, fps, stop_evt):
    enable_high_dpi()
    import dxcam

    perceiver = ColorFilterPerceiver(filters_dir)
    if not perceiver.specs:
        print(f"No filters in '{filters_dir}/'. Export some from the GUI first.")
        return
    cam = dxcam.create(output_color="BGR")
    cam.start(region=region, target_fps=fps, video_mode=True)
    n = 0
    last = time.perf_counter()
    try:
        while not stop_evt.is_set():
            frame = cam.get_latest_frame()
            if frame is None:
                continue
            h, w = frame.shape[:2]
            per = perceiver.perceive(frame)
            draw_server.set_shapes(perception_to_shapes(per, w, h))
            n += 1
            if time.perf_counter() - last > 2.0:
                print(f"  streaming: {len(per.pellets)} pellets, {len(per.snakes)} snakes, "
                      f"own={'yes' if per.own else 'no'}")
                last = time.perf_counter()
    finally:
        cam.stop()


def main():
    ap = argparse.ArgumentParser(description="Stream live detections to the overlay.")
    ap.add_argument("--filters", default="filters")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--region", type=int, nargs=4, metavar=("L", "T", "R", "B"),
                    default=None, help="on-screen game-canvas rect; default full screen")
    args = ap.parse_args()

    region = tuple(args.region) if args.region else None
    stop_evt = threading.Event()
    t = threading.Thread(target=capture_loop, args=(region, args.filters, args.fps, stop_evt),
                         daemon=True)
    t.start()

    print(f"live overlay: capturing region {region or 'full screen'} @ {args.fps}fps")
    try:
        asyncio.run(draw_server.serve())  # no demo ticker; capture thread feeds shapes
    except KeyboardInterrupt:
        stop_evt.set()
        print("\nstopped.")


if __name__ == "__main__":
    main()
