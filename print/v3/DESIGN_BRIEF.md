# Arova v3 "Wave-Piercer" modular catamaran: CAD design brief

Paste this into the CAD tool (SolidCraft). Units are mm. Reference STLs made from exactly these numbers are in this folder. They are watertight and their dimensions are checked.

## Goal and rules it must meet
- Arova "Ballast Free Ship": stay stable under 150–400 g cargo **without ballast water**.
- Size limit: every part and the assembly must fit in **250 × 250 × 250 mm**.
- Material: basic PLA. Sealing: water-based 3D-print varnish.
- The judges run the STL through CFD in medium turbulent water. Fluid efficiency, originality and sustainability score points.
- Brief ideas covered here:
  - adjustable hull spacing
  - each hull can be tested alone as a monohull
  - MPU-6050 kept dry on deck
  - stability from hull shape and low weight, not ballast

## Parts (4 printed parts; print the demihull twice)

### 1. Demihull (print ×2, identical)
- Overall 235 long (x), 50 wide (y), 55 high (z). Keel at z = 0, flat top deck at z = 55.
- **Plan shape (waterline):**
  - Transom 40 wide at x = 0, widening to full 50 by x = 25.
  - Parallel middle body 50 wide from x = 25 to x = 150.
  - Bow from x = 150 to 235: fine entry, half-beam = 25·(1 − t^1.8) with t = (x−150)/85, ending in a 2 mm wide tip (not a knife edge).
- **Sections:** sides are **vertical** from the bilge up to the deck. Bottom is flat, with a **6 mm bilge radius** on both lower edges. The radius shrinks where the hull narrows at the bow.
- **Keel rocker:** the keel is flat to x = 185, then rises as 16·((x−185)/50)² mm, reaching 16 mm at the bow tip. This is a wave-piercing bow that lifts less in waves.
- Closed solid, no holes, no sockets. Nothing can leak.
- Print **upside down** (flat deck face on the bed): no supports. 2 walls (0.8 mm), 4 top/bottom layers, 3–5 % gyroid or lightning infill.

### 2–4. Clip-on deck (three versions: hull gap 40 / 70 / 100 mm)
- Flat plate 150 long × 3 thick. It sits on top of both hulls from x = 25 to x = 175, over the parallel body.
- Under the plate, at each hull, a **saddle** of two flanges: 12 deep, 2.4 thick, 0.3 clearance each side of the 50 mm hull. The deck slides down over the hulls.
- Overall width = 2·50 + gap + 2·(0.3 + 2.4): **145 / 175 / 205 mm** for gaps 40 / 70 / 100.
- Hold the deck and hulls with 2 rubber bands or zip ties per hull. A drop of glue is OK for the final run.
- Print plate-down, flanges up: no supports.
- MPU-6050 + microcontroller go on the deck centreline in a zip bag or small box, above the water.

## Calculated performance (fresh water, from exact section integration of this geometry)
Estimated ship mass (2 hulls + deck) is about 250 g. Cargo centre of gravity is assumed 15 mm above the deck. Empty-ship KG is assumed at 0.5·depth until the inclining test.

| Gap | Overall beam | Load | Draft | Freeboard | GM (transverse) |
|---|---|---|---|---|---|
| 70 mm (default) | 175 | 0 g | 13.0 | 42.0 | 282 |
| 70 mm | 175 | 150 g | 20.4 | 34.6 | 158 |
| 70 mm | 175 | 250 g | 25.3 | 29.7 | 116 |
| 70 mm | 175 | **400 g** | **32.7** | **22.3** | **79** |
| 40 mm | 145 | 400 g | 32.2 | 22.8 | 31 |
| 100 mm | 205 | 400 g | 33.2 | 21.8 | 141 |
| One demihull alone + 50 g | 50 | | 14.4 | | about −6 (tips over) |

- At the full 400 g, freeboard stays above 20 mm and GM stays positive at every gap. Wider gap means more stability.
- One hull alone is unstable. That is the "why catamaran, why no ballast" demo.

## Why this shape wins (pitch points)
- **CFD and waves:**
  - Slender hulls (L/B ≈ 4.7 each) with a fine entry and a wave-piercing rocker bow cut wave resistance and slamming.
  - Rounded bilges reduce corner vortices in turbulent water.
- **Ballast-free stability:** hull spacing gives the stability. The app shows GM rising from 31 mm to 141 mm as the gap goes from 40 to 100 mm, with no ballast and no servos.
- **Validation-friendly:** sides are vertical through the whole waterline band. In the app pick **Type → v3 wave-piercer (printed)** and the printed gap: it uses the exact hydrostatic table of this shape (`data/v3_hydrostatics.json`, made by `make_v3_table.py`), including the aft-shifted centre of buoyancy.
- **Sustainability:** about 250 g PLA for the whole ship (a box catamaran of the same size needs more). Parts are reusable and swappable. There is no ballast water, which means no invasive-species transfer.
- **Modular test rig:** one set of hulls gives four configurations (gap 40 / 70 / 100, monohull). Same hulls, so the comparison is fair.

## Acceptance checks before printing
1. Each part is a single watertight solid; the bounding box is under 250 mm.
2. The demihull solid volume is about 551 cm³ (the reference STL value).
3. The deck slides over two hulls with a 0.3 mm gap per side; print one test strip first if the printer is tight.
4. After printing, weigh each part and enter the real mass in the app. Varnish, dry and weigh again.
5. Mark draft lines (mm tape) at bow, midship and stern on both hulls for the draft-vs-load test.

## Files in this folder
- `arova_v3_demihull_x2.stl`: print two
- `arova_v3_deck_gap40.stl`, `arova_v3_deck_gap70.stl` (print this first), `arova_v3_deck_gap100.stl`
- `make_v3.py`: regenerates all parts and the table above (`python3 print/v3/make_v3.py`)
- `arova_v3_preview.png`: render
