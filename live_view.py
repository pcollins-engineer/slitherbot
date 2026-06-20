"""Read-only live perception view (Phase 2 of the controller plan).

Captures the screen via Desktop Duplication, runs the color-filter perceiver
on every frame, and draws the result live. NO control is sent — this is
purely to confirm pellet/snake detection and the own-head heuristic hold up
in motion before closing the loop.

Run (full screen):
    python live_view.py

Run a sub-region (left top right bottom) — recommended, point it at the game:
    python live_view.py --region 0 110 1919 970

Keys:  q or Esc to quit.
"""

import argparse
import ctypes
import time

import cv2

from perception.color_filter_perceiver import ColorFilterPerceiver
from perception.overlay import draw, hud


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


def main():
    ap = argparse.ArgumentParser(description="Read-only live perception view.")
    ap.add_argument("--filters", default="filters")
    ap.add_argument("--fps", type=int, default=60, help="target capture fps")
    ap.add_argument("--region", type=int, nargs=4, metavar=("L", "T", "R", "B"),
                    default=None, help="capture sub-region; default full screen")
    ap.add_argument("--scale", type=float, default=1.0, help="display window scale")
    args = ap.parse_args()

    enable_high_dpi()
    perceiver = ColorFilterPerceiver(args.filters)
    if not perceiver.specs:
        print(f"No filters in '{args.filters}/'. Export some from the GUI first.")
        return
    print("perceiver backend: color filters (" +
          ", ".join(f"{s.name}:{s.kind}" for s in perceiver.specs) + ")")

    import dxcam
    cam = dxcam.create(output_color="BGR")
    region = tuple(args.region) if args.region else None
    cam.start(region=region, target_fps=args.fps, video_mode=True)

    win = "slitherbot live (read-only)  -  q/esc to quit"
    fps_ema = None
    prev = time.perf_counter()
    try:
        while True:
            frame = cam.get_latest_frame()
            if frame is None:
                continue

            per = perceiver.perceive(frame)
            vis = draw(frame, per)

            now = time.perf_counter()
            dt = now - prev
            prev = now
            inst = 1.0 / dt if dt > 0 else 0.0
            fps_ema = inst if fps_ema is None else 0.9 * fps_ema + 0.1 * inst
            own = "yes" if per.own else "no"
            hud(vis, f"{fps_ema:4.1f} fps | pellets {len(per.pellets):3d} | "
                     f"snakes {len(per.snakes)} | own head: {own}  [READ-ONLY]")

            if args.scale != 1.0:
                vis = cv2.resize(vis, None, fx=args.scale, fy=args.scale,
                                 interpolation=cv2.INTER_AREA)
            cv2.imshow(win, vis)
            if (cv2.waitKey(1) & 0xFF) in (27, ord("q")):
                break
    finally:
        cam.stop()
        del cam
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
