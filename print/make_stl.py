"""Generate printable STL hulls that match the app's hull models exactly (box pontoons, deck at the top).

Run: python3 print/make_stl.py   -> writes the .stl files next to this script and prints a check report.

Why boxes: the app's hydrostatics assume wall-sided rectangular pontoons, so a box hull is the one shape whose
tank results can confirm or falsify the calculations directly (Test A/B/C in the Validation tab).

Each hull is ONE watertight solid: a constant cross-section (y, z) extruded along the length (x).
v2 catamaran: two 52 x 52 mm pontoons joined by a 3 mm deck slab -> 235 x 160 x 55 mm, printed deck-down
(no bridging, no supports). v1 monohull: 235 x 104 x 55 mm box, printed flat bottom down.
"""
import struct
from pathlib import Path

L = 235.0          # mm, length (fits the 250 x 250 x 250 mm print limit)
DEPTH = 55.0       # mm, keel to deck top = app "Hull depth"
DECK_T = 3.0       # mm, catamaran deck slab thickness
PONTOON_B = 52.0   # mm
GAP = 56.0         # mm, clear gap between catamaran pontoons
MONO_B = 104.0     # mm


def triangulate(poly):
    """Ear clipping for a simple polygon given counter-clockwise. Returns index triples."""
    idx = list(range(len(poly)))
    tris = []

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    def inside(p, a, b, c):
        return cross(a, b, p) >= 0 and cross(b, c, p) >= 0 and cross(c, a, p) >= 0

    while len(idx) > 3:
        for k in range(len(idx)):
            i, j, m = idx[k - 1], idx[k], idx[(k + 1) % len(idx)]
            a, b, c = poly[i], poly[j], poly[m]
            if cross(a, b, c) <= 0:
                continue
            if any(inside(poly[q], a, b, c) for q in idx if q not in (i, j, m)):
                continue
            tris.append((i, j, m))
            idx.pop(k)
            break
        else:
            raise ValueError("polygon is not simple / not counter-clockwise")
    tris.append(tuple(idx))
    return tris


def extrude(section, length):
    """Extrude a CCW (y, z) polygon along x from 0 to length. Returns outward-facing triangles in 3D."""
    n = len(section)
    p0 = [(0.0, y, z) for y, z in section]
    p1 = [(length, y, z) for y, z in section]
    tris = []
    for i, j, m in triangulate(section):
        tris.append((p1[i], p1[j], p1[m]))          # +x cap (CCW seen from +x)
        tris.append((p0[i], p0[m], p0[j]))          # -x cap (reversed)
    for i in range(n):
        j = (i + 1) % n
        tris.append((p0[i], p0[j], p1[j]))          # side walls, outward for a CCW section
        tris.append((p0[i], p1[j], p1[i]))
    return tris


def normal(a, b, c):
    u = [b[k] - a[k] for k in range(3)]
    v = [c[k] - a[k] for k in range(3)]
    n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
    s = sum(x * x for x in n) ** 0.5 or 1.0
    return tuple(x / s for x in n)


def write_stl(path, tris, name):
    with open(path, "wb") as f:
        f.write(name.encode()[:80].ljust(80, b" "))
        f.write(struct.pack("<I", len(tris)))
        for a, b, c in tris:
            f.write(struct.pack("<12fH", *normal(a, b, c), *a, *b, *c, 0))


def check(tris):
    """Watertight check (every edge shared by exactly 2 triangles, opposite directions), volume, area, bbox."""
    edges = {}
    for a, b, c in tris:
        for e in ((a, b), (b, c), (c, a)):
            edges[e] = edges.get(e, 0) + 1
    manifold = all(edges.get((e[1], e[0]), 0) == cnt == 1 for e, cnt in edges.items())
    vol = sum((a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0])
               + a[2] * (b[0] * c[1] - b[1] * c[0])) for a, b, c in tris) / 6
    area = 0.0
    for a, b, c in tris:
        u = [b[k] - a[k] for k in range(3)]
        v = [c[k] - a[k] for k in range(3)]
        cx = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
        area += 0.5 * sum(x * x for x in cx) ** 0.5
    pts = [p for t in tris for p in t]
    bbox = [max(p[k] for p in pts) - min(p[k] for p in pts) for k in range(3)]
    return manifold, vol, area, bbox


def pla_mass_g(vol_mm3, area_mm2, shell_mm=1.2, infill=0.10, rho=1.24e-3):
    """Rough slicer-style estimate: solid shell over the surface + sparse infill inside (g)."""
    shell = area_mm2 * shell_mm
    return (shell + max(vol_mm3 - shell, 0) * infill) * rho


H = PONTOON_B + GAP / 2        # centreline -> outer edge of a pontoon (80 mm)
# Catamaran cross-section, deck-down print orientation: z = 0 is the DECK TOP, pontoon keels at z = 55.
cat_section = [(-H, 0), (H, 0), (H, DEPTH), (GAP / 2, DEPTH), (GAP / 2, DECK_T), (-GAP / 2, DECK_T),
               (-GAP / 2, DEPTH), (-H, DEPTH)]
mono_section = [(-MONO_B / 2, 0), (MONO_B / 2, 0), (MONO_B / 2, DEPTH), (-MONO_B / 2, DEPTH)]

if __name__ == "__main__":
    out = Path(__file__).parent
    for fname, section, label, expect in (
        ("arova_v2_catamaran.stl", cat_section, "Revised (v2) catamaran - print DECK DOWN",
         L * (2 * PONTOON_B * (DEPTH - DECK_T) + 2 * H * DECK_T)),
        ("arova_v1_monohull.stl", mono_section, "Baseline (v1) monohull - print flat bottom down",
         L * MONO_B * DEPTH)):
        tris = extrude(section, L)
        ok, vol, area, bbox = check(tris)
        assert ok, f"{fname}: mesh is not watertight"
        assert abs(vol - expect) < 1e-3 * expect, (fname, vol, expect)
        assert max(bbox) <= 250, f"{fname}: exceeds 250 mm print limit"
        write_stl(out / fname, tris, label)
        print(f"{fname}: watertight={ok}, size {bbox[0]:.0f} x {bbox[1]:.0f} x {bbox[2]:.0f} mm, "
              f"solid volume {vol/1000:.0f} cm³, est. PLA ~{pla_mass_g(vol, area):.0f} g at 10% infill "
              f"(~{pla_mass_g(vol, area, infill=0.05):.0f} g at 5%), {len(tris)} triangles")
