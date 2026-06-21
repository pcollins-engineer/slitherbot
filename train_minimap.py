"""Fine-tune YOLOv8 to detect the slither minimap (a one-class demo).

Stock COCO YOLO fires "clock" on the minimap; here we teach it the real class
"minimap". Fully automatic: it auto-labels a recorded clip (the minimap is at a
fixed spot, found via Hough circle), builds a YOLO dataset, and trains.

    python train_minimap.py                       # uses newest clips/* folder
    python train_minimap.py --clip clips/XXXX --epochs 25

Output weights: runs/minimap/weights/best.pt  -> run with:
    python yolov8_debug.py --model runs/minimap/weights/best.pt --conf 0.4
"""

import argparse
import glob
import os
import shutil

import cv2
import numpy as np


def detect_minimap(frames):
    """Median (cx, cy, r) of the minimap circle over a sample of frames."""
    H = W = None
    found = []
    for f in frames[:: max(1, len(frames) // 20)]:
        img = cv2.imread(f)
        if img is None:
            continue
        H, W = img.shape[:2]
        x0, y0 = int(W * 0.80), int(H * 0.65)
        roi = cv2.medianBlur(cv2.cvtColor(img[y0:, x0:], cv2.COLOR_BGR2GRAY), 3)
        c = cv2.HoughCircles(roi, cv2.HOUGH_GRADIENT, dp=1.2, minDist=200,
                             param1=80, param2=30, minRadius=70, maxRadius=160)
        if c is not None:
            cx, cy, r = c[0, 0]
            found.append((cx + x0, cy + y0, r))
    if not found:
        raise SystemExit("Could not detect the minimap circle in the clip.")
    arr = np.array(found)
    cx, cy, r = np.median(arr, axis=0)
    return float(cx), float(cy), float(r), W, H


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clip", default=None, help="clip dir (default: newest clips/*)")
    ap.add_argument("--epochs", type=int, default=25)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--batch", type=int, default=16)
    args = ap.parse_args()

    clip = args.clip or max(glob.glob("clips/*/"), key=os.path.getmtime)
    frames = sorted(glob.glob(os.path.join(clip, "frame_*.jpg")))
    if not frames:
        raise SystemExit(f"No frames in {clip}")
    print(f"clip: {clip}  ({len(frames)} frames)")

    cx, cy, r, W, H = detect_minimap(frames)
    label = f"0 {cx/W:.6f} {cy/H:.6f} {2*r/W:.6f} {2*r/H:.6f}\n"
    print(f"minimap @ ({cx:.0f},{cy:.0f}) r={r:.0f}  ->  label: {label.strip()}")

    root = "dataset_minimap"
    if os.path.isdir(root):
        shutil.rmtree(root)
    for sub in ("images/train", "images/val", "labels/train", "labels/val"):
        os.makedirs(os.path.join(root, sub), exist_ok=True)

    for i, f in enumerate(frames):
        split = "val" if i % 10 == 0 else "train"
        stem = f"f{i:05d}"
        shutil.copy(f, os.path.join(root, "images", split, stem + ".jpg"))
        with open(os.path.join(root, "labels", split, stem + ".txt"), "w") as fh:
            fh.write(label)

    data_yaml = os.path.join(root, "data.yaml")
    with open(data_yaml, "w") as fh:
        fh.write(f"path: {os.path.abspath(root)}\n"
                 f"train: images/train\nval: images/val\n"
                 f"names:\n  0: minimap\n")
    print(f"dataset built at {root}")

    from ultralytics import YOLO
    model = YOLO("yolov8n.pt")
    model.train(data=data_yaml, epochs=args.epochs, imgsz=args.imgsz,
                batch=args.batch, device=0, project="runs", name="minimap", exist_ok=True)
    print("\ndone -> runs/minimap/weights/best.pt")
    print("run it:  python yolov8_debug.py --model runs/minimap/weights/best.pt --conf 0.4")


if __name__ == "__main__":
    main()
