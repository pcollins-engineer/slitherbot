"""Main Tkinter application for the Slither.io color filter + eyedropper tool."""

import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from typing import List, Optional, Tuple

import cv2
from PIL import ImageTk

from core import ColorFilter, FilterExporter, ScreenshotLoader
from gui.eyedropper import canvas_to_image_coords, sample_pixel
from gui.preview_panel import bgr_to_tk, gray_to_tk
from gui.sliders import add_labeled_slider

CANVAS_SIZE = 400


class SlitherColorToolApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Slither.io Color Filter + Eyedropper Tool")

        self.loader = ScreenshotLoader()
        self.color_filter = ColorFilter()
        self.exporter = FilterExporter()

        self.current_bgr = None
        self.current_display_image: Optional[ImageTk.PhotoImage] = None
        self.current_mask_display_image: Optional[ImageTk.PhotoImage] = None

        self.view_mode = tk.StringVar(value="mask_applied")  # "mask", "mask_applied"

        # Recent colors: list of (rgb, hsv, hex, (x, y))
        self.recent_colors: List[Tuple[Tuple[int, int, int], Tuple[int, int, int], str, Tuple[int, int]]] = []

        self._build_ui()
        self._bind_keys()
        self._load_initial_image()

    # -------------------------
    # UI Construction
    # -------------------------

    def _build_ui(self):
        # Top controls: folder + navigation
        top_frame = ttk.Frame(self.root)
        top_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        ttk.Button(top_frame, text="Select Folder", command=self.on_select_folder).pack(side=tk.LEFT, padx=2)

        self.lbl_folder = ttk.Label(top_frame, text=f"Folder: {self.loader.folder}")
        self.lbl_folder.pack(side=tk.LEFT, padx=5)

        ttk.Button(top_frame, text="Prev", command=self.on_prev).pack(side=tk.RIGHT, padx=2)
        ttk.Button(top_frame, text="Next", command=self.on_next).pack(side=tk.RIGHT, padx=2)

        # Right panel: sliders + info (packed before the middle so it keeps its width)
        right_frame = ttk.Frame(self.root)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)

        # Middle: images
        mid_frame = ttk.Frame(self.root)
        mid_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.canvas_original = tk.Canvas(mid_frame, width=CANVAS_SIZE, height=CANVAS_SIZE, bg="black")
        self.canvas_original.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2, pady=2)

        self.canvas_filtered = tk.Canvas(mid_frame, width=CANVAS_SIZE, height=CANVAS_SIZE, bg="black")
        self.canvas_filtered.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2, pady=2)

        self.canvas_original.bind("<Button-1>", self.on_canvas_click)

        # View mode
        view_frame = ttk.LabelFrame(right_frame, text="View Mode")
        view_frame.pack(fill=tk.X, pady=5)

        ttk.Radiobutton(view_frame, text="Mask", variable=self.view_mode, value="mask",
                        command=self.update_preview).pack(anchor=tk.W)
        ttk.Radiobutton(view_frame, text="Mask Applied", variable=self.view_mode, value="mask_applied",
                        command=self.update_preview).pack(anchor=tk.W)

        # Sliders
        sliders_frame = ttk.LabelFrame(right_frame, text="HSV Range")
        sliders_frame.pack(fill=tk.X, pady=5)

        self.h_min_var = tk.IntVar(value=self.color_filter.h_min)
        self.h_max_var = tk.IntVar(value=self.color_filter.h_max)
        self.s_min_var = tk.IntVar(value=self.color_filter.s_min)
        self.s_max_var = tk.IntVar(value=self.color_filter.s_max)
        self.v_min_var = tk.IntVar(value=self.color_filter.v_min)
        self.v_max_var = tk.IntVar(value=self.color_filter.v_max)

        add_labeled_slider(sliders_frame, "H min", self.h_min_var, 0, 179, self.on_slider_change)
        add_labeled_slider(sliders_frame, "H max", self.h_max_var, 0, 179, self.on_slider_change)
        add_labeled_slider(sliders_frame, "S min", self.s_min_var, 0, 255, self.on_slider_change)
        add_labeled_slider(sliders_frame, "S max", self.s_max_var, 0, 255, self.on_slider_change)
        add_labeled_slider(sliders_frame, "V min", self.v_min_var, 0, 255, self.on_slider_change)
        add_labeled_slider(sliders_frame, "V max", self.v_max_var, 0, 255, self.on_slider_change)

        # Eyedropper info
        eyedrop_frame = ttk.LabelFrame(right_frame, text="Eyedropper")
        eyedrop_frame.pack(fill=tk.X, pady=5)

        self.lbl_rgb = ttk.Label(eyedrop_frame, text="RGB: -")
        self.lbl_rgb.pack(anchor=tk.W)
        self.lbl_hsv = ttk.Label(eyedrop_frame, text="HSV: -")
        self.lbl_hsv.pack(anchor=tk.W)
        self.lbl_hex = ttk.Label(eyedrop_frame, text="Hex: -")
        self.lbl_hex.pack(anchor=tk.W)
        self.lbl_coord = ttk.Label(eyedrop_frame, text="Coord: -")
        self.lbl_coord.pack(anchor=tk.W)

        self.recent_listbox = tk.Listbox(eyedrop_frame, height=5)
        self.recent_listbox.pack(fill=tk.X, pady=2)

        # Export buttons
        export_frame = ttk.LabelFrame(right_frame, text="Export Filters")
        export_frame.pack(fill=tk.X, pady=5)

        for name in ("slither_head", "slither_pellet", "slither_body"):
            ttk.Button(export_frame, text=f"Save as {name}",
                       command=lambda n=name: self.on_export(n)).pack(fill=tk.X, pady=1)

    # -------------------------
    # Key Bindings
    # -------------------------

    def _bind_keys(self):
        self.root.bind("<Left>", lambda e: self.on_prev())
        self.root.bind("<Right>", lambda e: self.on_next())

    # -------------------------
    # Image Loading / Display
    # -------------------------

    def _load_initial_image(self):
        path = self.loader.current_path()
        if path is None:
            messagebox.showinfo("Info", f"No images found in folder: {self.loader.folder}")
            return
        self.load_image(path)

    def load_image(self, path: str):
        self.current_bgr = cv2.imread(path)
        if self.current_bgr is None:
            messagebox.showerror("Error", f"Failed to load image: {path}")
            return
        self.update_preview()

    def _sync_filter_from_sliders(self):
        self.color_filter.set_range(
            self.h_min_var.get(),
            self.h_max_var.get(),
            self.s_min_var.get(),
            self.s_max_var.get(),
            self.v_min_var.get(),
            self.v_max_var.get(),
        )

    def update_preview(self):
        if self.current_bgr is None:
            return

        self._sync_filter_from_sliders()
        mask, filtered = self.color_filter.apply(self.current_bgr)

        # Original
        self.current_display_image = bgr_to_tk(self.current_bgr, (CANVAS_SIZE, CANVAS_SIZE))
        self.canvas_original.delete("all")
        self.canvas_original.create_image(0, 0, anchor=tk.NW, image=self.current_display_image)

        # Filtered / Mask
        if self.view_mode.get() == "mask":
            self.current_mask_display_image = gray_to_tk(mask, (CANVAS_SIZE, CANVAS_SIZE))
        else:
            self.current_mask_display_image = bgr_to_tk(filtered, (CANVAS_SIZE, CANVAS_SIZE))

        self.canvas_filtered.delete("all")
        self.canvas_filtered.create_image(0, 0, anchor=tk.NW, image=self.current_mask_display_image)

    # -------------------------
    # Event Handlers
    # -------------------------

    def on_select_folder(self):
        folder = filedialog.askdirectory(initialdir=".")
        if not folder:
            return
        self.loader.set_folder(folder)
        self.lbl_folder.config(text=f"Folder: {self.loader.folder}")
        if self.loader.has_images():
            self.load_image(self.loader.current_path())
        else:
            messagebox.showinfo("Info", f"No images found in folder: {self.loader.folder}")

    def on_next(self):
        path = self.loader.next()
        if path:
            self.load_image(path)

    def on_prev(self):
        path = self.loader.prev()
        if path:
            self.load_image(path)

    def on_slider_change(self, _event=None):
        self.update_preview()

    def on_canvas_click(self, event):
        if self.current_bgr is None:
            return

        img_height, img_width = self.current_bgr.shape[:2]
        coords = canvas_to_image_coords(event.x, event.y, img_width, img_height, CANVAS_SIZE)
        if coords is None:
            return
        x_img, y_img = coords

        sample = sample_pixel(self.current_bgr, x_img, y_img)

        self.lbl_rgb.config(text=f"RGB: {sample['rgb']}")
        self.lbl_hsv.config(text=f"HSV: {sample['hsv']}")
        self.lbl_hex.config(text=f"Hex: {sample['hex']}")
        self.lbl_coord.config(text=f"Coord: {sample['coord']}")

        self.recent_colors.insert(0, (sample["rgb"], sample["hsv"], sample["hex"], sample["coord"]))
        self.recent_colors = self.recent_colors[:10]
        self._refresh_recent_listbox()

    def _refresh_recent_listbox(self):
        self.recent_listbox.delete(0, tk.END)
        for rgb, hsv, hex_color, coord in self.recent_colors:
            self.recent_listbox.insert(tk.END, f"{hex_color} RGB{rgb} HSV{hsv} @ {coord}")

    def on_export(self, name: str):
        self._sync_filter_from_sliders()
        path = self.exporter.save(name, self.color_filter)
        messagebox.showinfo("Export", f"Saved filter as: {path}")


def main():
    root = tk.Tk()
    SlitherColorToolApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
