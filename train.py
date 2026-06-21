"""General YOLOv8 fine-tuner: train on a labeled clip and get weights you can
run live with yolov8_debug.py.

Pairs each image in a clip with its YOLO label (e.g. from snake_labeler.py),
builds a train/val dataset, and fine-tunes. Class names come from --names or a
classes.txt in the labels dir.

    # label first:  python snake_labeler.py --images clips/XXXX
    python train.py --images clips/XXXX --name snakes --epochs 50
    # then run it: python yolov8_debug.py --model runs/snakes/weights/best.pt --conf 0.4

Only images that actually have a non-empty label are used, so you can label
just a subset of frames.
"""

import argparse
import glob
import os
import shutil


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", default=None, help="image folder (default newest clips/*)")
    ap.add_argument("--labels", default=None, help="labels dir (default <images>/../labels)")
    ap.add_argument("--names", default=None, help="comma class names; else read classes.txt")
    ap.add_argument("--name", default="custom", help="run name -> runs/<name>")
    ap.add_argument("--model", default="yolov8n.pt")
    ap.add_argument("--epochs", type=int, default=50)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--device", default=0)
    args = ap.parse_args()

    images_dir = args.images or max(glob.glob("clips/*/"), key=os.path.getmtime)
    labels_dir = args.labels or os.path.join(os.path.dirname(os.path.normpath(images_dir)), "labels")

    if args.names:
        names = [c.strip() for c in args.names.split(",") if c.strip()]
    else:
        cls_file = os.path.join(labels_dir, "classes.txt")
        if not os.path.exists(cls_file):
            raise SystemExit(f"No --names and no {cls_file}. Label some frames first.")
        names = [l.strip() for l in open(cls_file) if l.strip()]
    print(f"classes: {names}")

    imgs = sorted(glob.glob(os.path.join(images_dir, "*.jpg")) +
                  glob.glob(os.path.join(images_dir, "*.png")))
    pairs = []
    for img in imgs:
        stem = os.path.splitext(os.path.basename(img))[0]
        lab = os.path.join(labels_dir, stem + ".txt")
        if os.path.exists(lab) and os.path.getsize(lab) > 0:
            pairs.append((img, lab))
    if not pairs:
        raise SystemExit(f"No labeled images found in {images_dir} (labels in {labels_dir}).")
    print(f"{len(pairs)} labeled frames of {len(imgs)} total")

    root = f"dataset_{args.name}"
    if os.path.isdir(root):
        shutil.rmtree(root)
    for sub in ("images/train", "images/val", "labels/train", "labels/val"):
        os.makedirs(os.path.join(root, sub), exist_ok=True)

    for i, (img, lab) in enumerate(pairs):
        split = "val" if i % 10 == 0 else "train"
        stem = f"f{i:05d}"
        shutil.copy(img, os.path.join(root, "images", split, stem + os.path.splitext(img)[1]))
        shutil.copy(lab, os.path.join(root, "labels", split, stem + ".txt"))

    data_yaml = os.path.join(root, "data.yaml")
    with open(data_yaml, "w") as f:
        f.write(f"path: {os.path.abspath(root)}\ntrain: images/train\nval: images/val\n"
                f"names:\n" + "\n".join(f"  {i}: {n}" for i, n in enumerate(names)) + "\n")

    from ultralytics import YOLO
    model = YOLO(args.model)
    model.train(data=data_yaml, epochs=args.epochs, imgsz=args.imgsz, batch=args.batch,
                device=args.device, project="runs", name=args.name, exist_ok=True)
    print(f"\ndone -> runs/{args.name}/weights/best.pt")
    print(f"run it: python yolov8_debug.py --model runs/{args.name}/weights/best.pt --conf 0.4")


if __name__ == "__main__":
    main()
