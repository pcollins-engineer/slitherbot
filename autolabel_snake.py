"""Auto-label snakes in a recorded clip (no manual labeling) → YOLO labels.

Uses the color-filter perceiver to find whole-snake boxes and writes them as
class 0 = "snake". Feeds train.py for a fine-tuned snake detector.

    python autolabel_snake.py                 # newest clips/* -> <clip>/../snake_labels
    python train.py --images clips/XXXX --labels snake_labels --name snake
"""

import argparse
import glob
import os

import cv2

from perception.color_filter_perceiver import ColorFilterPerceiver


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", default=None, help="clip dir (default newest clips/*)")
    ap.add_argument("--out", default="snake_labels", help="labels output dir")
    ap.add_argument("--filters", default="filters")
    args = ap.parse_args()

    clip = args.images or max(glob.glob("clips/*/"), key=os.path.getmtime)
    frames = sorted(glob.glob(os.path.join(clip, "*.jpg")) + glob.glob(os.path.join(clip, "*.png")))
    if not frames:
        raise SystemExit(f"No frames in {clip}")

    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "classes.txt"), "w") as f:
        f.write("snake\n")

    per = ColorFilterPerceiver(args.filters)
    labeled = total = 0
    for img_path in frames:
        img = cv2.imread(img_path)
        if img is None:
            continue
        h, w = img.shape[:2]
        snakes = per.perceive(img).snakes
        lines = []
        for s in snakes:
            cx = (s.x + s.w / 2) / w
            cy = (s.y + s.h / 2) / h
            lines.append(f"0 {cx:.6f} {cy:.6f} {s.w / w:.6f} {s.h / h:.6f}")
        stem = os.path.splitext(os.path.basename(img_path))[0]
        with open(os.path.join(args.out, stem + ".txt"), "w") as f:
            f.write("\n".join(lines) + ("\n" if lines else ""))
        total += len(lines)
        labeled += 1 if lines else 0

    print(f"clip: {clip}")
    print(f"auto-labeled {labeled}/{len(frames)} frames, {total} snake boxes -> {args.out}/")
    print(f"train: python train.py --images {clip.rstrip(os.sep)} --labels {args.out} --name snake")


if __name__ == "__main__":
    main()
