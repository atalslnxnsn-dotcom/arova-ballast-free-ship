# Ballast-Free Ship Operations (Arova Engineering Challenge 2026, ICT track)

One app for a ballast-free model vessel: cargo layout & stability, load-limit prediction, baseline vs revised hull,
density-aware route planner with real passage limits, roll/pitch/heave dashboard, and validation against tank tests.

**Live demo:** https://atalslnxnsn-dotcom-arova-ballast-free-ship-app-qgbvdu.streamlit.app/

## Run
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 test_hydro.py        # calculation tests (hand calculations, published values, synthetic data)
streamlit run app.py
```

## Tabs
1. **Cargo & stability** - draught, freeboard, GM, heel/trim, predicted load limit (and which limit binds), feasible correction.
2. **Hull comparison** - v1 vs v2 with same cargo/water, load sweep, drag at matched speed, JSON export.
3. **Route planner** - choose destination; waypoint salinity → density (EOS-80) → draught; full-scale draught
   (model × N) vs real passage limits; recommends the shortest route that passes, or how much cargo to unload.
4. **Ship dashboard** - regular-wave heave/pitch/roll (linear, documented) or uploaded CSV; automatic roll-decay
   analysis (Tn, ζ, k) with a button to use the measured k; alerts for roll, pitch and green water.
5. **Validation** - Test A draught vs load, Test B inclining experiment → measured GM → real hull VCG (button to use it),
   Test C roll decay (via tab 4).

## Where each judging criterion is covered
| Criterion (points) | Where in the app / repo |
|---|---|
| Cargo capacity, draught, buoyancy (15) | Tab 1 (load limit, draught, GM, correction), tab 2 (v1 vs v2) |
| Map-based route planning & decision support (15) | Tab 3 (destination, density map, passage limits, unload advice) |
| Interface, tilt monitoring, warnings (10) | Tab 4 (heave/pitch/roll, alerts, CSV + roll-decay analysis) |
| Engineering & validation (20) | Tab 5 (Tests A/B/C), `test_hydro.py`, measured data in `sample_data/` |
| Working demonstration (20) | Live demo link above |

## Files
- `hydro.py` - all calculations, no UI. `app.py` - Streamlit interface. `test_hydro.py` - tests.
- `print/` - printable box hulls that match the app (v1 monohull, v2 catamaran), print settings in `PRINT_NOTES.md`.
- `tools/mpu6050_logger/` - Arduino sketch (CSV `t,roll,pitch` at ~100 Hz); `tools/log_serial.py` - saves it to a file.
- `sample_data/` - sample (simulated, labelled) and measured test data.

## Method & assumptions (labels: calculated / simulated / measured / estimated)
| Item | Model | Status |
|---|---|---|
| Hull | Wall-sided rectangular pontoons | Assumption - validate with Test A |
| Hull VCG | 45 % of depth until measured | Replace with inclining result (Test B) |
| Roll k | 0.40 × overall beam until measured | Replace with roll-decay result (Test C) |
| Stability | Small-angle GM, heel = atan(yCG/GM); warning when the deck edge immerses | Standard |
| Waves | Linear dispersion, hull-averaged excitation, 1-DOF magnification, a33 = a55 = 0.5, k_yy = 0.25 L | Assumed coefficients |
| Water density | UNESCO EOS-80 | Standard |
| Route salinity/temperature | Typical November surface values; Kiel Canal value is a placeholder | Estimate |
| Passage limits | Kiel 9.5 m (ships ≤160 m), Drogden 8.0 m, Great Belt Route T ~17 m, Turku ~10 m, Elbe ~13.5 m, Gdańsk DCT 16.5 m | Sourced (map tooltip) |
| Drag | F = 0.5 ρ Cd A v², Cd assumed | Estimate |
