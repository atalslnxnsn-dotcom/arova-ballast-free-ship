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
- Overall 235 long (x), 50 wide (y), **70 high** (z). Keel at z = 0, flat top at z = 70.
- **Plan shape (waterline):**
  - Transom 40 wide at x = 0, widening to full 50 by x = 25.
  - Parallel middle body 50 wide from x = 25 to x = 150.
  - Bow from x = 150 to 235: fine entry, half-beam = 25·(1 − t^1.8) with t = (x−150)/85. It meets the parallel body tangentially and ends in a 2 mm wide tip (not a knife edge).
- **Sections:** sides are **vertical** from the bilge up to the top. The two top edges (the edges on the print bed) carry a **0.8 mm × 45° chamfer** that absorbs elephant foot where the deck flanges grip. Bottom is flat, with a **6 mm bilge radius** on both lower edges. The radius shrinks where the hull narrows at the bow.
- **Keel rocker:** the keel is flat to x = 185, then rises as 16·((x−185)/50)² mm, reaching 16 mm at the bow tip (wave-piercing bow).
- Closed solid, no holes, no sockets. Nothing can leak, and water on deck cannot flood it.
- Print **upside down** (flat top on the bed): no supports. **The STL is already saved in this orientation** - do not rotate it in the slicer (keel-down printing leaves the bow rocker as a 22 cm² unsupported overhang). **3 walls** (1.2 mm) for watertightness, 4 top/bottom layers, 3–5 % gyroid or lightning infill.

### 2. Clip-on deck (gap 100 = competition; 40 and 70 = optional comparison decks)
- Flat plate 150 long × **2 thick** (checked: 400 g as one point load mid-gap gives ~1 mm sag and 2.9 MPa, a 10× margin on printed PLA; 25 g lighter than 3 mm and lowers the ship's centre of gravity). It sits on top of both hulls from **x = 27.5 to x = 177.5**, so its centre lies over the centre of buoyancy (x ≈ 102.5).
- Under the plate, at each hull, a **saddle** of two flanges: 12 deep, 2.4 thick, 0.3 clearance each side of the 50 mm hull. The deck slides down over the hulls.
- Overall width = 2·50 + gap + 2·(0.3 + 2.4): **205 mm** for gap 100 (145 / 175 for gaps 40 / 70).
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

> **Note (night of 20 Nov):** the deck is now 2 mm and the hulls carry a 0.8 mm print chamfer; the challenge-check numbers below are being re-run with the app's model and will be replaced.

## Challenge check (team app's own model: `hydro.analyse` and `wave_motions`, fresh water, gap 100)
Assumptions until the real tests:
- Ship mass about 324 g (2 × 121 g hulls + 82 g deck).
- Empty-ship KG 44 mm.
- Cargo 30 mm tall, placed on the deck centre.

| Challenge requirement | Result | Pass? |
|---|---|---|
| Fits 250 × 250 × 250 mm | Largest part 235 × 205 × 15 (deck); assembly 235 × 205 × 73 | ✅ |
| Basic PLA, watertight | All parts single closed solids, no holes; 3 walls + varnish | ✅ |
| Floats with 150 g | Draft 24.0, freeboard 46.0, GM 204 mm, no warnings | ✅ |
| Floats with 250 g | Draft 28.9, freeboard 41.1, GM 157 mm, no warnings | ✅ |
| Floats with 400 g | Draft 36.3, freeboard **33.7**, GM **113 mm**, trim ≈ 0°, no warnings | ✅ |
| Stays balanced, cargo 20 mm off-centre (400 g) | Heel 5.6°, lowest deck edge still 23.8 mm above water | ✅ (just over the app's 5° comfort limit) |
| Wave test, H = 30–40 mm, T = 0.8 s, 400 g | Heave 16–22 mm, pitch 10–14°, roll 7–9°; relative motion 12–16 mm vs 33.7 mm freeboard | ✅ no water on deck |
| Very short steep waves (H ≥ 30 mm, T ≈ 0.6 s, steepness > 0.05) | Spray can reach the deck at 400 g | ⚠️ cannot sink (sealed hulls); stay at ≤ 250 g if such waves are announced |
| CFD in turbulent water | 13 % less wetted surface than the earlier box catamaran at the same 400 g load (510 vs 584 cm²); fine entry, rocker bow, rounded bilges | ✅ expected better; the real score comes from the judges' CFD |
| Electronics dry and above water | Cradle on deck centreline, ~75 mm above the keel | ✅ |
| Hull design originality | Custom wave-piercer + modular gap, not a GrabCAD model | ✅ |

Comparison decks: gap 40 at 400 g has GM only 12 mm and rolls up to 27° in beam waves. It is useful only to show why the wide stance wins. One demihull alone is unstable (GM about −40 mm) and tips over: that is the "why catamaran, why no ballast" demo.

## Why this shape wins (pitch points)
- **CFD and waves:**
  - Slender hulls (L/B ≈ 4.7 each) with a tangent fine entry and a wave-piercing rocker bow cut wave resistance and slamming.
  - Rounded bilges reduce corner vortices.
  - Wetted surface is 13 % lower than the box catamaran.
- **Ballast-free stability:** hull spacing gives the stability. At 400 g, GM goes from 12 mm to 113 mm as the gap goes from 40 to 100 mm, with no ballast and no servos.
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
