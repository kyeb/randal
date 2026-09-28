# /// script
# requires-python = ">=3.11,<3.13"
# dependencies = ["pyvista"]
# ///
"""Offscreen PNG renders of out/parts for quick visual checks.

Usage: uv run render.py [view,view,...] [hidden part label,...]
"""
import json
import sys
from pathlib import Path

import pyvista as pv

OUT = Path(__file__).parent / "out"
parts = json.loads((OUT / "parts/manifest.json").read_text())
hide = set(sys.argv[2].split(",")) if len(sys.argv) > 2 else set()
views = sys.argv[1].split(",") if len(sys.argv) > 1 else ["iso", "front", "side", "top"]
CAM = {
    "iso": [(520, -460, 420), (0, 0, 115), (0, 0, 1)],
    "iso_back": [(-520, -460, 420), (0, 0, 115), (0, 0, 1)],
    "front": [(900, 0, 115), (0, 0, 115), (0, 0, 1)],
    "back": [(-900, 0, 115), (0, 0, 115), (0, 0, 1)],
    "side": [(0, -900, 115), (0, 0, 115), (0, 0, 1)],
    "top": [(0, 0, 1000), (0, 0, 115), (1, 0, 0)],
    "bottom": [(0, 0, -900), (0, 0, 115), (1, 0, 0)],
    "motor": [(250, -60, 60), (0, 60, 40), (0, 0, 1)],
    "ear": [(90, -330, 60), (0, -90, 40), (0, 0, 1)],
    "brk_L": [(170, -190, 110), (0, -45, 45), (0, 0, 1)],
    "brk_R": [(170, 190, 110), (0, 45, 45), (0, 0, 1)],
    "bb": [(260, -40, 150), (-20, -30, 95), (0, 0, 1)],
    "cap": [(230, -260, 330), (0, -20, 225), (0, 0, 1)],
    "nut": [(120, 260, 330), (0, 80, 215), (0, 0, 1)],
    "detent": [(25, 30, 105), (-20, 0, 86), (0, 0, 1)],
    "detent_side": [(-20, 0, 86), (-20, 0, 86), (0, 0, 1)],
    "tongue": [(-160, 40, 150), (-28, 5, 114), (0, 0, 1)],
    "hood": [(160, 200, 320), (10, 75, 235), (0, 0, 1)],
    "tongue_front": [(30, 45, 125), (-25, -3, 114), (0, 0, 1)],
    "under_front": [(260, 0, -60), (0, 0, 55), (0, 0, 1)],
    "under_back": [(-260, 0, -60), (0, 0, 55), (0, 0, 1)],
}
for v in views:
    p = pv.Plotter(off_screen=True, window_size=(1400, 1100))
    p.set_background("white")
    for part in parts:
        if part["label"] in hide:
            continue
        mesh = pv.read(OUT / "parts" / part["file"])
        p.add_mesh(mesh, color=part["color"], smooth_shading=False, show_edges=False, specular=0.2)
        p.add_mesh(mesh.extract_feature_edges(35), color="black", line_width=1)
    pos, focal, up = CAM[v]
    p.camera_position = [pos, focal, up]
    if v in ("front", "back", "side", "top", "bottom"):
        p.enable_parallel_projection()
        p.camera.parallel_scale = 135
    else:
        p.camera.view_angle = 30
    f = OUT / f"render_{v}.png"
    p.screenshot(str(f))
    print(f)
