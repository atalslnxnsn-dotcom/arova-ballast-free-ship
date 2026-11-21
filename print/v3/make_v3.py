"""Arova v3 "Wave-piercer" modular catamaran: printable STLs + exact hydrostatics.

Run: python3 print/v3/make_v3.py
Writes demihull + three deck STLs next to this file and prints a check / hydrostatic report.

Design idea (see DESIGN_BRIEF.md):
- Two identical slender demihulls (235 x 50 x 70 mm), fine pointed bow, rounded bilges, keel rocker at the bow.
  Sides are vertical through the whole waterline band, so the app's wall-sided model stays close to exact.
- One flat deck that clips over both hulls with saddle flanges. Three decks = hull gaps of 40 / 70 / 100 mm,
  so the same hulls test narrow vs wide catamaran, and one hull alone is the monohull baseline.
All parts are plain closed solids: no holes, no supports, nothing that can leak.
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from make_stl import check, extrude, write_stl, pla_mass_g  # reuse the team's tested STL helpers

L, B, D = 235.0, 60.0, 70.0          # mm demihull length, beam, depth. v4: B 50 -> 60 (sweep: load limit 786 -> 918 g, safe wave H 30 -> 35 mm, off-centre heel 5.6 -> 3.7 deg)
BILGE_R = 6.0                         # mm bilge radius
BOW_START, ROCKER_START = 150.0, 185.0  # mm from transom: where the bow taper / keel rise begin
ROCKER_H = 16.0                       # mm keel rise at the bow tip
STERN_B = 40.0                        # mm transom width
TIP_B = 2.0                           # mm bow tip width (printable, not a knife edge)
DECK_X0, DECK_X1, DECK_T = 27.5, 177.5, 2.0   # deck span (centre on the LCB, ~102.5 mm); 2 mm plate: 400 g point load mid-gap -> ~1 mm sag, 2.9 MPa (10x margin)
FLANGE_H, FLANGE_T, FIT = 12.0, 2.4, 0.3      # saddle flange depth, thickness, side clearance
TOP_CHAMFER = 0.8                     # mm, hull top edges (print-bed edges): elephant-foot relief for the deck fit
GAPS = (40.0, 70.0, 100.0)            # mm clear gap between hulls
N_ST, N_ARC = 80, 6                   # stations along x, points per bilge arc
PLA_RHO_HULL_SHELL = 1.2              # mm shell for mass estimate (3 walls: watertight hulls)
CFD_GAP = 100.0                       # mm, competition configuration exported as one assembly for the judges' CFD
CRADLE = dict(inner=22.5, wall=2.0, base=2.0, height=12.0, length=60.0)  # MPU-6050 (21 mm) / Nano (18 mm) slide-in sled
# Embedded electronics: an open pocket in the top face of each demihull, closed from above by the deck.
# It is a dent in the outer surface - the hull's sealed air volume stays closed. Centred under the deck/LCB.
# 64 x 40 x 22 mm fits a 2xAA holder (60 x 35 x 20) in one hull and Nano + MPU6050 (+ mini breadboard) in the other.
POCKET = dict(x0=70.5, x1=134.5, w=40.0, d=22.0)


def half_beam(x):
    if x < 25:                                   # gentle transom taper
        return STERN_B / 2 + (B - STERN_B) / 2 * (x / 25) ** 0.5
    if x <= BOW_START:
        return B / 2
    t = (x - BOW_START) / (L - BOW_START)        # 0..1 over the bow
    return max(TIP_B / 2, B / 2 * (1 - t ** 1.8))  # fine entry, convex waterline


def keel(x):
    return 0.0 if x <= ROCKER_START else ROCKER_H * ((x - ROCKER_START) / (L - ROCKER_START)) ** 2


def section(x):
    """Closed (y, z) section, counter-clockwise seen from +x (convex except the top pocket notch)."""
    b, zk = half_beam(x), keel(x)
    r = min(BILGE_R, b * 0.8, (D - zk) * 0.3)
    pts = []
    for i in range(N_ARC):                       # starboard bilge: bottom -> side
        a = -math.pi / 2 + (math.pi / 2) * i / (N_ARC - 1)
        pts.append((b - r + r * math.cos(a), zk + r + r * math.sin(a)))
    c = min(TOP_CHAMFER, b * 0.4)                # 45 deg chamfer on the top edges = the edges on the print bed:
    # top edge with the electronics pocket: same vertex count at every station (zero depth outside the pocket)
    inside = POCKET["x0"] <= x <= POCKET["x1"]
    w = POCKET["w"] / 2 if inside else max(min(POCKET["w"] / 2, b - c - 2), (b - c) * 0.3)
    d = POCKET["d"] if inside else 0.0
    pts += [(b, D - c), (b - c, D), (w, D), (w, D - d), (-w, D - d), (-w, D), (-b + c, D), (-b, D - c)]
    for i in range(N_ARC):                       # port bilge: side -> bottom
        a = math.pi + (math.pi / 2) * i / (N_ARC - 1)
        pts.append((-b + r + r * math.cos(a), zk + r + r * math.sin(a)))
    return pts


def loft():
    eps = 0.05                                   # extra stations: vertical pocket end walls
    xs = sorted(set([L * (i / (N_ST - 1)) for i in range(N_ST)]
                    + [POCKET["x0"] - eps, POCKET["x0"], POCKET["x1"], POCKET["x1"] + eps]))
    secs = [[(x, y, z) for y, z in section(x)] for x in xs]
    n = len(secs[0])
    tris = []
    for s0, s1 in zip(secs, secs[1:]):
        for i in range(n):
            j = (i + 1) % n
            tris += [(s0[i], s1[j], s0[j]), (s0[i], s1[i], s1[j])]
    for k in range(1, n - 1):                    # end caps (no pocket there, so convex): fans
        tris.append((secs[0][0], secs[0][k], secs[0][k + 1]))
        tris.append((secs[-1][0], secs[-1][k + 1], secs[-1][k]))
    # drop zero-area triangles from the zero-depth pocket points (repeated vertices); the mesh stays watertight
    tris = [t for t in tris if len({tuple(round(c, 9) for c in p) for p in t}) == 3]
    return tris


def flip_if_inside_out(tris):
    _, vol, _, _ = check(tris)
    return tris if vol > 0 else [(a, c, b) for a, b, c in tris]


def deck_section(gap):
    """Deck cross-section in print orientation (plate on the bed at z=0, flanges pointing up)."""
    c = (gap + B) / 2                            # centreline -> hull centre
    i0, i1 = c - B / 2 - FIT, c + B / 2 + FIT    # inner/outer hull faces incl. clearance
    W = i1 + FLANGE_T                            # half overall width
    T, H = DECK_T, DECK_T + FLANGE_H
    right = [(W, 0), (W, H), (i1, H), (i1, T), (i0, T), (i0, H), (i0 - FLANGE_T, H), (i0 - FLANGE_T, T)]
    left = [(-y, z) for y, z in reversed(right)]
    return [(-W, 0), (W, 0)] + right[1:] + left[:-1]


def cradle_section():
    """U-channel for the electronics, printed base down; boards slide in from the end and sit above the water."""
    h, t, b = CRADLE["height"], CRADLE["wall"], CRADLE["base"]
    w = CRADLE["inner"] / 2 + t
    return [(-w, 0), (w, 0), (w, h), (w - t, h), (w - t, b), (-w + t, b), (-w + t, h), (-w, h)]


def moved(tris, f):
    """Apply a point map to every vertex; fix the winding if the map mirrors the part."""
    return flip_if_inside_out([tuple(f(*p) for p in t) for t in tris])


def assembly(gap):
    """Two hulls + deck in sailing position, one STL (three closed shells) for the judges' CFD.
    The deck is lifted 0.1 mm so no faces coincide; flanges keep their 0.3 mm side clearance."""
    c = (gap + B) / 2
    hull = flip_if_inside_out(loft())
    deck = flip_if_inside_out(extrude(deck_section(gap), DECK_X1 - DECK_X0))
    parts = [moved(hull, lambda x, y, z, s=s: (x, y + s * c, z)) for s in (1, -1)]
    parts.append(moved(deck, lambda x, y, z: (x + DECK_X0, y, D + DECK_T + 0.1 - z)))
    return parts


# ---------- exact hydrostatics by section integration ----------
def clip_below(poly, t):
    out = []
    for k in range(len(poly)):
        p, q = poly[k], poly[(k + 1) % len(poly)]
        pin, qin = p[1] <= t, q[1] <= t
        if pin:
            out.append(p)
        if pin != qin:
            f = (t - p[1]) / (q[1] - p[1])
            out.append((p[0] + f * (q[0] - p[0]), t))
    return out


def area_cz(poly):
    a = cz = 0.0
    for k in range(len(poly)):
        (y0, z0), (y1, z1) = poly[k], poly[(k + 1) % len(poly)]
        cr = y0 * z1 - y1 * z0
        a += cr
        cz += (z0 + z1) * cr
    return a / 2, (cz / (3 * a) if a else 0.0)


def hydro(T, gap, n_hulls=2, dx=0.5):
    """Volume, KB, waterplane area and transverse inertia at draft T (mm units) by integrating stations."""
    c = (gap + B) / 2 if n_hulls == 2 else 0.0
    V = M = Awp = It = Il = Mx = 0.0
    xs = [k * dx for k in range(int(L / dx) + 1)]
    for x in xs:
        a, cz = area_cz(clip_below(section(x), T))
        w = 2 * half_beam(x) if T > keel(x) + min(BILGE_R, half_beam(x) * 0.8) else 0.0
        V += a * dx
        M += a * cz * dx
        Awp += w * dx
        It += (w ** 3 / 12 + w * c * c) * dx
        Mx += w * x * dx
    lcf = Mx / Awp if Awp else 0
    Il = sum((2 * half_beam(x) if T > keel(x) + 3 else 0) * (x - lcf) ** 2 * dx for x in xs)
    k = n_hulls
    return dict(V=k * V, KB=M / V if V else 0, Awp=k * Awp, It=k * It if k == 2 else It, Il=k * Il)


def draft_for(mass_g, gap, n_hulls=2, rho=1.0):
    vol = mass_g / rho * 1000                    # mm^3 (rho in g/cm^3)
    lo, hi = 0.1, D
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if hydro(mid, gap, n_hulls, dx=1.0)["V"] < vol else (lo, mid)
    return (lo + hi) / 2


if __name__ == "__main__":
    out = Path(__file__).parent
    hull = flip_if_inside_out(loft())
    ok, vol, area, bbox = check(hull)
    assert ok, "demihull mesh is not watertight"
    assert max(bbox) <= 250
    # Export in PRINT orientation (flat top on the bed, keel up): keel-down printing leaves the bow rocker and
    # bilges as unsupported overhangs (verify_v3.py measured 22 cm2). The sailing-orientation hull is only
    # used inside the assembly/CFD files.
    hull_print = moved(hull, lambda x, y, z: (x, -y, D - z))   # 180 deg about x: flips z, mirrors y -> no mirror image
    write_stl(out / "arova_v3_demihull_x2.stl", hull_print, "Arova v3 demihull - PRINT TWO - already in print orientation")
    hull_g = pla_mass_g(vol, area, shell_mm=PLA_RHO_HULL_SHELL, infill=0.05)
    print(f"demihull: watertight={ok}, {bbox[0]:.0f} x {bbox[1]:.0f} x {bbox[2]:.0f} mm, "
          f"solid {vol/1000:.0f} cm3, est. PLA ~{hull_g:.0f} g each (3 walls, 5% infill)")
    # self-check: integrated volume at full depth must match the mesh volume
    full = hydro(D - 1e-6, 0, n_hulls=1, dx=0.25)["V"]
    assert abs(full - vol) / vol < 0.01, (full, vol)

    for gap in GAPS:
        tris = flip_if_inside_out(extrude(deck_section(gap), DECK_X1 - DECK_X0))
        ok, dvol, darea, dbox = check(tris)
        assert ok and max(dbox) <= 250, (gap, ok, dbox)
        write_stl(out / f"arova_v3_deck_gap{int(gap)}.stl", tris, f"Arova v3 deck, hull gap {gap:.0f} mm - plate down")
        deck_g = dvol * 1.24e-3 * 0.6             # thin part: ~60 % solid at 2 walls + 15 % infill
        ship_g = 2 * hull_g + deck_g
        print(f"\ndeck gap {gap:.0f} mm: {dbox[0]:.0f} x {dbox[1]:.0f} x {dbox[2]:.0f} mm, est. PLA ~{deck_g:.0f} g, "
              f"assembled ship ~{ship_g:.0f} g, overall beam {2*B+gap+2*(FIT+FLANGE_T):.0f} mm")
        kg_ship = 0.5 * D                         # shortcut: assumed empty-ship VCG until the inclining test
        print("  load g | draft mm | freeboard mm | GM_T mm (cargo CG 15 mm above deck)")
        for load in (0, 150, 250, 400):
            m = ship_g + load
            T = draft_for(m, gap)
            h = hydro(T, gap)
            kg = (ship_g * kg_ship + load * (D + DECK_T + 15)) / m
            gm = h["KB"] + h["It"] / h["V"] - kg
            print(f"  {load:6d} | {T:8.1f} | {D - T:12.1f} | {gm:8.0f}")

    cr = flip_if_inside_out(extrude(cradle_section(), CRADLE["length"]))
    ok, cvol, _, cbox = check(cr)
    assert ok
    write_stl(out / "arova_v3_electronics_cradle.stl", cr, "Arova v3 electronics cradle - base down")
    print(f"\nelectronics cradle: {cbox[0]:.0f} x {cbox[1]:.1f} x {cbox[2]:.0f} mm, ~{cvol*1.24e-3*0.8:.0f} g")

    parts = assembly(CFD_GAP)
    for p in parts:
        assert check(p)[0], "assembly shell not watertight"
    pts = [q for p in parts for t in p for q in t]
    abox = [max(q[k] for q in pts) - min(q[k] for q in pts) for k in range(3)]
    assert max(abox) <= 250, abox
    write_stl(out / f"arova_v3_assembly_gap{int(CFD_GAP)}_CFD.stl", [t for p in parts for t in p],
              f"Arova v3 assembly gap {CFD_GAP:.0f} mm - sailing position, for CFD")
    print(f"CFD assembly (gap {CFD_GAP:.0f}): {abox[0]:.0f} x {abox[1]:.0f} x {abox[2]:.1f} mm, 3 watertight shells")
    # CFD-safe file: only the wetted geometry (two closed hulls, 100 mm apart). The full assembly has the deck
    # 0.1-0.3 mm from the hulls, which CFD meshers either reject or resolve with a huge cell count; the deck is
    # >20 mm above the 400 g waterline, so it does not change the resistance result.
    write_stl(out / f"arova_v3_CFD_hulls_gap{int(CFD_GAP)}.stl", [t for p in parts[:2] for t in p],
              f"Arova v3 CFD hulls gap {CFD_GAP:.0f} mm - sailing position, keel z=0, x to bow")
    print(f"CFD hulls file (gap {CFD_GAP:.0f}): 2 watertight shells, {CFD_GAP:.0f} mm apart - send this one to CFD")

    T1 = draft_for(2 * hull_g / 2 + 50, 0, n_hulls=1)
    h1 = hydro(T1, 0, n_hulls=1)
    print(f"\nmonohull test (one demihull + 50 g): draft {T1:.1f} mm, GM ~{h1['KB'] + h1['It']/h1['V'] - 0.5*D:.1f} mm "
          f"(expect small or negative -> shows why the catamaran wins)")
    hT = hydro(25.0, 70)
    print(f"app equivalent at 25 mm draft: pontoon length L_eq = {hT['Awp']/(2*B):.0f} mm "
          f"(enter B={B:.0f}, D={D:.0f}, gap as printed)")
