"""Which deck for which waves? Pass/fail map over wave height x period for the printed v3 (team app model).

Run: python3 print/v3/wave_map.py

Cell symbols: .  safe   d  cargo deck gets wet   C  capsize risk (roll >= windward-hull lift-off - 5 deg)
              x  breaking wave (H/lambda > 1/7, outside a wave tank's regular-wave range)
Roll damping is the least certain input, so each deck is mapped for zeta = 0.10 and 0.20 (catamarans often
damp more than monohulls; the roll-decay test in the app measures it).
"""
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from challenge_check import ship, RHO, LIM          # noqa: E402
from hydro import Cargo, analyse, wave_motions      # noqa: E402

HS = [h / 1000 for h in range(5, 45, 5)]            # 5..40 mm
TS = [round(0.4 + 0.1 * i, 1) for i in range(13)]   # 0.4..1.6 s


def cell(h, r, H, T, zeta):
    xs = (h.deck_xc - h.deck_len / 2, h.deck_xc + h.deck_len / 2)
    mo = wave_motions(h, r, H, T, 0.3, zeta, x_points=xs)
    if mo["steepness"] > 1 / 7:
        return "x"
    lift = math.degrees(math.atan(2 * r.draft / (h.gap)))           # (s - b) = gap for equal hulls
    fb_deck = r.freeboard - h.deck_len / 2 * abs(math.tan(math.radians(r.trim_deg)))
    if mo["roll_deg"] >= lift - 5:
        return "C"
    if max(mo["rel_at"].values()) >= fb_deck:
        return "d"
    return "."


def grid(cfg, load_g, zeta):
    h, *_ = ship(cfg)
    r = analyse(h, [Cargo("load", load_g / 1000, h.deck_xc, 0, 0.06, 0.06, 0.03)], RHO, **LIM)
    rows = [f"{cfg}, {load_g} g, zeta {zeta}:  roll period {r.roll_period:.2f} s",
            "  H\\T  " + " ".join(f"{t:>3}" for t in TS)]
    safe_h = {}
    for H in reversed(HS):
        line = []
        for T in TS:
            c = cell(h, r, H, T, zeta)
            line.append(f"{c:>3}")
            if c == "." and T not in safe_h:
                safe_h[T] = H
        rows.append(f"  {H*1000:3.0f}  " + " ".join(line))
    worst = min((safe_h.get(T, 0.0) for T in TS if cell(h, r, 0.005, T, zeta) != "x"), default=0.0)
    rows.append(f"  -> safe in every period up to H = {worst*1000:.0f} mm")
    return "\n".join(rows), worst


if __name__ == "__main__":
    summary = []
    for cfg in ("2 hulls, gap 100 mm", "2 hulls, gap 70 mm"):
        for load in (250, 400):
            for zeta in (0.10, 0.20):
                txt, worst = grid(cfg, load, zeta)
                print(txt + "\n")
                summary.append((cfg, load, zeta, worst))
    print("SUMMARY - largest wave height safe at EVERY period 0.4-1.6 s:")
    for cfg, load, zeta, worst in summary:
        print(f"  {cfg:20s} {load} g  zeta {zeta:.2f}: {worst*1000:.0f} mm")
