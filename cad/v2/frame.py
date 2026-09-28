# /// script
# requires-python = ">=3.11,<3.13"
# dependencies = ["build123d"]
# ///
"""randal v2 frame: loop + backplane, motors hanging on Pololu stamped L-brackets, battery on top.

World axes: X fore-aft (+ = front, the open face), Y along the axle, Z up, ground at Z=0.
Print orientation: backplane on the bed, build direction +X. Every feature is either part of
the Y-Z profile (extruded along X) or grows straight up in +X from the backplane, so nothing
needs support.
"""
import json
import math
from pathlib import Path

from build123d import *

HERE = Path(__file__).parent
OUT = HERE / "out"

# ---------------------------------------------------------------- purchased parts (datasheets / vendor STEP)
WHEEL_R = 40.0
WHEEL_W = 10.0
GB_R = 18.4            # gearbox radius (Ø36.8)
SHAFT_OFFSET = 7.0     # output shaft is 7 mm off the gearbox axis
MOTOR_BODY = 70.1      # face to back of encoder cap
BRK_T = 2.0            # Pololu #1084 stamped L-bracket
BRK_AXIS = 20.8        # base-leg mounting surface to gearbox axis
BRK_BASE = 49.2        # base-leg length from the face plate's outer face
BRK_ROWS = 31.2        # base-leg hole rows, centred on the gearbox axis
BRK_HOLE0, BRK_PITCH = 8.4, 6.35   # first base hole from the face plate's outer face, then 1/4" pitch
CYTRON = (84.5, 62.0, 78.5, 56.0)        # board w, h, hole pitch w, h — pitch measured off the v1 frame (manual says ~78.74 × ~55.88)
BREADBOARD = (82.5, 54.6, 8.5)           # half-size 400-point (standard dims, not measured)
IMU = (25.4, 25.4, 20.32)                # SparkFun 1"x1" Qwiic, holes on 0.8"
BATTERY = (46.3, 155.3, 24.0)            # soft pack, x × y × z as it lies on the deck
PDB = (36.0, 50.0, 30.5)                 # Matek PDB-XT60, 30.5 mm hole square, M3
XT60 = (17.0, 10.0)                      # pass-through for the battery's XT60 + balance plug

# ---------------------------------------------------------------- frame parameters
D = 56.0               # depth (fore-aft) = print height
T_BACK = 3.0
T_LEG = 5.0
T_RAIL = 5.0           # bay floor; the brackets bolt to its underside
T_TOP = 5.0            # battery deck
Z_AXLE = WHEEL_R
X_MOTOR = -5.1         # gearbox axis and axle (shaft offset is vertical); set so the axle sits under the CoM
# motors sit shaft-up in their brackets (offset toward the base leg), so the encoder leads exit upward
BAY_H = 160.0          # rail top to deck underside
LIP_H = BATTERY[2] + 0.5   # pocket walls come up to the pack's top; the hood and clip close the top and front
T_CAP = 3.0
CAP_SKIRT = 12.0       # the clip's skirt drops over the outside of the left wall; its 2 M3 screws go through it
BAT_CLEAR = 2.0        # per end; the pack has to rotate in under the hood (needs ~1.9 mm over its length)
BAT_SHIFT = XT60[1] / 2    # pack sits toward +Y so the lead pass-through fits at the -Y end
FILLET = 6.0

X0, X1 = -D / 2, D / 2
XB = X0 + T_BACK
BAT_Y0 = -BATTERY[1] / 2 + BAT_SHIFT - BAT_CLEAR     # pocket ends
BAT_Y1 = BATTERY[1] / 2 + BAT_SHIFT + BAT_CLEAR
Y_IN = BAT_Y1                                         # the +Y wall is the pocket's end stop
Y_OUT = Y_IN + T_LEG
BRK_INSET = 3.66                                      # bracket plate's outer face sits this far inside the wall's outer face (as on v1)
Y_FACE = Y_OUT - BRK_INSET - BRK_T                    # motor face = inner face of the bracket plate
Z_MOTOR = Z_AXLE - SHAFT_OFFSET
Z_RAIL0 = Z_MOTOR + BRK_AXIS
Z_RAIL1 = Z_RAIL0 + T_RAIL
Z_TOP0 = Z_RAIL1 + BAY_H
Z_TOP1 = Z_TOP0 + T_TOP
Z_LIP = Z_TOP1 + LIP_H

CYTRON_HOLE = 3.5     # as on v1: bolt through to a nut on the back (or an M2.5 heat-set insert)
IMU_HOLE = 6.5        # as on v1: bolt through to a nut under the floor
M3_PILOT = 2.6
M3_CLEAR = 3.4
INSERT_M3 = (4.0, 6.0)   # bore Ø, depth for M3 knurled heat-set inserts (~4.5 OD, ~5 long)

# layout inside the bay (boards on the backplane, facing the open front)
SCREW_ACCESS = 25.0                                  # clear height above each bracket screw for an L-key from the front
BB_Y0, BB_Z0 = -BREADBOARD[0] / 2, Z_RAIL1 + SCREW_ACCESS + 3.0   # breadboard: centred (USB room at either end), above the bracket screws, slides in from the right
BB_Y = BB_Y0 + BREADBOARD[0] / 2
DETENT_L, DETENT_H = 22.0, 0.6                       # breadboard click: tongue length (longer = softer), bump height (tune after the first print)
BB_GRIP = 40.0                                       # length of the lips that hold the board (left end)
CY_Y, CY_Z = 26.0, Z_TOP0 - 8.0 - CYTRON[1] / 2      # Cytron: top-right, terminals toward -Y
PDB_Y, PDB_Z = -52.0, Z_TOP0 - 10.0 - PDB[1] / 2     # PDB footprint: top-left (optional)
IMU_X, IMU_Y = 0.0, 0.0                              # centred: no yaw-acceleration leakage into the fore-aft axis
CAP_SCREW_X = (-16.0, 16.0)
HOOD = 10.0            # right-end hood length over the pack
HOOD_RAMP = 1.5        # hood underside rises this much toward its tip: lead-in for the pack's corner
CLIP_W = 25.0          # left clip overlap onto the pack's top


def ybox(y0, y1, z0, z1, x0=X0, x1=X1):
    y0, y1 = sorted((y0, y1))
    z0, z1 = sorted((z0, z1))
    x0, x1 = sorted((x0, x1))
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(x1 - x0, y1 - y0, z1 - z0)


def cyl_x(y, z, r, x0, x1):
    return Pos((x0 + x1) / 2, y, z) * Rot(0, 90, 0) * Cylinder(r, x1 - x0)


def cyl_y(x, z, r, y0, y1):
    return Pos(x, (y0 + y1) / 2, z) * Rot(90, 0, 0) * Cylinder(r, abs(y1 - y0))


def cyl_z(x, y, r, z0, z1):
    return Pos(x, y, (z0 + z1) / 2) * Cylinder(r, z1 - z0)


def standoffs(yc, zc, pw, ph, pilot, h=5.0, od=6.5):
    posts, pilots = [], []
    for dy in (-pw / 2, pw / 2):
        for dz in (-ph / 2, ph / 2):
            posts.append(cyl_x(yc + dy, zc + dz, od / 2, XB - 0.5, XB + h))
            pilots.append(cyl_x(yc + dy, zc + dz, pilot / 2, XB - 1, XB + h + 1))
    return posts, pilots


def bracket_holes():
    """Through-holes in the rail for the brackets' base legs, 2 per row per side. The motor blocks the underside,
    so screws drop in from the bay floor (L-key from the open front) into nuts held under the bracket."""
    holes = []
    for s in (-1, 1):
        for k in (0, 5):     # the pair v1 uses
            y = s * (Y_OUT - BRK_INSET - BRK_HOLE0 - k * BRK_PITCH)
            for dx in (-BRK_ROWS / 2, BRK_ROWS / 2):
                holes.append(cyl_z(X_MOTOR + dx, y, M3_CLEAR / 2, Z_RAIL0 - 1, Z_RAIL1 + 1))
    return holes


def build_frame():
    # --- the loop profile, extruded the full depth
    legs = ybox(-Y_OUT, -Y_IN, Z_RAIL0, Z_LIP) + ybox(Y_IN, Y_OUT, Z_RAIL0, Z_LIP)
    rail = ybox(-Y_IN - 1, Y_IN + 1, Z_RAIL0, Z_RAIL1)
    deck = ybox(-Y_IN - 1, Y_IN + 1, Z_TOP0, Z_TOP1)
    frame = legs + rail + deck
    # right-end hood: roof over the pack's right end (profile, full depth) + a front lip that bridges off the wall
    frame += ybox(Y_IN - HOOD, Y_OUT, Z_LIP - 1, Z_LIP + T_CAP) - ybox(Y_IN - HOOD - 1, Y_IN, Z_LIP - 1.01, Z_LIP)
    ramp = Polygon((Y_IN - HOOD - 0.01, Z_LIP - 0.01), (Y_IN - HOOD - 0.01, Z_LIP + HOOD_RAMP), (Y_IN, Z_LIP - 0.01), align=None)
    frame -= extrude(Plane.YZ.offset(X1 + 1) * ramp, D + 2)
    frame += ybox(Y_IN - HOOD, Y_IN + 1, Z_TOP1 - 1, Z_LIP, X1 - T_CAP, X1)
    frame = fillet_inside(frame)

    # --- battery pocket stops above the deck. +Y end: the wall itself. -Y end: two blocks either side of the lead channel.
    ch = XT60[0] / 2 + 1
    for xa, xb in ((X0, -ch), (ch, X1 - T_CAP)):     # front block stops short of the clip's front skirt
        frame += ybox(-Y_IN - 1, BAT_Y0, Z_TOP1 - 1, Z_LIP, xa, xb)

    # --- backplane (first layers on the bed), rises above the deck as the back lip
    frame += ybox(-Y_IN - 1, Y_IN + 1, Z_RAIL1 - 1, Z_LIP, X0, XB)

    # IMU: one pad along the full depth (part of the profile, prints clean)
    iy = IMU[2] / 2
    frame += ybox(IMU_Y - iy - 6, IMU_Y + iy + 6, Z_RAIL1 - 1, Z_RAIL1 + 4, XB, X1)

    # breadboard rails: a ledge under the full length, lips over the front face on the left BB_GRIP mm only,
    # so the board slides right ~BB_GRIP mm to come free (its tape is worn out). 2 mm lips print as a short overhang.
    t_bb, c = BREADBOARD[2] + 0.4, 0.4
    y_end = BB_Y0 + BREADBOARD[0]
    y_stop = BB_Y0 - 0.3
    frame += ybox(y_stop - 3, y_end + 3.5, BB_Z0 - 3, BB_Z0, XB - 1, XB + t_bb)            # ledge
    frame += ybox(y_stop - 3, y_stop, BB_Z0 - 3, BB_Z0 + 12, XB - 1, XB + t_bb)           # left end stop
    frame += ybox(y_stop - 3, BB_Y0 + BB_GRIP, BB_Z0 - 3, BB_Z0 + 2, XB + t_bb, XB + t_bb + 2)   # bottom lip
    # click detent: a tongue cut free in the backplane by a U-slot (it flexes backward, out the robot's back), with a
    # 0.6 mm bump on its face just past the seated board's right edge: ramp on the entry side, 45° face holding the
    # board. Part of the first layers on the bed, so it prints clean.
    zc, tw = BB_Z0 + BREADBOARD[1] / 2, 8.0
    ty0, ty1 = y_end - DETENT_L, y_end + 3.5
    frame -= ybox(ty0, ty1 + 1.0, zc - tw / 2 - 1.0, zc + tw / 2 + 1.0, X0 - 1, XB + 0.01) - ybox(ty0 - 1, ty1, zc - tw / 2, zc + tw / 2, X0 - 2, XB + 1)
    # bump profile drawn in the Y-X plane (local u = world Y, local v = world -X), extruded up the tongue's height
    yx = Plane(origin=(0, 0, zc - tw / 2), x_dir=(0, 1, 0), z_dir=(0, 0, 1))
    bump = Polygon((y_end + 0.2, -(XB - 0.01)), (y_end + 0.2 + DETENT_H, -(XB + DETENT_H)), (ty1, -(XB - 0.01)), align=None)
    frame += extrude(yx * bump, tw)
    zt = BB_Z0 + BREADBOARD[1] + c
    frame += ybox(y_stop - 3, BB_Y0 + BB_GRIP, zt, zt + 3, XB - 1, XB + t_bb + 2)               # top rail
    frame += ybox(y_stop - 3, BB_Y0 + BB_GRIP, zt - 2, zt + 3, XB + t_bb, XB + t_bb + 2)          # top lip

    # Cytron standoffs (through-holes) + PDB standoffs (M3 pilots)
    cy_posts, cy_pilots = standoffs(CY_Y, CY_Z, CYTRON[2], CYTRON[3], CYTRON_HOLE)
    pdb_posts, pdb_pilots = standoffs(PDB_Y, PDB_Z, PDB[2], PDB[2], M3_PILOT + 0.1)
    for p in cy_posts + pdb_posts:
        frame += p

    # --- cuts
    cuts = Part() + bracket_holes()[0]
    for h in bracket_holes()[1:]:
        cuts += h
    for p in cy_pilots + pdb_pilots:
        cuts += p
    for y in (IMU_Y - iy, IMU_Y + iy):
        for dx in (-iy, iy):
            cuts += cyl_z(IMU_X + dx, y, IMU_HOLE / 2, Z_RAIL0 - 1, Z_RAIL1 + 5)
    # battery lead: channel through the -Y stop blocks and a hole down through the deck into the bay
    cuts += ybox(-Y_IN + 0.01, BAT_Y0, Z_TOP0 - 1, Z_LIP + 1, -XT60[0] / 2, XT60[0] / 2)
    # motor ribbons (positions from the vendor model): leads leave each encoder cap ~35° off the shaft side and
    # mirror fore/aft between the two motors. Shaft up: they exit just under the floor, so a slot sits right above
    # each exit — right motor's toward the front, left motor's toward the back.
    y_brk = Y_OUT - BRK_INSET - BRK_BASE          # inner end of the bracket's base leg
    cuts += ybox(16, y_brk - 1.5, Z_RAIL0 - 1, Z_RAIL1 + 1, X_MOTOR + 3, X_MOTOR + 19)
    cuts += ybox(-(y_brk - 1.5), -16, Z_RAIL0 - 1, Z_RAIL1 + 1, X_MOTOR - 19, X_MOTOR - 3)
    # cap screws: left side only, M3×8 into M3 heat-set inserts pressed into the wall from outside (stop block behind
    # gives the depth). An M3×8 ends inside the insert, so the bore is the whole hole.
    zs = Z_LIP - CAP_SKIRT / 2
    for x in CAP_SCREW_X:
        cuts += cyl_y(x, zs, INSERT_M3[0] / 2, -(Y_OUT + 1), -(Y_OUT - INSERT_M3[1]))
    # zip-tie slot pairs up the left side (beside the PDB) for the power harness
    for z in (Z_TOP0 - 60, Z_TOP0 - 20):
        for yc in (-Y_IN + 3, -Y_IN + 9):
            cuts += ybox(yc - 1.5, yc + 1.5, z - 2, z + 2, X0 - 1, XB + 1)
    frame -= cuts
    return round_outside(frame)


def fillet_inside(shape):
    """Bay corners: R6 up at the deck, R3 at the floor (keeps the outer bracket screws' heads clear)."""
    try:
        edges = shape.edges().filter_by(Axis.X)
        top = [e for e in edges if abs(abs(e.center().Y) - Y_IN) < 0.01 and abs(e.center().Z - Z_TOP0) < 0.01]
        floor = [e for e in edges if abs(abs(e.center().Y) - Y_IN) < 0.01 and abs(e.center().Z - Z_RAIL1) < 0.01]
        shape = fillet(top, FILLET) if top else shape
        floor = [e for e in shape.edges().filter_by(Axis.X) if abs(abs(e.center().Y) - Y_IN) < 0.01 and abs(e.center().Z - Z_RAIL1) < 0.01]
        return fillet(floor, 3.0) if floor else shape
    except Exception as exc:  # fillets are cosmetic; never block the build on them
        print("inside fillet skipped:", exc)
        return shape


def round_outside(shape):
    """Match v1: R3 on the loop's outer corners, R2 along the outer front edges (back face = bed, sharp).
    Edges that won't take a fillet (next to a slot or insert hole) are skipped one at a time and reported."""
    tops = (Z_LIP, Z_LIP + T_CAP)

    def fillet_each(shape, pick, r, what):
        skipped = 0
        for _ in range(200):
            todo = [e for e in shape.edges() if pick(e)]
            if not todo:
                break
            try:
                return fillet(todo, r), skipped
            except Exception:
                pass
            # fall back to one at a time
            done_any = False
            for e in todo:
                try:
                    shape = fillet([e], r)
                    done_any = True
                    break
                except Exception:
                    continue
            if not done_any:
                skipped = len(todo)
                break
        if skipped:
            print(f"{what}: {skipped} edge(s) left sharp")
        return shape, skipped

    def corner(e):
        c = e.center()
        if not (e.geom_type == GeomType.LINE and abs(abs(e.tangent_at().X) - 1) < 1e-6):
            return False
        at_bottom = abs(abs(c.Y) - Y_OUT) < 0.01 and abs(c.Z - Z_RAIL0) < 0.01
        at_top = abs(abs(c.Y) - Y_OUT) < 0.01 and any(abs(c.Z - z) < 0.01 for z in tops)
        return at_bottom or at_top

    def rim(e):
        c = e.center()
        if abs(c.X - X1) > 0.01:      # front face only: the back face sits on the print bed and stays sharp
            return False
        if e.geom_type == GeomType.CIRCLE:
            return False
        if abs(abs(c.Y) - Y_OUT) < 0.01 or abs(abs(c.Y) - Y_OUT) < 0.01:
            return True
        if abs(c.Z - Z_RAIL0) < 0.01 or any(abs(c.Z - z) < 0.01 for z in tops):
            return abs(c.Y) > Y_IN - HOOD - 1 or abs(c.Z - Z_RAIL0) < 0.01 or c.Z > Z_LIP + T_CAP - 0.01
        return False

    shape, _ = fillet_each(shape, corner, 3.0, "outer corners R3")
    shape, _ = fillet_each(shape, rim, 2.0, "outer rim R2")
    return shape


def build_clip():
    """Left battery clip: covers the pack's left end (top + front), 2 M3×8 into inserts in the left wall.
    Prints upside down (top plate on the bed), no supports."""
    y1 = BAT_Y0 + CLIP_W
    top = ybox(-Y_OUT - 0.2 - T_CAP, y1, Z_LIP, Z_LIP + T_CAP, X0, X1)
    front = ybox(-Y_IN + 0.3, y1, Z_TOP1 + 0.3, Z_LIP, X1 - T_CAP, X1)
    skirt = ybox(-(Y_OUT + 0.2), -(Y_OUT + 0.2 + T_CAP), Z_LIP - CAP_SKIRT, Z_LIP, X0, X1)
    clip = top + front + skirt
    for x in CAP_SCREW_X:
        clip -= cyl_y(x, Z_LIP - CAP_SKIRT / 2, M3_CLEAR / 2, -(Y_OUT - 1), -(Y_OUT + T_CAP + 1))
    try:
        clip = fillet([e for e in clip.edges() if abs(e.center().Z - (Z_LIP + T_CAP)) < 0.01], 1.5)
    except Exception as exc:
        print("clip fillet skipped:", exc)
    return clip


# ---------------------------------------------------------------- purchased-part models for the assembly
def about_z(shape):
    """The -Y side's copy: same part turned 180° about the vertical axis through the gearbox axis."""
    return Pos(X_MOTOR, 0, 0) * Rot(0, 0, 180) * Pos(-X_MOTOR, 0, 0) * shape


def motor(side):
    m = import_step(HERE / "vendor/37d-gearmotor-50-70-encoder.step")
    # vendor: axis +Z (shaft out), face z=19.93, gearbox axis x=19.93 y=0, shaft offset toward -Y.
    # world: axis outward (vendor Z -> +Y), shaft offset up (vendor -Y -> +Z), vendor X -> +X.
    m = m.moved(Location((-19.93, 0, -19.93)))
    m = m.moved(Location(Plane(origin=(X_MOTOR, Y_FACE, Z_MOTOR), x_dir=(1, 0, 0), z_dir=(0, 1, 0))))
    return m if side > 0 else about_z(m)


def bracket(side):
    b = import_step(HERE / "vendor/37d-l-bracket.step")
    # vendor: face plate z 5.8..7.8 (motor on the -Z side), gearbox axis at x=-1 y=1, base leg outer face y=-19.8.
    # world: axis outward (+Y), base leg on top (vendor +Y -> world -Z), vendor X -> +X.
    b = b.moved(Location((1.0, -1.0, -5.8)))
    b = b.moved(Location(Plane(origin=(X_MOTOR, Y_FACE, Z_MOTOR), x_dir=(1, 0, 0), z_dir=(0, 1, 0))))
    return b if side > 0 else about_z(b)


def wheel(side):
    y_in = Y_OUT + 5.0     # clear of the M3 heads; hub sits on the outer end of the shaft
    w = cyl_y(X_MOTOR, Z_AXLE, WHEEL_R, side * y_in, side * (y_in + WHEEL_W))
    w -= cyl_y(X_MOTOR, Z_AXLE, WHEEL_R - 8, side * (y_in - 1), side * (y_in + WHEEL_W + 1))
    hub = cyl_y(X_MOTOR, Z_AXLE, 11, side * y_in, side * (y_in + WHEEL_W))
    spokes = cyl_y(X_MOTOR, Z_AXLE, WHEEL_R - 7.5, side * (y_in + 3), side * (y_in + 6))
    bore = cyl_y(X_MOTOR, Z_AXLE, 3.1, side * Y_IN, side * (y_in + WHEEL_W + 1))
    return w + hub + spokes - bore


def board(y, z, w, h, t, x0):
    return Pos(x0 + t / 2, y, z) * Box(t, w, h)


def assembly():
    parts = []

    def add(shape, label, color, mass):
        shape.label, shape.color = label, Color(color)
        parts.append((shape, label, mass))

    add(build_frame(), "frame", "#9aa3ad", None)
    add(build_clip(), "battery clip", "#7f8a96", None)
    for s, n in ((1, "R"), (-1, "L")):
        add(motor(s), "motor_" + n, "#7d6e5d", 205)
        add(bracket(s), "bracket_" + n, "#c9ccd1", 16)
        add(wheel(s), "wheel_" + n, "#2b2b2b", 40)
    bat_z = Z_TOP1 + BATTERY[2] / 2
    bat_x = XB + BAT_CLEAR + BATTERY[0] / 2
    add(Pos(bat_x, BAT_SHIFT, bat_z) * Box(*BATTERY), "battery", "#e08a2e", 355)
    add(board(BB_Y, BB_Z0 + BREADBOARD[1] / 2, BREADBOARD[0], BREADBOARD[1], BREADBOARD[2], XB), "breadboard", "#f2f0e8", 30)
    add(board(BB_Y, BB_Z0 + BREADBOARD[1] / 2, 51, 28, 13, XB + BREADBOARD[2]), "esp32", "#1d3b6e", 12)
    cy = board(CY_Y, CY_Z, CYTRON[0], CYTRON[1], 1.6, XB + 5)
    cy += Pos(XB + 5 + 1.6 + 6, CY_Y - CYTRON[0] / 2 + 5, CY_Z) * Box(12, 10, 46)   # terminal block
    add(cy, "cytron", "#1f1f1f", 34)
    add(board(PDB_Y, PDB_Z, PDB[0], PDB[1], 6, XB + 5), "pdb (optional)", "#3c3c46", 12)
    add(Pos(IMU_X, IMU_Y, Z_RAIL1 + 4 + 0.8) * Box(IMU[0], IMU[1], 1.6), "imu", "#c0392b", 3)
    add(Pos(0, 0, Z_RAIL1 + 30) * Box(1, 1, 1), "wiring (lumped)", "#000000", 45)
    return parts


def mass_properties(parts):
    density = 1.24e-3 * 0.85   # PLA g/mm³, ~solid at these wall thicknesses
    total_m, mx, my, mz, iy_axle = 0.0, 0.0, 0.0, 0.0, 0.0
    rows = []
    for shape, label, mass in parts:
        vol = shape.volume
        m = mass if mass is not None else vol * density
        c = shape.center(CenterOf.MASS) if vol > 1 else shape.center(CenterOf.BOUNDING_BOX)
        rows.append((label, round(m), round(c.X, 1), round(c.Y, 1), round(c.Z, 1)))
        total_m += m
        mx, my, mz = mx + m * c.X, my + m * c.Y, mz + m * c.Z
        iy_axle += m * ((c.X - X_MOTOR) ** 2 + (c.Z - Z_AXLE) ** 2)
    com_x, com_y, com_z = mx / total_m, my / total_m, mz / total_m
    l = math.hypot(com_x - X_MOTOR, com_z - Z_AXLE) / 1000
    return {
        "parts": rows,
        "mass_g": round(total_m),
        "com_x_mm": round(com_x, 1),
        "com_y_mm": round(com_y, 1),
        "com_z_mm": round(com_z, 1),
        "com_above_axle_mm": round(com_z - Z_AXLE, 1),
        "com_ahead_of_axle_mm": round(com_x - X_MOTOR, 1),
        "rest_trim_deg": round(math.degrees(math.atan2(com_x - X_MOTOR, com_z - Z_AXLE)), 2),
        "pitch_inertia_about_axle_kgm2_pointmass": round(iy_axle * 1e-9, 5),
        "locked_wheel_pole_hz": round(math.sqrt(total_m / 1000 * 9.81 * l / (iy_axle * 1e-9)) / (2 * math.pi), 3),
    }


def screw_access(parts):
    """Anything inside the column above each bracket screw (Ø9, SCREW_ACCESS tall) blocks the L-key."""
    blocked = []
    for h in bracket_holes():
        c = h.center()
        col = cyl_z(c.X, c.Y, 4.5, Z_RAIL1 + 0.2, Z_RAIL1 + SCREW_ACCESS)
        for shape, label, _ in parts:
            if shape.volume > 1 and shape.bounding_box().overlaps(col.bounding_box()):
                try:
                    v = (shape & col).volume
                except Exception:
                    continue
                if v > 0.5:
                    blocked.append([round(c.X, 1), round(c.Y, 1), label])
    return blocked


def interferences(parts):
    hits = []
    solid = [(s, l) for s, l, _ in parts if s.volume > 1]
    for i in range(len(solid)):
        for j in range(i + 1, len(solid)):
            a, la = solid[i]
            b, lb = solid[j]
            if not a.bounding_box().overlaps(b.bounding_box()):
                continue
            try:
                v = (a & b).volume
            except Exception:
                continue
            if v > 1.0:
                hits.append([la, lb, round(v, 1)])
    return hits


def main():
    OUT.mkdir(exist_ok=True)
    parts = assembly()
    frame = parts[0][0]
    bb = frame.bounding_box()
    print("frame bbox", bb.size, "valid", frame.is_valid, "volume cm3", round(frame.volume / 1000, 1))

    export_step(frame, OUT / "frame.step")
    export_stl(frame, OUT / "frame.stl", tolerance=0.05, angular_tolerance=0.2)
    clip = next(p[0] for p in parts if p[1] == "battery clip")
    export_step(clip, OUT / "battery_clip.step")
    export_stl(clip, OUT / "battery_clip.stl", tolerance=0.05, angular_tolerance=0.2)
    asm = Compound(children=[p[0] for p in parts], label="randal")
    export_gltf(asm, str(OUT / "assembly.glb"), binary=True, linear_deflection=0.1, angular_deflection=0.3)

    parts_dir = OUT / "parts"
    parts_dir.mkdir(exist_ok=True)
    for f in parts_dir.glob("*.stl"):
        f.unlink()
    manifest = []
    for i, (shape, label, _) in enumerate(parts):
        if shape.volume <= 1:
            continue
        f = parts_dir / f"{i:02d}.stl"
        export_stl(shape, f, tolerance=0.1, angular_tolerance=0.3)
        manifest.append({"file": f.name, "label": label, "color": list(tuple(shape.color))[:3]})
    (parts_dir / "manifest.json").write_text(json.dumps(manifest))

    props = mass_properties(parts)
    props["frame_bbox_mm"] = [round(v, 1) for v in (bb.size.X, bb.size.Y, bb.size.Z)]
    props["print_footprint_mm"] = [round(bb.size.Y, 1), round(bb.size.Z, 1), round(bb.size.X, 1)]
    props["axle"] = {"x": X_MOTOR, "z": Z_AXLE}
    over = max(abs(s.bounding_box().max.Y) for s, l, _ in parts if l.startswith("wheel"))
    props["width_over_wheels_mm"] = round(2 * over, 1)
    props["overall_height_mm"] = round(max(s.bounding_box().max.Z for s, _, _ in parts), 1)
    props["ground_clearance_mm"] = round(min(s.bounding_box().min.Z for s, l, _ in parts if not l.startswith("wheel")), 1)
    props["interferences"] = interferences(parts)
    props["bracket_screws_blocked"] = screw_access(parts)
    (OUT / "summary.json").write_text(json.dumps(props, indent=2))
    print(json.dumps({k: v for k, v in props.items() if k != "parts"}, indent=2))


if __name__ == "__main__":
    main()
