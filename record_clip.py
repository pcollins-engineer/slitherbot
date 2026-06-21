"""Record a gameplay clip to a folder of JPG frames (for labeling / training).

    python record_clip.py --seconds 20 --fps 15

Frames go to clips/<timestamp>/frame_XXXXX.jpg. A writer-thread pool keeps
disk I/O off the capture loop. Region defaults to the tuned game canvas.
"""

import argparse
import ctypes
import os
import queue
import threading
import time


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
    ap = argparse.ArgumentParser(description="Record a gameplay clip.")
    ap.add_argument("--seconds", type=float, default=20.0)
    ap.add_argument("--fps", type=int, default=15)
    ap.add_argument("--region", type=int, nargs=4, metavar=("L", "T", "R", "B"),
                    default=[0, 155, 1920, 1000])
    ap.add_argument("--out", default=None, help="output dir (default clips/<timestamp>)")
    args = ap.parse_args()

    enable_high_dpi()
    import cv2
    import dxcam

    out = args.out or os.path.join("clips", time.strftime("%Y%m%d_%H%M%S"))
    os.makedirs(out, exist_ok=True)

    STOP = object()
    q = queue.Queue(maxsize=400)

    def writer():
        while True:
            item = q.get()
            if item is STOP:
                q.task_done(); break
            idx, frame = item
            cv2.imwrite(os.path.join(out, f"frame_{idx:05d}.jpg"), frame,
                        [cv2.IMWRITE_JPEG_QUALITY, 92])
            q.task_done()

    threads = [threading.Thread(target=writer, daemon=True) for _ in range(6)]
    for t in threads:
        t.start()

    cam = dxcam.create(output_color="BGR")
    cam.start(region=tuple(args.region), target_fps=args.fps, video_mode=True)
    print(f"recording {args.seconds}s @ {args.fps}fps -> {out}")

    start = time.perf_counter()
    i = 0
    while time.perf_counter() - start < args.seconds:
        frame = cam.get_latest_frame()
        if frame is None:
            continue
        q.put((i, frame))
        i += 1
    cam.stop()

    for _ in threads:
        q.put(STOP)
    for t in threads:
        t.join()
    print(f"done: {i} frames in {out}")


if __name__ == "__main__":
    main()
