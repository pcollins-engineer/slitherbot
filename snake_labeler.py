"""Manual bounding-box labeler for snake training data (Tkinter).

Draw boxes on recorded frames and export YOLO labels for fine-tuning.

    python snake_labeler.py                      # newest clips/* folder
    python snake_labeler.py --images clips/XXXX --classes snake,snake_head,pellet

Controls:
    drag mouse      draw a box (current class)
    1..9            pick class
    u / Backspace   undo last box
    c               clear all boxes on this frame
    a / Left        previous frame      d / Right / Space   next frame
    s               save now (also auto-saves on navigate)
    q / Esc         quit

Labels are written next to the images in a sibling `labels/` folder, plus a
`classes.txt` / `data.yaml`, ready for `yolo detect train`.
"""

import argparse
import glob
import os
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk

CLASS_COLORS = ["#ff3030", "#00ff66", "#33aaff", "#ffcc00", "#ff00ff",
                "#00ffff", "#ff8800", "#aa66ff", "#88ff00"]
MAX_W, MAX_H = 1280, 720


class Labeler:
    def __init__(self, root, images, out_dir, classes):
        self.root = root
        self.images = images
        self.out_dir = out_dir
        self.classes = classes
        self.idx = 0
        self.cls = 0
        self.boxes = []          # current frame: list of [cls, x1, y1, x2, y2] in image px
        self.drag = None         # (x0, y0) during drag
        self.temp_id = None
        self.scale = 1.0
        self.tkimg = None
        self.img_wh = (0, 0)

        os.makedirs(out_dir, exist_ok=True)
        self._write_meta()
        self._build_ui()
        self._bind()
        self.load(0)

    # ---- ui ----
    def _build_ui(self):
        self.root.title("snake labeler")
        main = ttk.Frame(self.root); main.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(main, width=MAX_W, height=MAX_H, bg="black",
                                highlightthickness=0)
        self.canvas.pack(side=tk.LEFT)

        side = ttk.Frame(main); side.pack(side=tk.RIGHT, fill=tk.Y, padx=6, pady=6)
        ttk.Label(side, text="Class").pack(anchor=tk.W)
        self.cls_var = tk.IntVar(value=0)
        for i, name in enumerate(self.classes):
            ttk.Radiobutton(side, text=f"{i+1}. {name}", variable=self.cls_var,
                            value=i, command=self._on_cls).pack(anchor=tk.W)
        ttk.Separator(side, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=6)
        self.lbl_status = ttk.Label(side, text="", justify=tk.LEFT)
        self.lbl_status.pack(anchor=tk.W)
        ttk.Separator(side, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=6)
        ttk.Button(side, text="< Prev (a)", command=lambda: self.step(-1)).pack(fill=tk.X)
        ttk.Button(side, text="Next (d) >", command=lambda: self.step(1)).pack(fill=tk.X)
        ttk.Button(side, text="Undo (u)", command=self.undo).pack(fill=tk.X, pady=(6, 0))
        ttk.Button(side, text="Clear (c)", command=self.clear).pack(fill=tk.X)
        ttk.Button(side, text="Save (s)", command=self.save).pack(fill=tk.X, pady=(6, 0))
        ttk.Label(side, text="drag = draw box\n1-9 class  u undo  c clear",
                  foreground="#666").pack(anchor=tk.W, pady=8)

    def _bind(self):
        self.canvas.bind("<Button-1>", self.on_down)
        self.canvas.bind("<B1-Motion>", self.on_move)
        self.canvas.bind("<ButtonRelease-1>", self.on_up)
        self.root.bind("<Key>", self.on_key)

    # ---- data ----
    def _write_meta(self):
        with open(os.path.join(self.out_dir, "classes.txt"), "w") as f:
            f.write("\n".join(self.classes) + "\n")
        with open(os.path.join(self.out_dir, "data.yaml"), "w") as f:
            names = "\n".join(f"  {i}: {n}" for i, n in enumerate(self.classes))
            f.write(f"path: {os.path.abspath(os.path.dirname(self.out_dir))}\n"
                    f"train: images\nval: images\nnames:\n{names}\n")

    def label_path(self, i):
        stem = os.path.splitext(os.path.basename(self.images[i]))[0]
        return os.path.join(self.out_dir, stem + ".txt")

    def load(self, i):
        self.idx = i % len(self.images)
        img = Image.open(self.images[self.idx]).convert("RGB")
        self.img_wh = img.size
        self.scale = min(MAX_W / img.width, MAX_H / img.height, 1.0)
        disp = img.resize((int(img.width * self.scale), int(img.height * self.scale)),
                          Image.BILINEAR)
        self.tkimg = ImageTk.PhotoImage(disp)
        self.boxes = self._read_labels(self.idx)
        self.redraw()

    def _read_labels(self, i):
        p = self.label_path(i)
        boxes = []
        if os.path.exists(p):
            W, H = self.img_wh
            for line in open(p):
                parts = line.split()
                if len(parts) == 5:
                    c, cx, cy, w, h = parts
                    c = int(c); cx = float(cx) * W; cy = float(cy) * H
                    w = float(w) * W; h = float(h) * H
                    boxes.append([c, cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2])
        return boxes

    def save(self):
        W, H = self.img_wh
        lines = []
        for c, x1, y1, x2, y2 in self.boxes:
            cx = (x1 + x2) / 2 / W; cy = (y1 + y2) / 2 / H
            w = abs(x2 - x1) / W; h = abs(y2 - y1) / H
            lines.append(f"{c} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
        with open(self.label_path(self.idx), "w") as f:
            f.write("\n".join(lines) + ("\n" if lines else ""))
        self.set_status(saved=True)

    # ---- drawing ----
    def redraw(self):
        self.canvas.delete("all")
        self.canvas.config(width=self.tkimg.width(), height=self.tkimg.height())
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tkimg)
        for c, x1, y1, x2, y2 in self.boxes:
            color = CLASS_COLORS[c % len(CLASS_COLORS)]
            self.canvas.create_rectangle(x1 * self.scale, y1 * self.scale,
                                         x2 * self.scale, y2 * self.scale,
                                         outline=color, width=2)
            self.canvas.create_text(x1 * self.scale + 2, y1 * self.scale - 8,
                                    anchor=tk.W, fill=color, text=self.classes[c],
                                    font=("TkDefaultFont", 9))
        self.set_status()

    def set_status(self, saved=False):
        self.lbl_status.config(text=(
            f"frame {self.idx+1}/{len(self.images)}\n"
            f"{os.path.basename(self.images[self.idx])}\n"
            f"boxes: {len(self.boxes)}\n"
            f"class: {self.classes[self.cls]}\n"
            f"{'saved ✓' if saved else ''}"))

    # ---- events ----
    def on_down(self, e):
        self.drag = (e.x, e.y)
        self.temp_id = self.canvas.create_rectangle(e.x, e.y, e.x, e.y,
                                                    outline=CLASS_COLORS[self.cls], width=2)

    def on_move(self, e):
        if self.drag and self.temp_id:
            self.canvas.coords(self.temp_id, self.drag[0], self.drag[1], e.x, e.y)

    def on_up(self, e):
        if not self.drag:
            return
        x0, y0 = self.drag
        x1, y1, x2, y2 = min(x0, e.x), min(y0, e.y), max(x0, e.x), max(y0, e.y)
        self.drag = None
        self.temp_id = None
        if x2 - x1 > 4 and y2 - y1 > 4:  # ignore tiny clicks
            self.boxes.append([self.cls, x1 / self.scale, y1 / self.scale,
                               x2 / self.scale, y2 / self.scale])
        self.redraw()

    def on_key(self, e):
        k = e.keysym.lower()
        if k in ("q", "escape"):
            self.save(); self.root.destroy()
        elif k in ("d", "right", "space"):
            self.step(1)
        elif k in ("a", "left"):
            self.step(-1)
        elif k in ("u", "backspace"):
            self.undo()
        elif k == "c":
            self.clear()
        elif k == "s":
            self.save()
        elif k.isdigit() and 1 <= int(k) <= len(self.classes):
            self.cls = int(k) - 1
            self.cls_var.set(self.cls)
            self.set_status()

    def _on_cls(self):
        self.cls = self.cls_var.get()
        self.set_status()

    def step(self, d):
        self.save()
        self.load(self.idx + d)

    def undo(self):
        if self.boxes:
            self.boxes.pop()
            self.redraw()

    def clear(self):
        self.boxes = []
        self.redraw()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", default=None, help="image folder (default newest clips/*)")
    ap.add_argument("--out", default=None, help="labels output dir (default <images>/../labels)")
    ap.add_argument("--classes", default="snake,snake_head,pellet")
    args = ap.parse_args()

    folder = args.images or max(glob.glob("clips/*/"), key=os.path.getmtime)
    images = sorted(glob.glob(os.path.join(folder, "*.jpg")) +
                    glob.glob(os.path.join(folder, "*.png")))
    if not images:
        raise SystemExit(f"No images in {folder}")
    out = args.out or os.path.join(os.path.dirname(os.path.normpath(folder)), "labels")
    classes = [c.strip() for c in args.classes.split(",") if c.strip()]

    root = tk.Tk()
    Labeler(root, images, out, classes)
    root.mainloop()


if __name__ == "__main__":
    main()
