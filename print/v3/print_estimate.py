"""Mass and print-time estimate for the v3 print set, measured from the STL files (surface area and volume).

Run: python3 print/v3/print_estimate.py

Model (stated so the numbers can be checked): a closed FDM part = solid shell over its whole surface
(walls x line width, which also roughly equals the top/bottom skin thickness) + sparse infill in the rest.
PLA density 1.24 g/cm3. Print time = extruded volume / average volumetric flow; the two flows bracket a
typical bed-slinger (~5 mm3/s average incl. travel) and a fast CoreXY (~12 mm3/s). Real slicer numbers win:
slice the files and replace these estimates.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from verify_v3 import load, shells, volume, cross, sub  # noqa: E402

PLA = 1.24e-3            # g/mm3
LINE = 0.42              # mm extrusion width
PROFILES = {
    "watertight (3 walls, 5% gyroid)": dict(walls=3, infill=0.05),
    "fast (2 walls, lightning ~2%)": dict(walls=2, infill=0.02),
}
FLOWS = {"typical printer": 5.0, "fast CoreXY": 12.0}     # mm3/s average
SET = [("arova_v3_demihull_x2.stl", 2), ("arova_v3_deck_gap100.stl", 1), ("arova_v3_electronics_cradle.stl", 1)]


def area(tris):
    return sum(sum(c * c for c in cross(sub(b, a), sub(c_, a))) ** 0.5 / 2 for a, b, c_ in tris)


def estimate(tris, walls, infill):
    A, V = area(tris), sum(volume(s) for s in shells(tris))
    shell = min(A * walls * LINE, V)          # thin parts (deck, cradle) are nearly solid
    return shell + (V - shell) * infill       # mm3 of plastic


def area_centroid_z(tris):
    a_sum = z_sum = 0.0
    for a, b, c in tris:
        ar = sum(x * x for x in cross(sub(b, a), sub(c, a))) ** 0.5 / 2
        a_sum += ar
        z_sum += ar * (a[2] + b[2] + c[2]) / 3
    return z_sum / a_sum


def volume_centroid_z(tris):
    v = m = 0.0
    for a, b, c in tris:
        d = volume([(a, b, c)])
        v += d
        m += d * (a[2] + b[2] + c[2]) / 4      # tetra with apex at the origin (z=0)
    return m / v


def mass_kg_estimate(cfg="2 hulls, gap 100 mm", electronics=False, profile="watertight (3 walls, 5% gyroid)"):
    """(mass kg, KG m above keel) of the assembled ship, from the STL files.

    Hull CG = surface-area centroid (a 3-wall shell carries its mass at the skin), deck CG = volume centroid.
    Electronics option: 40 g, 15 mm above the deck.
    """
    import make_v3 as v3
    prof = PROFILES[profile]
    hull_t = load(HERE / "arova_v3_demihull_x2.stl")             # print orientation: keel at z = D
    parts = [((2 if cfg.startswith("2") else 1) * estimate(hull_t, **prof) * PLA / 1000,
              v3.D - area_centroid_z(hull_t))]
    if cfg.startswith("2"):
        gap = cfg.split("gap ")[1].split()[0]
        deck_t = load(HERE / f"arova_v3_deck_gap{gap}.stl")      # plate on the bed (z=0), flanges up
        parts.append((estimate(deck_t, **prof) * PLA / 1000, v3.D + v3.DECK_T - volume_centroid_z(deck_t)))
    if electronics:
        parts.append((0.040, (v3.D + v3.DECK_T if cfg.startswith("2") else v3.D) + 15))
    m = sum(p[0] for p in parts)
    return m, sum(p[0] * p[1] for p in parts) / m / 1000


if __name__ == "__main__":
    for name, prof in PROFILES.items():
        total_v = 0.0
        print(f"\n{name}")
        longest = 0.0
        for fname, qty in SET:
            v = estimate(load(HERE / fname), **prof)
            total_v += v * qty
            longest = max(longest, v)
            t = " / ".join(f"{v / f / 3600:.1f} h" for f in FLOWS.values())
            print(f"  {fname:34s} x{qty}: {v * PLA:6.0f} g each, {t} each ({' / '.join(FLOWS)})")
        times = ", ".join(f"{k} ~{total_v / f / 3600:.1f} h" for k, f in FLOWS.items())
        par = ", ".join(f"{k} ~{longest / f / 3600:.1f} h" for k, f in FLOWS.items())
        print(f"  TOTAL print set: {total_v * PLA:.0f} g PLA; one printer: {times}; parts on 4 printers at once: {par}")
