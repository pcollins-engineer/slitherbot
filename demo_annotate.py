"""Human-readable annotated demo: draw labeled boxes over each detected object.

Unlike ``preprocess.py`` (which emits the fine-grained YOLO representation —
a chain of body_segment boxes per snake), this draws **one box per whole
object** with a text label, for showing that detection works at a glance:

    python demo_annotate.py                         # all frames in screenshots/
    python demo_annotate.py screenshots/blue_enemy.png

Output: ``dataset/demo/<name>_annotated.png``.

Snakes are labeled just "snake" — telling mine vs. enemy apart isn't solved
yet (snakes can share a color); see the Autonomous Controller plan in the
README for the camera-center heuristic.
"""

import argparse
import glob
import os
import sys

import cv2

from pipeline.config import Settings, load_filters

# Map filter kind -> human label shown on the box.
KIND_LABEL = {
    "pellet": "pellet",
    "body": "snake",
    "head": "snake head",
    "boost_orb": "orb",
}
BOX_COLOR = (0, 0, 255)  # red (BGR)


# A real snake is a large blob; require this many px to reject stray fragments.
DEMO_MIN_SNAKE_AREA = 800


def is_round(w, h, area):
    """Compact + roughly square → pellet/orb; rejects thin text strokes & lines."""
    if w == 0 or h == 0:
        return False
    extent = area / float(w * h)       # filled fraction of the bbox
    aspect = max(w, h) / float(min(w, h))
    return extent >= 0.45 and aspect <= 2.5


def labeled_box(img, x, y, w, h, text):
    cv2.rectangle(img, (x, y), (x + w, y + h), BOX_COLOR, 2)
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
    ty = max(y, th + 4)
    cv2.rectangle(img, (x, ty - th - 4), (x + tw + 4, ty), BOX_COLOR, -1)
    cv2.putText(img, text, (x + 2, ty - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                (255, 255, 255), 1, cv2.LINE_AA)


def annotate(path, specs, settings):
    bgr = cv2.imread(path)
    if bgr is None:
        print(f"  ! failed to read {path}")
        return None
    counts = {}
    for spec in specs:
        mask, _ = spec.color_filter.apply(bgr)
        if spec.kind == "body":
            min_area = max(settings.min_body_area, DEMO_MIN_SNAKE_AREA)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        elif spec.kind == "head":
            min_area = settings.min_head_area
        else:
            min_area = settings.min_pellet_area
        round_only = spec.kind in ("pellet", "boost_orb")

        label = KIND_LABEL.get(spec.kind, spec.kind)
        num, _labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
        for i in range(1, num):
            area = int(stats[i, cv2.CC_STAT_AREA])
            if area < min_area:
                continue
            x = int(stats[i, cv2.CC_STAT_LEFT]); y = int(stats[i, cv2.CC_STAT_TOP])
            w = int(stats[i, cv2.CC_STAT_WIDTH]); h = int(stats[i, cv2.CC_STAT_HEIGHT])
            if round_only and not is_round(w, h, area):
                continue  # drop thin text strokes / UI lines
            labeled_box(bgr, x, y, w, h, label)
            counts[label] = counts.get(label, 0) + 1
    return bgr, counts


def main():
    parser = argparse.ArgumentParser(description="Draw labeled detection boxes onto frames.")
    parser.add_argument("images", nargs="*", help="image paths (default: all of screenshots/)")
    parser.add_argument("--filters", default="filters")
    parser.add_argument("--out", default=os.path.join("dataset", "demo"))
    args = parser.parse_args()

    specs = load_filters(args.filters)
    if not specs:
        print(f"No usable filters in '{args.filters}/'. Export some from the GUI first.")
        return

    images = args.images or sorted(
        p for ext in (".png", ".jpg", ".jpeg", ".bmp")
        for p in glob.glob(os.path.join("screenshots", f"*{ext}"))
    )
    if not images:
        print("No images to annotate.")
        return

    os.makedirs(args.out, exist_ok=True)
    for path in images:
        result = annotate(path, specs, settings=Settings())
        if result is None:
            continue
        bgr, counts = result
        stem = os.path.splitext(os.path.basename(path))[0]
        out_path = os.path.join(args.out, f"{stem}_annotated.png")
        cv2.imwrite(out_path, bgr)
        summary = ", ".join(f"{v} {k}" for k, v in counts.items()) or "nothing"
        print(f"  {stem}: {summary}  ->  {out_path}")


if __name__ == "__main__":
    main()
