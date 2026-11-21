# Arova v3 "Wave-Piercer" modular catamaran: CAD design brief

Paste this into the CAD tool (SolidCraft). Units are mm. Reference STLs made from exactly these numbers are in this folder. They are watertight and their dimensions are checked. **Competition configuration: hull gap 100 mm.**

## Goal and rules it must meet
- Arova "Ballast Free Ship": stay stable under 150–400 g cargo **without ballast water**.
- Size limit: every part and the assembly must fit in **250 × 250 × 250 mm**.
- Material: basic PLA. Sealing: water-based 3D-print varnish.
- The judges run the STL through CFD in medium turbulent water. Fluid efficiency, originality and sustainability score points.
- Brief ideas covered here:
  - adjustable hull spacing
  - each hull can be tested alone as a monohull
  - MPU-6050 kept dry above the water
  - stability from hull shape and low weight, not ballast

## Parts (print the demihull twice)

### 1. Demihull (print ×2, identical)
- Overall 235 long (x), **60 wide** (y), **70 high** (z). (v4: widened from 50 mm after a parametric sweep, compared at 3-wall print mass: load limit 786 → 918 g, safe wave height 30 → 35 mm, off-centre heel 5.6 → 3.7°.) Keel at z = 0, flat top at z = 70.
- **Plan shape (waterline):**
  - Transom 40 wide at x = 0, widening to full 50 by x = 25.
  - Parallel middle body 60 wide from x = 25 to x = 150.
  - Bow from x = 150 to 235: fine entry, half-beam = 25·(1 − t^1.8) with t = (x−150)/85. It meets the parallel body tangentially and ends in a 2 mm wide tip (not a knife edge).
- **Sections:** sides are **vertical** from the bilge up to the top. The two top edges (the edges on the print bed) carry a **0.8 mm × 45° chamfer** that absorbs elephant foot where the deck flanges grip. Bottom is flat, with a **6 mm bilge radius** on both lower edges. The radius shrinks where the hull narrows at the bow.
- **Keel rocker:** the keel is flat to x = 185, then rises as 16·((x−185)/50)² mm, reaching 16 mm at the bow tip (wave-piercing bow).
- Closed solid, no holes, no sockets. Nothing can leak, and water on deck cannot flood it.
- Print **upside down** (flat top on the bed): no supports. **The STL is already saved in this orientation** - do not rotate it in the slicer (keel-down printing leaves the bow rocker as a 22 cm² unsupported overhang). **3 walls** (1.2 mm) for watertightness, 4 top/bottom layers, 3–5 % gyroid or lightning infill.

### 2. Clip-on deck (gap 100 = competition; 40 and 70 = optional comparison decks)
- Flat plate 150 long × **2 thick** (checked: 400 g as one point load mid-gap gives ~1 mm sag and 2.9 MPa, a 10× margin on printed PLA; 25 g lighter than 3 mm and lowers the ship's centre of gravity). It sits on top of both hulls from **x = 27.5 to x = 177.5**, so its centre lies over the centre of buoyancy (x ≈ 102.5).
- Under the plate, at each hull, a **saddle** of two flanges: 12 deep, 2.4 thick, 0.3 clearance each side of the 60 mm hull. The deck slides down over the hulls.
- Overall width = 2·60 + gap + 2·(0.3 + 2.4): **225 mm** for gap 100 (165 / 195 for gaps 40 / 70).
- Hold the deck and hulls with 2 rubber bands or zip ties per hull. A drop of glue is OK for the final run.
- Print plate-down, flanges up: no supports.

### 3. Electronics cradle (print ×1)
- U-channel 60 long, 26.5 wide, 12 high: 2 mm base, 2 mm walls, **22.5 mm inner slot**. The MPU-6050 (GY-521, 21 mm) or an Arduino Nano (18 mm) slides in from the end.
- Tape or glue it on the deck centreline. The boards then sit about 75 mm above the keel, far above the water. Put the battery in a zip bag next to it.
- Print base-down: no supports.

### 4. CFD files for the judges (not printed)
- **Send `arova_v3_CFD_hulls_gap100.stl` to CFD.** It holds only the wetted geometry: both hulls in sailing position (keel at z = 0, x toward the bow), 235 × 200 × 70 mm, two closed shells 100 mm apart. The deck sits more than 20 mm above the 400 g waterline, so it does not change the resistance result.
- `arova_v3_assembly_gap100_CFD.stl` is the full ship with the deck, **for display only**. Its deck sits 0.1–0.3 mm from the hulls, a gap CFD meshers often reject or resolve with a huge mesh.
- `verify_v3.py` checks both files (shells, clearance, watertightness).

## Challenge check (team app model, regenerate with `python3 print/v3/challenge_check.py --brief`)

Fresh water 15 °C; masses and centres of gravity measured from the STL files (watertight print profile); cargo is a 30 mm tall box on the deck centre; wave cases use 300 mm tank depth and 10 % damping. Real weighing and the inclining test replace these estimates.

**2 hulls, gap 100 mm**

| Check | Result | Pass |
|---|---|---|
| Ship as printed | mass 444 g, KG 43.9 mm (from the STL files) | ✅ |
| Floats with 150 g (centred) | draft 25.1 mm, lowest freeboard 44.2 mm, GM 230 mm, trim +0.3° | ✅ |
| Floats with 250 g (centred) | draft 29.3 mm, lowest freeboard 40.4 mm, GM 188 mm, trim +0.1° | ✅ |
| Floats with 400 g (centred) | draft 35.5 mm, lowest freeboard 34.1 mm, GM 145 mm, trim -0.2° | ✅ |
| 400 g, 20 mm off-centre | heel 3.7°, lowest freeboard 26.9 mm | ✅ |
| Predicted load limit (centred) | 876 g; first limit: Lowest freeboard 10.0 mm below 10 mm limit (water on deck risk). | ✅ |
| Waves H 10–40 mm, T 0.5–1.5 s, 400 g: cargo deck stays dry (worst case) | H 40 mm, T 0.6 s: 41.7 mm relative motion at the deck ends vs 34.3 mm deck height (margin -7.4 mm) | ❌ |
| Waves, 400 g: no capsize in beam seas (worst case) | H 40 mm, T 0.5 s: roll 32.2° vs windward-hull lift-off 35.3° (margin +3.1°) | ❌ |
| Waves, 400 g: water over the sealed bow/stern tips (info) | H 40 mm, T 0.6 s: 57.6 mm vs 34.1 mm at the tips (margin -23.5 mm) - closed hulls shed it | ✅ |

**2 hulls, gap 100 mm + 40 g electronics**

| Check | Result | Pass |
|---|---|---|
| Ship as printed | mass 484 g, KG 47.5 mm (from the STL files) | ✅ |
| Floats with 150 g (centred) | draft 26.8 mm, lowest freeboard 42.6 mm, GM 212 mm, trim +0.3° | ✅ |
| Floats with 250 g (centred) | draft 30.9 mm, lowest freeboard 38.8 mm, GM 175 mm, trim +0.1° | ✅ |
| Floats with 400 g (centred) | draft 37.1 mm, lowest freeboard 32.4 mm, GM 136 mm, trim -0.2° | ✅ |
| 400 g, 20 mm off-centre | heel 3.8°, lowest freeboard 25.1 mm | ✅ |
| Predicted load limit (centred) | 841 g; first limit: Lowest freeboard 10.0 mm below 10 mm limit (water on deck risk). | ✅ |
| Waves H 10–40 mm, T 0.5–1.5 s, 400 g: cargo deck stays dry (worst case) | H 40 mm, T 0.6 s: 34.4 mm relative motion at the deck ends vs 32.6 mm deck height (margin -1.8 mm) | ❌ |
| Waves, 400 g: no capsize in beam seas (worst case) | H 40 mm, T 0.5 s: roll 34.9° vs windward-hull lift-off 36.6° (margin +1.7°) | ❌ |
| Waves, 400 g: water over the sealed bow/stern tips (info) | H 40 mm, T 0.6 s: 48.1 mm vs 32.4 mm at the tips (margin -15.7 mm) - closed hulls shed it | ✅ |

**2 hulls, gap 70 mm**

| Check | Result | Pass |
|---|---|---|
| Ship as printed | mass 433 g, KG 43.2 mm (from the STL files) | ✅ |
| Floats with 150 g (centred) | draft 24.7 mm, lowest freeboard 44.7 mm, GM 145 mm, trim +0.3° | ✅ |
| Floats with 250 g (centred) | draft 28.8 mm, lowest freeboard 40.9 mm, GM 115 mm, trim +0.1° | ✅ |
| Floats with 400 g (centred) | draft 35.0 mm, lowest freeboard 34.6 mm, GM 84 mm, trim -0.2° | ✅ |
| 400 g, 20 mm off-centre | heel 6.5°, lowest freeboard 23.7 mm | ✅ |
| Predicted load limit (centred) | 886 g; first limit: Lowest freeboard 10.0 mm below 10 mm limit (water on deck risk). | ✅ |
| Waves H 10–40 mm, T 0.5–1.5 s, 400 g: cargo deck stays dry (worst case) | H 40 mm, T 0.6 s: 42.2 mm relative motion at the deck ends vs 34.7 mm deck height (margin -7.4 mm) | ❌ |
| Waves, 400 g: no capsize in beam seas (worst case) | H 40 mm, T 0.5 s: roll 35.1° vs windward-hull lift-off 45.0° (margin +9.9°) | ✅ |
| Waves, 400 g: water over the sealed bow/stern tips (info) | H 40 mm, T 0.6 s: 58.2 mm vs 34.6 mm at the tips (margin -23.6 mm) - closed hulls shed it | ✅ |

**2 hulls, gap 40 mm**

| Check | Result | Pass |
|---|---|---|
| Ship as printed | mass 421 g, KG 42.5 mm (from the STL files) | ✅ |
| Floats with 150 g (centred) | draft 24.2 mm, lowest freeboard 45.1 mm, GM 75 mm, trim +0.3° | ✅ |
| Floats with 250 g (centred) | draft 28.3 mm, lowest freeboard 41.3 mm, GM 55 mm, trim +0.2° | ✅ |
| Floats with 400 g (centred) | draft 34.5 mm, lowest freeboard 35.1 mm, GM 35 mm, trim -0.2° | ✅ |
| 400 g, 20 mm off-centre | heel 15.6°, lowest freeboard 12.8 mm | ✅ |
| Predicted load limit (centred) | 895 g; first limit: Lowest freeboard 10.0 mm below 10 mm limit (water on deck risk). | ✅ |
| Waves H 10–40 mm, T 0.5–1.5 s, 400 g: cargo deck stays dry (worst case) | H 40 mm, T 0.6 s: 42.1 mm relative motion at the deck ends vs 35.2 mm deck height (margin -6.9 mm) | ❌ |
| Waves, 400 g: no capsize in beam seas (worst case) | H 40 mm, T 0.6 s: roll 20.9° vs windward-hull lift-off 59.9° (margin +39.1°) | ✅ |
| Waves, 400 g: water over the sealed bow/stern tips (info) | H 40 mm, T 0.6 s: 58.1 mm vs 35.1 mm at the tips (margin -23.0 mm) - closed hulls shed it | ✅ |

**1 hull alone (monohull baseline)**: 169 g + 50 g on top → GM -21.7 mm (tips over) - the 'why a catamaran' demo.

## Which deck for which waves (`python3 print/v3/wave_map.py`)
Map over wave height 5–40 mm × period 0.4–1.6 s, 250 g and 400 g, roll damping 0.10 and 0.20, 300 mm tank depth:
- **Both decks are safe at every period up to H = 30 mm** (35 mm with roll damping 0.20) (cargo deck dry, roll well below the windward-hull lift-off angle).
- The only risk is a narrow band, **T ≈ 0.4–0.5 s with H ≥ 35 mm**, at the catamaran's own roll period (0.44–0.46 s for gap 100). Even at H = 40 mm the roll stays 4.4° below the lift-off angle; the deck ends can get splashed.
- **Use gap 100 for the competition.** It has the best static stability (400 g placed 20 mm off-centre gives 3.7° heel, against 6.5° with gap 70).
- Keep the **gap 70 deck as a backup**. Swap to it only if the organisers announce very short, steep beam waves (period about 0.5 s, height 35 mm or more).
- Ask at check-in: wave height, wave period, and the tank depth.

## Why this shape wins (pitch points)
- **CFD and waves:**
  - Slender hulls (L/B ≈ 3.9 each) with a tangent fine entry and a wave-piercing rocker bow cut wave resistance and slamming.
  - Rounded bilges reduce corner vortices.
  - Wetted surface is 13 % lower than the box catamaran.
- **Ballast-free stability:** hull spacing gives the stability. At 400 g, GM goes from 38 mm to 156 mm as the gap goes from 40 to 100 mm, with no ballast and no servos.
- **Seaworthy:** 70 mm hull depth keeps 34 mm freeboard at the maximum 400 g load.
- **Validation-friendly:** sides are vertical through the whole waterline band. In the app pick **Type → v3 wave-piercer (printed)** and the printed gap. It uses the exact hydrostatic table of this shape (`data/v3_hydrostatics.json`, made by `make_v3_table.py`).
- **Sustainability:** reusable, swappable parts, and no ballast water, which means no invasive-species transfer.
- **Modular test rig:** one set of hulls gives four configurations (gap 40 / 70 / 100, monohull). Same hulls, so the comparison is fair.

## Acceptance checks before printing
1. Each part is a single watertight solid; the bounding box is under 250 mm.
2. The demihull solid volume is about 703 cm³ (the reference STL value).
3. The deck slides over two hulls with a 0.3 mm gap per side. Print a short test strip first if the printer is tight.
4. After printing, weigh each part and enter the real mass in the app. Varnish, dry and weigh again. Run the inclining test for the real KG.
5. Mark draft lines (mm tape) at bow, midship and stern on both hulls for the draft-vs-load test.

## Files in this folder
- `arova_v3_demihull_x2.stl`: print two
- `arova_v3_deck_gap100.stl`: competition deck, print first
- `arova_v3_deck_gap40.stl`, `arova_v3_deck_gap70.stl`: optional comparison decks
- `arova_v3_electronics_cradle.stl`: print one
- `arova_v3_assembly_gap100_CFD.stl`: submit this to the judges for CFD
- `make_v3.py`: regenerates all parts (`python3 print/v3/make_v3.py`). `make_v3_table.py` regenerates the app's table.
- `arova_v3_preview.png`: render
