"""Independent check of the v3 print files - reads the STL files themselves, not the generator's numbers.

Run: python3 print/v3/verify_v3.py      (exit code 1 if any check fails)

1. Every part: watertight (each edge used exactly twice, opposite directions), outward normals, fits 250 mm.
2. Printability in the orientation the FILE is in: area of down-facing surfaces that are not on the bed
   (overhang steeper than 45 deg from vertical -> needs support or sags).
3. Hydrostatics cross-check: displaced volume of the demihull MESH below each waterline, computed by clipping
   the triangles (divergence theorem, apex on the waterplane), against data/v3_hydrostatics.json.
4. Deck fit: slot width measured on the deck mesh vs hull width measured on the hull mesh.
5. CFD file: number of separate shells and the smallest gap between them.
"""
import json
import math
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MAX_MM = 250.0
OVERHANG_COS = math.cos(math.radians(45))   # down-facing steeper than 45 deg from vertical


def load(path):
    b = path.read_bytes()
    n = struct.unpack("<I", b[80:84])[0]
    return [tuple(struct.unpack("<3f", b[84 + 50 * i + 12 + 12 * k:84 + 50 * i + 24 + 12 * k]) for k in range(3))
            for i in range(n)]


def key(p):
    return tuple(round(c, 4) for c in p)


def watertight(tris):
    edges = {}
    for t in tris:
        for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            e = (key(a), key(b))
            edges[e] = edges.get(e, 0) + 1
    return all(cnt == 1 and edges.get((e[1], e[0]), 0) == 1 for e, cnt in edges.items())


def cross(u, v):
    return (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def volume(tris, apex=(0.0, 0.0, 0.0)):
    v = 0.0
    for a, b, c in tris:
        a, b, c = sub(a, apex), sub(b, apex), sub(c, apex)
        v += a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0]) + a[2] * (b[0] * c[1] - b[1] * c[0])
    return v / 6


def bbox(tris):
    pts = [p for t in tris for p in t]
    lo = [min(p[k] for p in pts) for k in range(3)]
    hi = [max(p[k] for p in pts) for k in range(3)]
    return lo, hi


def overhang_area(tris, bed_z):
    """Area (mm^2) of faces pointing down by more than 45 deg from vertical, excluding faces lying on the bed."""
    area = 0.0
    for a, b, c in tris:
        n = cross(sub(b, a), sub(c, a))
        s = math.sqrt(sum(x * x for x in n)) or 1.0
        if n[2] / s < -OVERHANG_COS and max(a[2], b[2], c[2]) > bed_z + 0.2:
            area += s / 2
    return area


def clip_below(tri, z0):
    """Part of a triangle below z = z0, as a list of triangles."""
    below = [p for p in tri if p[2] <= z0]
    if len(below) == 3:
        return [tri]
    if not below:
        return []
    poly = []
    for i in range(3):
        p, q = tri[i], tri[(i + 1) % 3]
        if p[2] <= z0:
            poly.append(p)
        if (p[2] <= z0) != (q[2] <= z0):
            f = (z0 - p[2]) / (q[2] - p[2])
            poly.append(tuple(p[k] + f * (q[k] - p[k]) for k in range(3)))
    return [(poly[0], poly[i], poly[i + 1]) for i in range(1, len(poly) - 1)]


def volume_below(tris, z0):
    """Closed mesh volume under the plane z = z0: the missing cap lies in the plane, so with the apex on the
    plane its tetrahedra have zero volume and the clipped surface alone gives the exact volume."""
    apex = (0.0, 0.0, z0)
    return volume([c for t in tris for c in clip_below(t, z0)], apex)


def shells(tris):
    parent = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for t in tris:
        ks = [key(p) for p in t]
        for k in ks[1:]:
            parent[find(k)] = find(ks[0])
    groups = {}
    for t in tris:
        groups.setdefault(find(key(t[0])), []).append(t)
    return list(groups.values())


def width_at(tris, z0, x0, x1):
    """Max y-extent of mesh vertices/edge crossings at height z0 within x0..x1 (mm)."""
    ys = []
    for t in tris:
        for i in range(3):
            p, q = t[i], t[(i + 1) % 3]
            if (p[2] - z0) * (q[2] - z0) <= 0 and p[2] != q[2]:
                f = (z0 - p[2]) / (q[2] - p[2])
                x = p[0] + f * (q[0] - p[0])
                if x0 <= x <= x1:
                    ys.append(p[1] + f * (q[1] - p[1]))
    return (min(ys), max(ys)) if ys else None


def point_tri(p, tri):
    """Distance from point p to triangle tri (closest-point regions, Ericson 'Real-Time Collision Detection')."""
    a, b, c = tri
    dot = lambda u, v: u[0] * v[0] + u[1] * v[1] + u[2] * v[2]
    ab, ac, ap = sub(b, a), sub(c, a), sub(p, a)
    d1, d2 = dot(ab, ap), dot(ac, ap)
    if d1 <= 0 and d2 <= 0:
        q = a
    else:
        bp = sub(p, b); d3, d4 = dot(ab, bp), dot(ac, bp)
        cp = sub(p, c); d5, d6 = dot(ab, cp), dot(ac, cp)
        vc, vb, va = d1 * d4 - d3 * d2, d5 * d2 - d1 * d6, d3 * d6 - d5 * d4
        if d3 >= 0 and d4 <= d3:
            q = b
        elif vc <= 0 and d1 >= 0 and d3 <= 0:
            q = tuple(a[k] + d1 / (d1 - d3) * ab[k] for k in range(3))
        elif d6 >= 0 and d5 <= d6:
            q = c
        elif vb <= 0 and d2 >= 0 and d6 <= 0:
            q = tuple(a[k] + d2 / (d2 - d6) * ac[k] for k in range(3))
        elif va <= 0 and (d4 - d3) >= 0 and (d5 - d6) >= 0:
            w = (d4 - d3) / ((d4 - d3) + (d5 - d6))
            q = tuple(b[k] + w * (c[k] - b[k]) for k in range(3))
        else:
            den = 1 / (va + vb + vc)
            v, w = vb * den, vc * den
            q = tuple(a[k] + ab[k] * v + ac[k] * w for k in range(3))
    return math.dist(p, q)


def main():
    fails = []
    report = []
    parts = sorted(HERE.glob("*.stl"))
    for p in parts:
        t = load(p)
        lo, hi = bbox(t)
        size = [hi[k] - lo[k] for k in range(3)]
        cfd = "CFD" in p.name
        n_sh = len(shells(t))
        ok_w = all(watertight(s) for s in shells(t))
        vol = sum(volume(s) for s in shells(t))
        over = overhang_area(t, lo[2])
        line = (f"{p.name}: {size[0]:.1f} x {size[1]:.1f} x {size[2]:.1f} mm, {n_sh} shell(s), "
                f"watertight={ok_w}, volume {vol/1000:.1f} cm3, overhang >45deg not on bed: {over/100:.1f} cm2")
        report.append(line)
        if not ok_w:
            fails.append(f"{p.name}: not watertight")
        if vol <= 0:
            fails.append(f"{p.name}: normals point inward")
        if max(size) > MAX_MM + 1e-6:
            fails.append(f"{p.name}: exceeds {MAX_MM} mm")
        if not cfd and over > 50:   # > 0.5 cm2 of unsupported down-facing surface in the file's own orientation
            fails.append(f"{p.name}: {over/100:.1f} cm2 overhang in the file orientation - export it in print orientation")

    # 3. hydrostatics: mesh vs table (demihull in sailing orientation = keel at z_min)
    hull_files = [p for p in parts if "demihull" in p.name]
    if hull_files:
        hull = load(hull_files[0])
        lo, hi = bbox(hull)
        if overhang_area(hull, lo[2]) > overhang_area([tuple((x, y, hi[2] + lo[2] - z) for x, y, z in reversed(t)) for t in hull], lo[2]):
            sail = hull
        else:   # file is keel-up (print orientation): flip to sailing
            sail = [tuple((x, y, hi[2] + lo[2] - z) for x, y, z in reversed(t)) for t in hull]
        tab = json.loads((ROOT / "data" / "v3_hydrostatics.json").read_text())["configs"]["1 hull (monohull test)"]["rows"]
        worst = 0.0
        for row in tab[9::10]:
            T, V_tab = row[0] * 1000, row[1] * 1e9
            V_mesh = volume_below(sail, lo[2] + T)
            err = (V_mesh - V_tab) / V_tab
            worst = max(worst, abs(err))
        report.append(f"hydrostatics: mesh volume vs table at {len(tab[9::10])} draughts, worst difference {worst*100:.2f} %")
        if worst > 0.01:
            fails.append(f"hydrostatic table differs from the hull mesh by {worst*100:.2f} %")
        # 4. deck fit: hull width over the deck span, deck slot width at mid-flange height
        h_w = width_at(sail, hi[2] - lo[2] - 6 + lo[2], 30, 150)
        for d in [p for p in parts if "deck_gap" in p.name]:
            deck = load(d)
            gap = float(d.stem.split("gap")[-1])
            c = (gap + (h_w[1] - h_w[0])) / 2
            ys = width_at(deck, 9.0, 1, 149)       # flange zone (plate 0-3 mm, flanges 3-15 mm)
            inner = sorted(y for y in {round(v, 3) for t in deck for p in t for v in [p[1]]} if c - 30 < y < c + 30)
            slot = inner[-2] - inner[1] if len(inner) >= 4 else float("nan")
            clear = (slot - (h_w[1] - h_w[0])) / 2
            report.append(f"{d.name}: slot {slot:.2f} mm for hull {h_w[1]-h_w[0]:.2f} mm -> clearance {clear:.2f} mm per side")
            if not 0.2 <= clear <= 0.6:
                fails.append(f"{d.name}: clearance {clear:.2f} mm per side outside 0.2-0.6 mm")

    # 5. CFD file: true clearance = smallest distance from any vertex of one shell to the surface of another
    for p in [p for p in parts if "CFD" in p.name]:
        sh = sorted(shells(load(p)), key=len)
        gap = min(min(point_tri(v, t) for t in other for v in {q for s in [small] for tr in s for q in tr})
                  for i, small in enumerate(sh) for other in sh[i + 1:]) if len(sh) > 1 else float("inf")
        report.append(f"{p.name}: {len(sh)} shells, smallest clearance between shells {gap:.2f} mm")
        if gap < 0.5:
            fails.append(f"{p.name}: shells only {gap:.2f} mm apart - CFD meshers may fail or need huge meshes")

    print("\n".join(report))
    print("\nFAILED:\n- " + "\n- ".join(fails) if fails else "\nALL CHECKS PASSED")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
