"""Single-file Desktop Duplication capture test.

Purpose: prove the Windows Desktop Duplication API returns a *real*
(non-black) frame when the process is DPI-aware. It grabs ONE full-desktop
frame, saves it to a PNG, prints whether it looks black, and exits.

Why this exists: on a scaled display, a process that is NOT DPI-aware sees a
virtualized / offset desktop, so the duplicated frame comes back all black
(or shifted). The fix is to set DPI awareness *before* capturing — which is
the first thing this script does.

Requires:
    pip install dxcam      # dxcam wraps the DXGI Desktop Duplication API
    pip install pillow     # already a project dep; used to save the PNG

Run:
    python dd_capture_test.py
"""

import ctypes
import sys
import time


def enable_high_dpi() -> str:
    """Make this process per-monitor DPI-aware BEFORE any capture happens.

    Tries the most modern API first and falls back. Returns a label of what
    actually took effect (for the printout).
    """
    # Windows 10 1703+: DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 == -4
    try:
        if ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
            return "SetProcessDpiAwarenessContext(PER_MONITOR_AWARE_V2)"
    except Exception:
        pass
    # Windows 8.1+: PROCESS_PER_MONITOR_DPI_AWARE == 2
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return "SetProcessDpiAwareness(PER_MONITOR)"
    except Exception:
        pass
    # Vista+: system-DPI aware (last resort)
    try:
        ctypes.windll.user32.SetProcessDPIAware()
        return "SetProcessDPIAware()"
    except Exception:
        return "DPI awareness NOT set (all calls failed)"


def main():
    if sys.platform != "win32":
        print("This test only runs on Windows.")
        return

    # MUST run before creating the duplication, or frames can be black/offset.
    print(f"DPI awareness: {enable_high_dpi()}")

    try:
        import dxcam
    except ImportError:
        print("dxcam not installed.  Run:  pip install dxcam")
        return

    # output_idx defaults to the primary monitor; the whole desktop is captured.
    cam = dxcam.create(output_color="RGB")

    # grab() returns None if no *new* frame is ready yet — retry briefly.
    frame = cam.grab()
    for _ in range(10):
        if frame is not None:
            break
        time.sleep(0.05)
        frame = cam.grab()
    del cam  # release the duplication

    if frame is None:
        print("grab() returned None (no frame ready). Move the mouse and rerun.")
        return

    h, w = frame.shape[:2]
    mean = float(frame.mean())
    verdict = "LIKELY BLACK [X]" if mean < 1.0 else "looks OK [OK]"
    print(f"captured {w}x{h}, mean brightness = {mean:.1f}  ({verdict})")

    from PIL import Image
    out = "dd_capture_test.png"
    Image.fromarray(frame).save(out)
    print(f"saved -> {out}")


if __name__ == "__main__":
    main()
