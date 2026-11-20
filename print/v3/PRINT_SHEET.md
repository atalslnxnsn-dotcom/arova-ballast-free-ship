# Arova v3 — print sheet for the printer operators

**Team:** ICT · **Ship:** v3 ballast-free catamaran, competition set-up **gap 100 mm** · Material: basic PLA · Units: mm

## What to print (priority order)
| # | File | Qty | Size (mm) | On the bed | Est. PLA each* | Est. time each* |
|---|---|---|---|---|---|---|
| 1 | `arova_v3_demihull_x2.stl` | **2** | 235 × 50 × 70 | **as saved**: flat top face down, keel up | 125 g | 5.6 h / 2.3 h |
| 2 | `arova_v3_deck_gap100.stl` | 1 | 150 × 205 × 14 | as saved: plate down, flanges up | 98 g | 4.4 h / 1.8 h |
| 3 | `arova_v3_electronics_cradle.stl` | 1 | 60 × 27 × 12 | as saved: base down | 7 g | 0.3 h |
| 4 | `arova_v3_deck_gap70.stl` | 1 | 150 × 175 × 14 | as saved | 87 g | 3.9 h / 1.6 h |

Print #4 (the gap 70 deck) **only if there is printer time left**. It is the backup deck for very short, steep beam waves.

\* Watertight profile. Times are for a typical printer / a fast CoreXY printer. They are estimates from the STL surface area and volume (`print_estimate.py`). **The slicer's number wins.**

**All 4 parts on separate printers at the same time:** about 2.3–5.6 h in total. **One printer, one part after another:** about 6.6–16 h.

## Slicer settings (watertight profile)
- Layer 0.2 mm, nozzle 0.4 mm, PLA at its normal temperatures.
- **Walls: 3**, **top/bottom: 5 layers** - the hulls are sealed air boxes and must not leak.
- **Infill: 5 % gyroid** (or lightning).
- **No supports, no rotation.** The files are already in print orientation (checked: 0 cm² of overhang steeper than 45°).
- Brim only if corners lift. **Elephant-foot compensation 0.15–0.2 mm if available.** The hulls also have a 0.8 mm chamfer on the bed edge for the same reason.

**If time is short (fast profile):** 2 walls, 4 top/bottom layers, lightning infill. About 234 g in total, about 30–40 % faster. The hulls then depend more on the varnish to stay watertight.

## Checks done before sending (`verify_v3.py`, all passed)
- Every part is one closed, watertight solid with outward normals; the largest dimension is 235 mm (limit 250 mm).
- Hydrostatic table vs the hull mesh: within 0.15 % over 14 draughts.
- Deck slot 50.60 mm on a 50.00 mm hull: 0.30 mm clearance per side.

## CFD (not printed)
- Send **`arova_v3_CFD_hulls_gap100.stl`** to the CFD software: both hulls in sailing position, keel at z = 0, x toward the bow, two closed shells 100 mm apart.
- `arova_v3_assembly_gap100_CFD.stl` includes the deck. It is **for display only**: its deck sits 0.1–0.3 mm from the hulls.

## After printing (team)
1. Weigh every part (0.1 g scale) and enter the masses in the app.
2. Dry-fit the deck on both hulls. If it is tight, sand the top 1 mm of the hull sides lightly.
3. Varnish the hulls (water-based sealant), let them dry, weigh again.
4. Hold the deck with 2 rubber bands or zip ties per hull.
