# /// script
# requires-python = ">=3.11,<3.13"
# dependencies = ["build123d"]
# ///
"""Numeric audit of things the interference check can't see."""
import math
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
import frame as F
from build123d import *

print("== bracket base holes (vendor STEP circle edges) vs frame rail holes")
frame_holes = [h.center() for h in F.bracket_holes()]
for s in (1, -1):
    b = F.bracket(s)
    pts = []
    for e in b.edges():
        if e.geom_type == GeomType.CIRCLE and abs(e.radius - 1.59) < 0.05:
            c = e.arc_center
            if abs(e.normal().Z) > 0.9:          # base-leg holes run vertically in world
                pts.append((c.X, c.Y))
    worst = 0
    for fh in frame_holes:
        if (fh.Y > 0) != (s > 0):
            continue
        d = min(math.hypot(fh.X - p[0], fh.Y - p[1]) for p in pts)
        worst = max(worst, d)
    print(f"  side {s:+d}: worst frame-hole-to-bracket-hole offset {worst:.2f} mm ({len(pts)//2} bracket holes found)")

print("== nut room under the bracket at each frame hole (base underside down to the motor can)")
for fh in frame_holes:
    dx = abs(fh.X - F.X_MOTOR)
    can_top = F.Z_MOTOR + math.sqrt(max(F.GB_R ** 2 - dx ** 2, 0))
    print(f"  hole ({fh.X:6.1f},{fh.Y:6.1f}): {F.Z_RAIL0 - F.BRK_T - can_top:.1f} mm")

print("== encoder caps vs IMU holes")
cap_inner = F.Y_FACE - F.MOTOR_BODY
print(f"  encoder caps end at |y| = {cap_inner:.1f}; IMU holes reach |y| = {F.IMU[2] / 2 + F.IMU_HOLE / 2:.1f}; "
      f"cap top z = {F.Z_MOTOR + 17.0:.1f}, rail underside z = {F.Z_RAIL0:.1f}")

print("== Cytron connector clearances")
cy_l, cy_r = F.CY_Y - F.CYTRON[0] / 2, F.CY_Y + F.CYTRON[0] / 2
print(f"  terminal side (left) edge y={cy_l:.1f}, PDB right edge y={F.PDB_Y + F.PDB[0] / 2:.1f}  -> gap {cy_l - (F.PDB_Y + F.PDB[0] / 2):.1f}")
print(f"  control-header side (right) edge y={cy_r:.1f}, wall y={F.Y_IN:.1f}  -> gap {F.Y_IN - cy_r:.1f}")

print("== battery insertion (rigid pack, right end tucks under the hood, left end drops past the stop blocks)")
L, H = F.BATTERY[1], F.BATTERY[2]
pocket = F.BAT_Y1 - F.BAT_Y0
worst = max(L * math.cos(t) + H * math.sin(t) for t in [i * math.pi / 1800 for i in range(0, 300)])
print(f"  pocket {pocket:.2f} mm; pack's max projected length while rotating in {worst:.2f} mm -> slack {pocket - worst:.2f}")

print("== print check: faces pointing down in print orientation (build direction +X), not on the bed")
for name, shape, bed_x, up in (("frame", F.build_frame(), F.X0, Vector(1, 0, 0)), ("battery clip", F.build_clip(), None, Vector(0, 0, -1))):
    bb = shape.bounding_box()
    if bed_x is None:          # the clip prints upside down: its top plate on the bed, build direction -Z
        bed = bb.max.Z
    rows = []
    for f in shape.faces():
        try:
            n = f.normal_at(f.center())
        except Exception:
            continue
        down = -n.dot(up)      # 1 = facing straight down
        if down < 0.71:        # anything shallower than 45° from vertical prints fine
            continue
        c = f.center()
        on_bed = abs(c.X - bed_x) < 0.05 if bed_x is not None else abs(c.Z - bed) < 0.05
        if on_bed or f.area < 0.5:
            continue
        fb = f.bounding_box()
        span = sorted([fb.size.X, fb.size.Y, fb.size.Z])
        rows.append((round(f.area, 1), round(span[1], 1), round(span[2], 1), round(c.X, 1), round(c.Y, 1), round(c.Z, 1), f.geom_type.name))
    rows.sort(key=lambda r: -r[0])
    print(f"  {name}: {len(rows)} downward faces")
    for r in rows[:30]:
        print(f"    area {r[0]:7.1f}  size {r[1]:5.1f} x {r[2]:5.1f}  at ({r[3]:6.1f},{r[4]:6.1f},{r[5]:6.1f})  {r[6]}")
