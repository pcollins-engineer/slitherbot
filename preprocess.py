"""Auto-label preprocessing CLI.

Reads exported color filters + raw frames and emits a YOLO dataset:

    python preprocess.py                 # filters/ + screenshots/ -> dataset/
    python preprocess.py --no-grid       # skip grid pitch estimation
    python preprocess.py --out runs/v0   # choose output dir

Output layout (dataset/ by default):
    images/        copies of the source frames
    labels/        YOLO label .txt per frame
    overlays/      debug visualizations (boxes/circles drawn on the frame)
    screen_model/  per-frame parametric scene JSON
    data.yaml      Ultralytics dataset descriptor

The labels are v0 *proposals* — load them in a YOLO labeling tool, correct
the mistakes, then train (see README).
"""

import argparse
import glob
import os
import shutil

import cv2

from pipeline import blobs, body, grid, overlay, screen_model, yolo_export
from pipeline.config import Settings, load_filters
from pipeline.screen_model import build as build_screen_model

IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".bmp")


def gather_images(folder: str):
    files = []
    for ext in IMAGE_EXTS:
        files.extend(glob.glob(os.path.join(folder, f"*{ext}")))
    return sorted(files)


def process_image(path: str, specs, settings: Settings):
    """Run all filters over one frame; return (detections, grid_pitch, shape)."""
    bgr = cv2.imread(path)
    if bgr is None:
        print(f"  ! failed to read {path}")
        return None
    h, w = bgr.shape[:2]

    # Heads first so the body can orient itself toward them.
    head_centers = []
    for spec in specs:
        if spec.kind == "head":
            mask, _ = spec.color_filter.apply(bgr)
            head_centers.extend(blobs.head_centers(mask, settings.min_head_area))

    detections = []
    for spec in specs:
        mask, _ = spec.color_filter.apply(bgr)
        if spec.kind == "pellet":
            detections += blobs.box_detections(mask, "pellet", settings.min_pellet_area)
        elif spec.kind == "boost_orb":
            detections += blobs.box_detections(mask, "boost_orb", settings.min_pellet_area)
        elif spec.kind == "head":
            detections += blobs.box_detections(mask, "snake_head", settings.min_head_area)
        elif spec.kind == "body":
            detections += body.body_detections(mask, settings, head_centers)

    pitch = grid.estimate_grid_pitch(bgr) if settings.detect_grid else None
    return bgr, detections, pitch, (w, h)


def main():
    parser = argparse.ArgumentParser(description="Auto-label Slither.io frames for YOLO.")
    parser.add_argument("--screenshots", default="screenshots", help="folder of input frames")
    parser.add_argument("--filters", default="filters", help="folder of exported *.json filters")
    parser.add_argument("--out", default="dataset", help="output dataset folder")
    parser.add_argument("--no-grid", action="store_true", help="skip grid pitch estimation")
    parser.add_argument("--min-pellet-area", type=int, default=Settings.min_pellet_area)
    parser.add_argument("--min-head-area", type=int, default=Settings.min_head_area)
    parser.add_argument("--min-body-area", type=int, default=Settings.min_body_area)
    args = parser.parse_args()

    settings = Settings(
        min_pellet_area=args.min_pellet_area,
        min_head_area=args.min_head_area,
        min_body_area=args.min_body_area,
        detect_grid=not args.no_grid,
    )

    specs = load_filters(args.filters)
    if not specs:
        print(f"No usable filters in '{args.filters}/'. Export some from the GUI first "
              f"(Save as slither_head / slither_pellet / slither_body), then rerun.")
        return
    print(f"Loaded {len(specs)} filter(s): " + ", ".join(f"{s.name}({s.kind})" for s in specs))

    images = gather_images(args.screenshots)
    if not images:
        print(f"No images in '{args.screenshots}/'. Drop a gameplay frame in there and rerun.")
        return

    # Output dirs.
    img_out = os.path.join(args.out, "images")
    lbl_out = os.path.join(args.out, "labels")
    ovl_out = os.path.join(args.out, "overlays")
    sm_out = os.path.join(args.out, "screen_model")
    for d in (img_out, lbl_out, ovl_out, sm_out):
        os.makedirs(d, exist_ok=True)

    import json
    total = 0
    for path in images:
        stem = os.path.splitext(os.path.basename(path))[0]
        result = process_image(path, specs, settings)
        if result is None:
            continue
        bgr, detections, pitch, (w, h) = result
        total += len(detections)

        shutil.copy(path, os.path.join(img_out, os.path.basename(path)))
        yolo_export.write_label(os.path.join(lbl_out, f"{stem}.txt"), detections, w, h)
        cv2.imwrite(os.path.join(ovl_out, f"{stem}.png"), overlay.draw(bgr, detections))

        model = build_screen_model(os.path.basename(path), w, h, detections, pitch)
        with open(os.path.join(sm_out, f"{stem}.json"), "w", encoding="utf-8") as f:
            json.dump(model.to_dict(), f, indent=2)

        pitch_str = "n/a" if pitch is None else f"{pitch:.1f}px"
        print(f"  {stem}: {len(detections)} detections, grid pitch {pitch_str}")

    yolo_export.write_data_yaml(os.path.join(args.out, "data.yaml"), args.out)
    print(f"\nDone. {total} proposed labels across {len(images)} image(s) -> '{args.out}/'.")
    print(f"Review overlays in '{ovl_out}/', correct labels, then train (see README).")


if __name__ == "__main__":
    main()
