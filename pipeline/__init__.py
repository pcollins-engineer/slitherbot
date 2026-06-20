"""Auto-label preprocessing pipeline.

Turns exported color filters (``filters/*.json``) + raw frames
(``screenshots/``) into YOLO-format labels, debug overlays, and a
per-frame parametric "screen model".

This is the v0 auto-labeler described in the README: its output is meant
to be hand-corrected, not trusted blindly. See ``preprocess.py`` for the
CLI entry point.
"""
