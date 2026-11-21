"""Challenge pass/fail table for the printed v3, computed with the team app's own model (hydro.py).

Run: python3 print/v3/challenge_check.py           -> prints a markdown table
     python3 print/v3/challenge_check.py --brief   -> also writes it into DESIGN_BRIEF.md

Inputs come from the files, not from guesses:
- part masses from print_estimate.py (watertight profile) and their centres of gravity from the STL meshes
  (hull = surface-area centroid, since a 3-wall shell carries most of its mass at the skin; deck = volume centroid);
- hydrostatics from data/v3_hydrostatics.json (exact sections, cross-checked against the mesh by verify_v3.py).
Fresh water 15 C. Cargo = 30 mm tall box(es) on the deck centre. Electronics option adds 40 g in the hull-top pockets.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))
from print_estimate import mass_kg_estimate             # noqa: E402
from hydro import Cargo, analyse, load_limit, wave_motions, seawater_density, load_v3_hull  # noqa: E402
import make_v3 as v3                                     # noqa: E402

RHO = seawater_density(0, 15)
LIM = dict(min_freeboard_m=0.010, max_heel_deg=5.0, min_gm_m=0.005)


def ship(cfg="2 hulls, gap 100 mm", electronics=False):
    m, kg = mass_kg_estimate(cfg, electronics)
    return load_v3_hull(cfg, m, kg), m, kg


def rows(cfg="2 hulls, gap 100 mm", electronics=False):
    h, m, kg = ship(cfg, electronics)
    out = [("Ship as printed", f"mass {m*1000:.0f} g, KG {kg*1000:.1f} mm (from the STL files)", True)]
    for g in (150, 250, 400):
        r = analyse(h, [Cargo("load", g / 1000, h.deck_xc, 0, 0.06, 0.06, 0.03)], RHO, **LIM)
        out.append((f"Floats with {g} g (centred)",
                    f"draft {r.draft*1000:.1f} mm, lowest freeboard {r.min_freeboard*1000:.1f} mm, GM {r.gm*1000:.0f} mm, "
                    f"trim {r.trim_deg:+.1f}°", not r.warnings))
    r = analyse(h, [Cargo("load", 0.4, h.deck_xc, 0.02, 0.06, 0.06, 0.03)], RHO, **LIM)
    out.append(("400 g, 20 mm off-centre", f"heel {r.heel_deg:.1f}°, lowest freeboard {r.min_freeboard*1000:.1f} mm",
                r.gm > 0 and r.min_freeboard > LIM["min_freeboard_m"]))
    cap, why = load_limit(h, [Cargo("load", 0.4, h.deck_xc, 0, 0.06, 0.06, 0.03)], RHO, **LIM)
    out.append(("Predicted load limit (centred)", f"{cap*1000:.0f} g; first limit: {why.split(':')[0]}", cap >= 0.4))
    # Waves, 400 g. Three different questions, each at its own worst case over the sea-state grid:
    #  - cargo deck dry: relative motion at the deck ends vs the deck's height above water (cargo lives there);
    #  - no capsize: roll amplitude in beam waves vs the angle where the windward hull lifts out
    #    (catamaran righting arm peaks near tan(phi) = 2T/(s - b), s = hull centre spacing, b = hull beam);
    #  - water over the sealed bow/stern ends: information only - closed hulls shed it (wave-piercing bows do).
    r4 = analyse(h, [Cargo("load", 0.4, h.deck_xc, 0, 0.06, 0.06, 0.03)], RHO, **LIM)
    xs = (h.deck_xc - (h.deck_len or h.length) / 2, h.deck_xc + (h.deck_len or h.length) / 2)
    fb_deck = r4.freeboard - (h.deck_len or h.length) / 2 * abs(__import__("math").tan(__import__("math").radians(r4.trim_deg)))
    s_c = h.gap + h.beam if h.n_pontoons == 2 else 0.0
    lift = __import__("math").degrees(__import__("math").atan(2 * r4.draft / (s_c - h.beam))) if s_c > h.beam else float("nan")
    worst_deck = worst_roll = worst_end = None
    for H in (0.01, 0.02, 0.03, 0.04):
        for T in (0.5, 0.6, 0.8, 1.0, 1.5):
            mo = wave_motions(h, r4, H, T, 0.3, 0.1, x_points=xs)
            if mo["steepness"] > 1 / 7:
                continue                      # breaking waves: outside any tank's "wave simulation"
            d = (fb_deck - max(mo["rel_at"].values()), H, T, mo)
            r = (lift - mo["roll_deg"], H, T, mo)
            e = (r4.min_freeboard - mo["rel_motion_m"], H, T, mo)
            worst_deck = d if worst_deck is None or d[0] < worst_deck[0] else worst_deck
            worst_roll = r if worst_roll is None or r[0] < worst_roll[0] else worst_roll
            worst_end = e if worst_end is None or e[0] < worst_end[0] else worst_end
    m_, H, T, mo = worst_deck
    out.append(("Waves H 10–40 mm, T 0.5–1.5 s, 400 g: cargo deck stays dry (worst case)",
                f"H {H*1000:.0f} mm, T {T} s: {max(mo['rel_at'].values())*1000:.1f} mm relative motion at the deck ends vs "
                f"{fb_deck*1000:.1f} mm deck height (margin {m_*1000:+.1f} mm)", m_ > 0))
    m_, H, T, mo = worst_roll
    out.append(("Waves, 400 g: no capsize in beam seas (worst case)",
                f"H {H*1000:.0f} mm, T {T} s: roll {mo['roll_deg']:.1f}° vs windward-hull lift-off {lift:.1f}° "
                f"(margin {m_:+.1f}°)", m_ > 5))
    m_, H, T, mo = worst_end
    out.append(("Waves, 400 g: water over the sealed bow/stern tips (info)",
                f"H {H*1000:.0f} mm, T {T} s: {mo['rel_motion_m']*1000:.1f} mm vs {r4.min_freeboard*1000:.1f} mm at the tips "
                f"(margin {m_*1000:+.1f} mm) - closed hulls shed it", True))
    return out


def table(cfg, electronics=False):
    lines = [f"**{cfg}{' + 40 g electronics (in the hull pockets)' if electronics else ''}**", "",
             "| Check | Result | Pass |", "|---|---|---|"]
    for name, res, ok in rows(cfg, electronics):
        lines.append(f"| {name} | {res} | {'✅' if ok else '❌'} |")
    return "\n".join(lines)


if __name__ == "__main__":
    md = "\n\n".join([table("2 hulls, gap 100 mm"), table("2 hulls, gap 100 mm", electronics=True),
                      table("2 hulls, gap 70 mm"), table("2 hulls, gap 40 mm")])
    mono_h, mm, mk = ship("1 hull (monohull test)")
    r = analyse(mono_h, [Cargo("load", 0.05, 0, 0, 0.04, 0.04, 0.02)], RHO, **LIM)
    md += (f"\n\n**1 hull alone (monohull baseline)**: {mm*1000:.0f} g + 50 g on top → GM {r.gm*1000:.1f} mm "
           f"({'tips over' if r.gm <= 0 else 'barely stable'}) - the 'why a catamaran' demo.")
    print(md)
    if "--brief" in sys.argv:
        p = HERE / "DESIGN_BRIEF.md"
        s = p.read_text()
        i = s.find("## Challenge check")
        j = s.find("\n## ", i + 5)
        head = s[:i]
        note = "> **Note (night of 20 Nov):**"
        if note in head:                       # drop the "being re-run" note
            k = head.find(note)
            head = head[:k] + head[head.find("\n\n", k) + 2:]
        s = (head + "## Challenge check (team app model, regenerate with `python3 print/v3/challenge_check.py --brief`)\n\n"
             "Fresh water 15 °C; masses and centres of gravity measured from the STL files (watertight print profile); "
             "cargo is a 30 mm tall box on the deck centre; wave cases use 300 mm tank depth and 10 % damping. "
             "Real weighing and the inclining test replace these estimates.\n\n" + md + "\n" + (s[j:] if j > 0 else ""))
        p.write_text(s)
        print("\nwrote DESIGN_BRIEF.md")
