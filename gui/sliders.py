"""Reusable labeled slider widget for the HSV range controls."""

import tkinter as tk
from tkinter import ttk


def add_labeled_slider(parent, label: str, var: tk.IntVar, from_: int, to_: int, command):
    """Build a row containing a label, a horizontal scale, and a numeric entry.

    All three share the same IntVar, so they stay in sync.
    """
    row = ttk.Frame(parent)
    row.pack(fill=tk.X, pady=1)

    ttk.Label(row, text=label, width=6).pack(side=tk.LEFT)
    scale = ttk.Scale(
        row, from_=from_, to=to_, orient=tk.HORIZONTAL, variable=var, command=command
    )
    scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
    entry = ttk.Entry(row, width=4, textvariable=var)
    entry.pack(side=tk.RIGHT, padx=2)

    return scale, entry
