"""Hydrostatic table of the printed v3 hull, read by the app (hydro.load_v3_hull).

Run: python3 print/v3/make_v3_table.py  -> writes data/v3_hydrostatics.json

Integrates the exact demihull sections from make_v3.py station by station (dx = 0.5 mm):
volume, vertical and longitudinal centre of buoyancy, waterplane area, transverse and longitudinal
waterplane inertia - for one demihull, then combined for each printed deck gap.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import make_v3 as v3  # noqa: E402  (same geometry that wrote the STL)

DX = 0.5
XS = [k * DX for k in range(int(v3.L / DX) + 1)]
MID = v3.L / 2


def waterline_width(x, T):
    pts = [p for p in v3.clip_below(v3.section(x), T) if abs(p[1] - T) < 1e-9]
    return (max(y for y, _ in pts) - min(y for y, _ in pts)) if len(pts) >= 2 else 0.0


def one_hull(T):
    """Per-demihull quantities at draft T (mm units, x from midship)."""
    V = Mz = Mx = Awp = Iown = Mxw = 0.0
    widths = []
    for x in XS:
        a, cz = v3.area_cz(v3.clip_below(v3.section(x), T))
        w = waterline_width(x, T)
        V += a * DX
        Mz += a * cz * DX
        Mx += a * (x - MID) * DX
        Awp += w * DX
        Iown += w ** 3 / 12 * DX
        Mxw += w * (x - MID) * DX
        widths.append(w)
    lcf = Mxw / Awp if Awp else 0.0
    Il = sum(w * ((x - MID) - lcf) ** 2 * DX for x, w in zip(XS, widths))
    return dict(V=V, KB=Mz / V if V else 0.0, LCB=Mx / V if V else 0.0, Awp=Awp, Iown=Iown, Il=Il)


def table(n_hulls, gap):
    c = (gap + v3.B) / 2 if n_hulls == 2 else 0.0
    rows = []
    for i in range(1, int(v3.D / 0.5) + 1):
        T = i * 0.5
        h = one_hull(T)
        if h["V"] <= 0:
            continue
        It = n_hulls * (h["Iown"] + h["Awp"] * c * c)
        # SI units: m, m^3, m^2, m^4
        rows.append([T / 1e3, n_hulls * h["V"] / 1e9, h["KB"] / 1e3, h["LCB"] / 1e3, n_hulls * h["Awp"] / 1e6,
                     It / 1e12, n_hulls * h["Il"] / 1e12])
    return rows


if __name__ == "__main__":
    out = {"columns": ["T_m", "V_m3", "KB_m", "LCB_m_from_midship", "Awp_m2", "IT_m4", "IL_m4"],
           "geometry": dict(length_m=v3.L / 1e3, demihull_beam_m=v3.B / 1e3, depth_m=v3.D / 1e3,
                            deck_top_m=(v3.D + v3.DECK_T) / 1e3, deck_length_m=(v3.DECK_X1 - v3.DECK_X0) / 1e3,
                            deck_centre_x_from_midship_m=((v3.DECK_X0 + v3.DECK_X1) / 2 - v3.L / 2) / 1e3,
                            flange_m=(v3.FIT + v3.FLANGE_T) / 1e3),
           "configs": {}}
    out["configs"]["1 hull (monohull test)"] = dict(n_hulls=1, gap_m=0.0, rows=table(1, 0.0))
    for gap in v3.GAPS:
        out["configs"][f"2 hulls, gap {gap:.0f} mm"] = dict(n_hulls=2, gap_m=gap / 1e3, rows=table(2, gap))
    # Print-based mass and KG per configuration (from the STL files), used by the app until the parts are weighed
    # and the inclining test gives the real KG. Run make_v3.py first so the STL files are current.
    from print_estimate import mass_kg_estimate
    for name, cfg in out["configs"].items():
        m, kg = mass_kg_estimate(name)
        cfg["estimate"] = dict(mass_kg=round(m, 4), kg_m=round(kg, 5), source="print_estimate.py, watertight profile")
    dest = HERE.parents[1] / "data" / "v3_hydrostatics.json"
    dest.parent.mkdir(exist_ok=True)
    dest.write_text(json.dumps(out, indent=1))
    for name, cfg in out["configs"].items():
        r = cfg["rows"][-1]
        print(f"{name}: {len(cfg['rows'])} drafts, full-depth volume {r[1]*1e6:.0f} cm3")
    print("wrote", dest)
