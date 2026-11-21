"""Lidded electronics box for the deck centre (optional alternative to the hull-top pockets).

Run: python3 print/v3/make_ebox.py  -> arova_v3_ebox_base.stl, arova_v3_ebox_lid.stl

Inside 75 x 60 x 24 mm: a 2xAA holder (60 x 35 x 20) and an Arduino Nano (45 x 18) side by side, MPU6050 on top
of the holder or beside the Nano. Walls and floor 2 mm. The lid's lip drops 5 mm inside the box with 0.25 mm
clearance per side (press fit; tape the seam for splash). Both parts print flat face down without supports.
Drill one 5 mm cable hole where needed. Each part is ONE closed surface (no overlapping bodies).
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from make_stl import write_stl, check  # noqa: E402

IN_L, IN_W, IN_H, WALL = 75.0, 60.0, 24.0, 2.0
LIP_H, LIP_T, CLR = 5.0, 1.6, 0.25


def corners(r, z):
    x0, y0, x1, y1 = r
    return [(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)]       # counter-clockwise seen from +z


def face(r, z, up):
    a, b, c, d = corners(r, z)
    return [(a, b, c), (a, c, d)] if up else [(a, c, b), (a, d, c)]


def ring(r_out, r_in, z, up):
    """Flat frame between two nested rectangles at height z."""
    o, i = corners(r_out, z), corners(r_in, z)
    t = []
    for k in range(4):
        q = (o[k], o[(k + 1) % 4], i[(k + 1) % 4], i[k])
        t += [(q[0], q[1], q[2]), (q[0], q[2], q[3])] if up else [(q[0], q[2], q[1]), (q[0], q[3], q[2])]
    return t


def wall(r, z0, z1, outward):
    """Vertical sides of rectangle r from z0 to z1; outward=False for an inner (cavity) wall."""
    lo, hi = corners(r, z0), corners(r, z1)
    t = []
    for k in range(4):
        a, b, c, d = lo[k], lo[(k + 1) % 4], hi[(k + 1) % 4], hi[k]
        t += [(a, b, c), (a, c, d)] if outward else [(a, c, b), (a, d, c)]
    return t


L, W, H = IN_L + 2 * WALL, IN_W + 2 * WALL, IN_H + WALL
OUT = (0.0, 0.0, L, W)
IN = (WALL, WALL, L - WALL, W - WALL)
# Open-top box: outer bottom, outer sides, top rim, inner sides, inner floor
base = face(OUT, 0, False) + wall(OUT, 0, H, True) + ring(OUT, IN, H, True) + wall(IN, WALL, H, False) + face(IN, WALL, True)
# Lid (printed plate down): plate bottom + sides, plate top outside the lip, lip outer/inner walls, lip top, plate top inside
LO = (WALL + CLR, WALL + CLR, L - WALL - CLR, W - WALL - CLR)
LI = (LO[0] + LIP_T, LO[1] + LIP_T, LO[2] - LIP_T, LO[3] - LIP_T)
lid = (face(OUT, 0, False) + wall(OUT, 0, WALL, True) + ring(OUT, LO, WALL, True) + wall(LO, WALL, WALL + LIP_H, True)
       + ring(LO, LI, WALL + LIP_H, True) + wall(LI, WALL, WALL + LIP_H, False) + face(LI, WALL, True))

if __name__ == "__main__":
    out = Path(__file__).parent
    for name, tris in (("arova_v3_ebox_base.stl", base), ("arova_v3_ebox_lid.stl", lid)):
        ok, vol, _, bb = check(tris)
        assert ok and vol > 0, (name, ok, vol)
        write_stl(out / name, tris, name.replace(".stl", ""))
    print(f"base {L:.0f} x {W:.0f} x {H:.0f} mm, lid {L:.0f} x {W:.0f} x {WALL + LIP_H:.0f} mm "
          f"(inside {IN_L:.0f} x {IN_W:.0f} x {IN_H:.0f}, lip clearance {CLR} mm/side)")
