# Print notes - Arova ballast-free ship (team ICT)

| File | Size (L x B x H) | Orientation on the bed | Est. PLA (light settings) |
|---|---|---|---|
| `arova_v2_catamaran.stl` | 235 x 160 x 55 mm | **Deck down** (flat deck on the bed, pontoons upward) - no supports, no bridging | ~185 g |
| `arova_v1_monohull.stl` | 235 x 104 x 55 mm | Flat bottom down - no supports | ~135 g |

Both are single watertight solids, units **mm**, within the 250 x 250 x 250 mm limit. Material: basic PLA.

## Slicer settings (light and fast, still watertight)
- Layer height 0.2-0.28 mm, nozzle 0.4 mm
- **Walls: 2** (0.8 mm), **top/bottom: 4 layers** - keeps it watertight
- **Infill: lightning (or gyroid 3-5 %)** - the hull is a closed air box, infill only supports the top skin
- No supports, no brim needed (large flat face on the bed); add a brim only if corners lift
- If only one hull can be printed: **v2 catamaran** first

## After printing
1. **Weigh** each hull (0.1 g scale) and enter the mass in the app sidebar - do not use the slicer estimate.
2. Coat the outside with the water-based sealant; let it dry; weigh again.
3. Mark the draught scale (mm tape) at bow, stern and both sides for Test A.

Why box hulls: the app's hydrostatics assume wall-sided pontoons, so these shapes let the tank tests check the
calculations directly. Regenerate or change dimensions with `python3 print/make_stl.py`.
