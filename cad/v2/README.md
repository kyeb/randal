# randal v2 frame

One-piece printed loop frame with a backplane, motors hanging from the bay floor on Pololu L-brackets, and the
battery on top. v1 was the previous loop frame with the Pi panel.

## Files

| File | What it does |
|---|---|
| `frame.py` | The model (build123d). Writes `out/frame.stl`, `out/battery_clip.stl`, STEP files, `out/assembly.glb`, and `out/summary.json` (mass, CoM, interference and screw-access checks). |
| `audit.py` | Numeric checks the renders can't show: bracket hole alignment against the vendor model, nut room, connector clearances, battery rotate-in slack, and every overhang in print orientation. |
| `render.py` | Offscreen PNG views of the assembly, e.g. `uv run render.py iso,front bracket_L`. |
| `viewer.html`, `serve.py` | Interactive 3D viewer: `python3 serve.py 8123`, then open `http://localhost:8123/viewer.html`. |
| `vendor/` | Pololu's STEP models of the 37D 50:1 encoder gearmotor and the #1084 stamped L-bracket. |

```bash
uv run frame.py && uv run audit.py
```

## Printing

- Bambu PLA, 3–4 walls (for the insert holes and the detent tongue).
- `frame.stl`: backplane on the bed, no supports. About 179 × 198 mm on the bed, 56 mm tall.
- `battery_clip.stl`: top plate on the bed, no supports.

## Hardware

| Joint | Hardware |
|---|---|
| Brackets to bay floor | 8 × M3×10 (or ×12) from the top, nuts held under the bracket |
| Battery clip | 2 × M3×8 into M3 heat-set inserts in the left wall |
| Cytron | 4 screws through the standoffs to nuts on the back (M2.5 if M3 won't pass the board's ~3 mm holes) |
| IMU | 4 screws through the floor to nuts underneath |

## Assembly notes

- Battery: tuck the right end under the hood, drop the left end in, screw on the clip. The leads go down
  through the deck at the left end, so the pack can charge in place.
- Breadboard: slides in from the right along its rails and clicks past the detent. Press the tongue on the
  backplane's rear face to slide it back out.
- Motor ribbons come up through the two floor slots above their encoder caps (right motor front, left motor back).
- Tuning knobs if the first print is off: `DETENT_L` / `DETENT_H` (click force), `INSERT_M3` (insert bore),
  `BAT_CLEAR` (pocket length).
