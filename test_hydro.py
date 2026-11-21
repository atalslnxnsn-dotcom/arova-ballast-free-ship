"""Hand-checkable tests. Run: python3 test_hydro.py"""
from math import isclose, degrees, atan
from hydro import (Hull, Cargo, analyse, seawater_density, check_layout, suggest_rebalance,
    route_profile, ROUTES, ROUTES_BY_DEST, simulate_roll, wave_number, wave_motions, roll_decay,
    k_from_period, inclining_gm, roll_stats, haversine_km, load_limit, check_suggestion, pick_route,
    unload_to_fit)
from math import sin as SIN

# EOS-80 published check values
assert isclose(seawater_density(35, 25), 1023.343, abs_tol=0.01)
assert isclose(seawater_density(0, 4), 999.975, abs_tol=0.01)
assert seawater_density(6, 8) < seawater_density(35, 10)

# Monohull box: KB = T/2, BM = B^2/(12T), all by hand
mono = Hull("box", length=0.2, beam=0.1, depth=0.05, mass=0.5, kg_hull=0.02)
r = analyse(mono, [], rho=1000.0)
T = 0.5 / 1000 / (0.2 * 0.1)                     # 0.025 m
assert isclose(r.draft, T)
assert isclose(r.gm, T / 2 + 0.1**2 / (12 * T) - 0.02)
assert r.heel_deg == 0 and not r.warnings

# Off-centre cargo: heel = atan(yCG/GM)
c = [Cargo("box", 0.1, 0.0, 0.02, 0.04, 0.04, 0.02)]
r = analyse(mono, c, rho=1000.0)
assert isclose(r.ycg, 0.1 * 0.02 / 0.6)
assert isclose(r.heel_deg, degrees(atan(r.ycg / r.gm)))

# Catamaran is stiffer than a monohull with the same waterplane area
cat = Hull("cat", 0.235, 0.052, 0.055, n_pontoons=2, gap=0.056)
mon = Hull("mono", 0.235, 0.104, 0.055)
load = [Cargo("load", 0.4, 0, 0.02, 0.05, 0.05, 0.03)]
rc, rm = analyse(cat, load, 999.1), analyse(mon, load, 999.1)
assert isclose(rc.draft, rm.draft)
assert rc.gm > 0 > rm.gm                          # 400 g on deck: catamaran stable, monohull capsizes
assert any("UNSTABLE" in w for w in rm.warnings) and rm.min_freeboard == 0.0

# Overload sinks, high cargo goes unstable
assert any("SINKS" in w for w in analyse(cat, [Cargo("x", 2.0, 0, 0, 0.1, 0.1, 0.05)], 1000).warnings)
assert any("UNSTABLE" in w for w in analyse(mon, [Cargo("tower", 0.4, 0, 0, 0.03, 0.03, 0.4)], 1000).warnings)

# Layout checks
assert check_layout(cat, [Cargo("out", 0.1, 0.2, 0, 0.05, 0.05, 0.05)])
assert check_layout(cat, [Cargo("a", 0.1, 0, 0, 0.05, 0.05, 0.05), Cargo("b", 0.1, 0.01, 0, 0.05, 0.05, 0.05)])

# Rebalance suggestion brings yCG back to zero
items = [Cargo("a", 0.3, 0, 0.03, 0.04, 0.04, 0.03), Cargo("b", 0.1, 0.05, -0.02, 0.04, 0.04, 0.03)]
r = analyse(cat, items, 1000)
name, new_y, new_x = suggest_rebalance(items, r.total_mass, r.ycg, r.xcg)
items[0].y, items[0].x = new_y, new_x
assert isclose(analyse(cat, items, 1000).ycg, 0, abs_tol=1e-12)

# Routes: lower density -> deeper draft; worst point is the brackish canal on route A
assert isclose(haversine_km((60.0, 20.0), (61.0, 20.0)), 111.2, abs_tol=0.2)
rows, s = route_profile(cat, load, ROUTES_BY_DEST["Rotterdam"]["via Kiel Canal"])
assert s["worst_point"] == "Kiel Canal" and s["distance_km"] > 0

# Roll sim: free decay at the natural period is recovered by roll_stats
t, roll, _ = simulate_roll(1.0, 0.0, wave_amp_deg=0.0, damping=0.01, initial_deg=10, duration_s=10)
amp, period = roll_stats(t, roll)
assert isclose(period, 1.0, rel_tol=0.03), period

# Load limit: just under passes, just over fails; off-centre cargo lowers the limit
from dataclasses import replace
centre = [Cargo("c", 0.2, 0, 0, 0.05, 0.04, 0.025)]
lim_c, why = load_limit(cat, centre, 1000)
assert not analyse(cat, [replace(centre[0], mass=lim_c * 0.99)], 1000).warnings
assert analyse(cat, [replace(centre[0], mass=lim_c * 1.01)], 1000).warnings and why
lim_off, _ = load_limit(cat, [replace(centre[0], y=0.03)], 1000)
assert lim_off < lim_c

# Rebalance feasibility: off-deck move is rejected, centring move is accepted
two = [Cargo("a", 0.2, 0, 0.02, 0.05, 0.04, 0.025), Cargo("b", 0.05, 0.06, 0, 0.04, 0.04, 0.025)]
assert not check_suggestion(cat, two, 1000, "a", 0, 0.5)[0]
assert check_suggestion(cat, two, 1000, "a", 0, 0.0)[0]

# Route pick: draft limit just below route A's max draft excludes it
summ = {n: route_profile(cat, centre, w)[1] for n, w in ROUTES_BY_DEST["Rotterdam"].items()}
assert pick_route(summ) == "via Kiel Canal"                                  # shortest
alt = pick_route(summ, summ["via Kiel Canal"]["max_draft_mm"] - 1e-6)        # canal too deep -> another route
assert alt and alt != "via Kiel Canal"
assert pick_route(summ, 0.0) is None

# Regressions from the Codex review (counterexamples that used to pass silently)
h = Hull("cat", .235, .052, .055, 2, .056)
ok, why, after = check_suggestion(h, [Cargo("heavy", 2, 0, .02, .05, .04, .025)], 1000, "heavy", 0, 0)
assert not ok and "SINKS" in why                                   # 1) improving but sinking move is not "safe"
cap, why = load_limit(h, [Cargo("outside", .2, .3, 0, .05, .04, .025)], 1000)
assert cap is None and "outside" in why                            # 2) no capacity for an invalid layout
r = analyse(Hull("short-wide", .05, .2, .1, mass=.5, kg_hull=.09), [], 1000, min_freeboard_m=0, min_gm_m=0)
assert r.gm_long < 0 and any("longitudinal" in w for w in r.warnings)   # 3) explicit GM_L <= 0 error

# Codex review 2, P1: the 160 mm catamaran at 1:400 is 64 m wide - Kiel Canal (max 32.5 m) must be blocked
kiel = ROUTES_BY_DEST["Rotterdam"]["via Kiel Canal"]
_, sb = route_profile(cat, centre, kiel, scale=400)
assert not sb["limit_ok"] and "32.5" in sb["blocked"] and sb["binding_point"] == "Kiel Canal"
assert unload_to_fit(cat, centre, kiel, 400) is None                # unloading cannot fix a beam limit
summ = {n: route_profile(cat, centre, w, scale=400)[1] for n, w in ROUTES_BY_DEST["Rotterdam"].items()}
assert pick_route(summ) != "via Kiel Canal"

# Draught limit on a ship small enough for the canal: scale so the deepest point is 9.6 m in the canal
nar = Hull("narrow", 0.235, 0.08, 0.045, mass=0.4, kg_hull=0.01)   # stable and canal-sized at ~1:300
lowc = [Cargo("c", 0.2, 0, 0, 0.05, 0.04, 0.01)]
assert not analyse(nar, lowc, 1000).warnings
rows0, _ = route_profile(nar, lowc, kiel)
N = 9.6 / [r for r in rows0 if r["waypoint"] == "Kiel Canal"][0]["deepest_mm"] * 1000
_, s1 = route_profile(nar, lowc, kiel, scale=N)
assert nar.length * N <= 160 and not s1["blocked"]                 # size passes, so the 9.5 m step applies
assert not s1["limit_ok"] and s1["binding_point"] == "Kiel Canal"
g = unload_to_fit(nar, lowc, kiel, N)
assert g and g > 0
fixed = [replace(lowc[0], mass=lowc[0].mass - g / 1000)]
assert route_profile(nar, fixed, kiel, scale=N)[1]["limit_ok"]     # the advised (rounded-up) unload really fits
summ = {n: route_profile(nar, lowc, w, scale=N)[1] for n, w in ROUTES_BY_DEST["Rotterdam"].items()}
assert pick_route(summ) == "via Great Belt + Skagen"                # 9.6 m also exceeds Drogden 8 m

# Codex review 2, P1: limits are checked on the deepest (heeled) corner, not the mean draught
off = [Cargo("off", 0.2, 0, 0.02, 0.05, 0.04, 0.025)]
rows_o, _ = route_profile(nar, off, kiel)
ko = [r for r in rows_o if r["waypoint"] == "Kiel Canal"][0]
assert ko["deepest_mm"] > ko["draft_mm"]
N2 = 9.5 / (ko["draft_mm"] + ko["deepest_mm"]) * 2 * 1000            # mean below 9.5 m, deepest corner above
_, so = route_profile(nar, off, kiel, scale=N2)
row = [r for r in route_profile(nar, off, kiel, scale=N2)[0] if r["waypoint"] == "Kiel Canal"][0]
assert row["mean_full_draft_m"] < 9.5 < row["full_draft_m"] and not so["limit_ok"]

# Codex review 2, P2: an unload that clears one limit but not another is never advised
two_lim = [("A", 55.0, 12.0, 10.0, 10.0, 9.0, "test"), ("B", 55.5, 12.5, 5.0, 10.0, 9.0, "test")]
g2 = unload_to_fit(nar, centre, two_lim, 400)
assert g2 and route_profile(nar, [replace(centre[0], mass=centre[0].mass - g2 / 1000)], two_lim, 400)[1]["limit_ok"]

# Codex review 2, P2: unknown permitted draught is reported as unverified, Muuga 18 m depth is not a draught limit
_, ss = route_profile(cat, centre, ROUTES_BY_DEST["Stockholm"]["Aland Sea"], scale=400)
assert ss["unverified"] == ["Stockholm"]
assert all(r["limit_m"] is None for r in route_profile(cat, centre, ROUTES_BY_DEST["Tallinn"]["Gulf of Finland"])[0]
           if r["waypoint"] == "Tallinn (Muuga)")

# Codex review 2, P3: bad inputs fail loudly instead of returning a silent "OK"
for bad in (0, -1, float("nan")):
    try:
        route_profile(cat, centre, kiel, scale=bad); raise AssertionError("bad scale accepted")
    except ValueError:
        pass
try:
    route_profile(cat, centre, []); raise AssertionError("empty route accepted")
except ValueError:
    pass

# Dispersion: deep water k = w^2/g; finite depth satisfies g k tanh(kh) = w^2; shallow -> w/sqrt(gh)
from math import pi as PI, tanh as TANH, sqrt as SQRT, exp as EXP, cos as COS
w = 2 * PI / 0.8
assert isclose(wave_number(0.8), w * w / 9.81)
k = wave_number(0.8, 0.3)
assert isclose(9.81 * k * TANH(k * 0.3), w * w, rel_tol=1e-9)
assert isclose(wave_number(20, 0.05), (2 * PI / 20) / SQRT(9.81 * 0.05), rel_tol=0.01)

# Long-wave limit: heave -> a, pitch -> wave slope k*a (static response, magnification -> 1)
rc = analyse(cat, centre, 1000)
m = wave_motions(cat, rc, 0.02, 30.0)
assert isclose(m["heave_m"], 0.01, rel_tol=0.01)
assert isclose(m["pitch_deg"], degrees(wave_number(30.0) * 0.01), rel_tol=0.01)
assert m["T_heave"] > 0 and m["T_pitch"] > 0

# Roll decay: recover Tn and zeta from a synthetic noisy free decay
import random
rs = random.Random(0)
Tn, z = 0.5, 0.06
wn = 2 * PI / Tn
tt = [i * 0.005 for i in range(1200)]
xx = [2.0 + 10 * EXP(-z * wn * ti) * COS(wn * SQRT(1 - z * z) * ti) + rs.gauss(0, 0.05) for ti in tt]
d = roll_decay(tt, xx)
assert d and isclose(d["Tn"], Tn, rel_tol=0.02) and abs(d["zeta"] - z) < 0.01, d
assert roll_decay(tt[:50], xx[:50]) is None                         # too short -> no fake result
# Noisy small-amplitude cycles used to bias damping low (0.059 instead of 0.08); smoothing pass fixes it
_, rr8, _ = simulate_roll(0.4, 0, 0, 1.0, 0.08, initial_deg=10, duration_s=10.0, dt=0.01)
t8 = [i * 0.01 for i in range(len(rr8))]
for seed in (1, 2, 3):
    rs = random.Random(seed)
    d8 = roll_decay(t8, [v + rs.gauss(0, 0.3) for v in rr8])
    assert abs(d8["zeta"] - 0.08) < 0.01 and isclose(d8["Tn"], 0.4, rel_tol=0.02), d8

# k from period is the inverse of the roll-period formula; a measured k_roll is used
assert isclose(k_from_period(rc.roll_period, rc.gm), 0.40 * cat.overall_beam)
assert isclose(analyse(replace(cat, k_roll=0.05), centre, 1000).roll_period, 2 * PI * 0.05 / SQRT(9.81 * rc.gm))

# Inclining test: angles generated from a known GM are inverted back
GM, D = 0.012, 0.55
ws, ds = [0.01, 0.02, 0.01, 0.02], [0.03, 0.03, -0.03, -0.03]
angs = [degrees(atan(wi * di / (D * GM))) for wi, di in zip(ws, ds)]
gm_fit, r2, th0 = inclining_gm(ws, ds, angs, D)
assert isclose(gm_fit, GM, rel_tol=1e-9) and r2 > 0.999 and abs(th0) < 1e-9
assert inclining_gm([0.01, 0.02], [0.03, 0.03], [1.0, 2.0], D) is None      # < 3 points
# Codex review 2, P2: a 0.5 deg initial list used to turn GM 200 mm into 165 mm; the intercept absorbs it
from math import tan as TAN, radians as RAD
GM2, D2 = 0.200, 0.30
ws2, ds2 = [0.025, 0.05, 0.025, 0.05, 0.0], [0.06, 0.06, -0.06, -0.06, 0.0]
angs2 = [degrees(atan(TAN(RAD(0.5)) + wi * di / (D2 * GM2))) for wi, di in zip(ws2, ds2)]
gm2, r22, th02 = inclining_gm(ws2, ds2, angs2, D2)
assert isclose(gm2, GM2, rel_tol=1e-6) and isclose(th02, 0.5, rel_tol=1e-6)

# Codex review 2, P2: decay analysis rejects non-decays and bad time axes, and works on heavy damping
grow = [EXP(0.05 * 2 * PI / 0.5 * ti) * COS(2 * PI / 0.5 * ti) for ti in tt]
assert roll_decay(tt, grow) is None                                  # growing oscillation
assert roll_decay([], []) is None and roll_decay([0.0] * 50, xx[:50]) is None and roll_decay(tt[::-1], xx) is None
assert roll_decay(tt[:20], [float("nan")] * 20) is None
heavy = [10 * EXP(-0.15 * wn * ti) * COS(wn * SQRT(1 - 0.0225) * ti) for ti in tt]
dh = roll_decay(tt, heavy)
assert dh and abs(dh["zeta"] - 0.15) < 0.01 and isclose(dh["Tn"], Tn, rel_tol=0.02), dh

# Codex review 2, P1/P2: finite-depth pressure attenuation, keel clearance and relative motion (green water)
from math import cosh as COSH
k3 = wave_number(0.45, 0.03)
m3 = wave_motions(cat, rc, 0.01, 0.45, 0.03)
u = k3 * cat.length / 2
assert isclose(m3["heave_qs_m"], abs(0.005 * COSH(k3 * (0.03 - rc.draft)) / COSH(k3 * 0.03) * SIN(u) / u), rel_tol=1e-9)
assert wave_motions(cat, rc, 0.01, 1.0, 0.015)["keel_clearance_m"] < 0  # 15 mm water under a 22.5 mm draught
assert wave_motions(cat, rc, 0.02, 30.0)["rel_motion_m"] < 0.1 * 0.01  # long waves: hull follows the surface
assert isclose(wave_motions(cat, rc, 0.02, 0.15)["rel_motion_m"], 0.01, rel_tol=0.1)  # short waves: hull still
ms = wave_motions(cat, rc, 0.038, 0.35, 0.3)                         # wave shorter than the hull
assert ms["heave_m"] >= 0 and ms["pitch_deg"] >= 0 and ms["roll_deg"] >= 0   # amplitudes never negative
assert ms["rel_motion_m"] > 0.019                                     # short wave: relative motion exceeds the wave amplitude
from hydro import magnification
assert magnification(1.0, 0.0) == float("inf")
try:
    wave_number(-20, 0.05); raise AssertionError("negative period accepted")
except ValueError:
    pass

print("all hydro tests passed")

# ---------- table hulls (printed v3) ----------
from hydro import hydrostatics_at, load_v3_hull, v3_configs
# 1) A box written as a table must reproduce the wall-sided formulas exactly
Awp, It, Il = cat.waterplane_area, cat.i_transverse, cat.i_longitudinal
box_rows = tuple((T, Awp * T, T / 2, 0.0, Awp, It, Il) for T in [i * 0.0005 for i in range(1, 111)])
cat_tab = replace(cat, table=box_rows)
for load in (centre, off, []):
    a_, b_ = analyse(cat, load, 1000), analyse(cat_tab, load, 1000)
    assert isclose(a_.draft, b_.draft, rel_tol=1e-9) and isclose(a_.gm, b_.gm, rel_tol=1e-9)
    assert isclose(a_.gm_long, b_.gm_long, rel_tol=1e-9) and isclose(a_.reserve_buoyancy_kg, b_.reserve_buoyancy_kg)
# 2) v3 table agrees with make_v3's own (independent, step-width) draught solver: 251 g ship + 250 g, gap 70
import sys as _sys
_sys.path.insert(0, "print/v3")
import make_v3 as _mv3
assert "2 hulls, gap 70 mm" in v3_configs()
v3 = load_v3_hull("2 hulls, gap 70 mm", mass=0.251)
r3 = analyse(v3, [Cargo("load", 0.25, v3.deck_xc, 0, 0.05, 0.04, 0.025)], 1000)
assert abs(r3.draft * 1000 - _mv3.draft_for(501, 70.0)) < 0.4, (r3.draft, _mv3.draft_for(501, 70.0))
assert r3.lcb < 0                                             # fine bow -> buoyancy centre aft of midship
# 3) Trim is measured against the LCB, and the rebalance suggestion levels the v3 hull
items3 = [Cargo("a", 0.2, v3.deck_xc + 0.03, 0.01, 0.04, 0.04, 0.02)]
r3a = analyse(v3, items3, 1000)
nm, ny, nx = suggest_rebalance(items3, r3a.total_mass, r3a.ycg, r3a.xcg - r3a.lcb)
items3[0].x, items3[0].y = nx, ny
lev = analyse(v3, items3, 1000)
assert abs(lev.trim_deg) < 0.2 and abs(lev.heel_deg) < 1e-6, (lev.trim_deg, lev.heel_deg)
# 4) The deck is shorter than the hulls and sits aft: a box near the bow is off the deck
assert check_layout(v3, [Cargo("bow", 0.1, 0.09, 0, 0.04, 0.04, 0.02)])
assert not check_layout(v3, [Cargo("mid", 0.1, v3.deck_xc, 0, 0.04, 0.04, 0.02)])
# 5) One demihull alone (monohull test) is much less stable than the catamaran
r1 = analyse(load_v3_hull("1 hull (monohull test)", mass=0.09), [Cargo("w", 0.05, 0, 0, 0.03, 0.03, 0.01)], 1000)
assert r1.gm < r3.gm

print("table hull tests passed")
# 6) Hull mass sits at the hull's own LCG (not midship): the empty v3 floats almost level
e3 = load_v3_hull("2 hulls, gap 70 mm", mass=0.251)
assert e3.lcg_hull < 0 and abs(analyse(e3, [], 1000).trim_deg) < 1.0, analyse(e3, [], 1000).trim_deg   # was 3.5 deg
print("v3 LCG test passed")
# 7) Relative motion at chosen stations: hull ends agree with rel_motion_m; midship moves least in long waves
mx = wave_motions(cat, rc, 0.02, 0.6, 0.3, x_points=(cat.length / 2, -cat.length / 2, 0.0))
assert isclose(max(mx["rel_at"][cat.length / 2], mx["rel_at"][-cat.length / 2]), mx["rel_motion_m"])
print("x_points test passed")
# 8) v3 without a measured KG uses the STL-based estimate, not 45 % of depth (which overstated GM by ~14 mm)
from hydro import v3_estimates
m_est, kg_est = v3_estimates()["2 hulls, gap 100 mm"]
h_est = load_v3_hull("2 hulls, gap 100 mm", m_est)
assert isclose(h_est.vcg, kg_est) and kg_est > 0.45 * h_est.depth
h_old = replace(h_est, kg_hull=0.0)                       # the old default
load400 = [Cargo("load", 0.4, h_est.deck_xc, 0, 0.06, 0.06, 0.03)]
# GM error = KG error x hull-mass share: ~14 mm empty, ~6.5 mm with 400 g on board
assert analyse(h_old, [], 1000).gm - analyse(h_est, [], 1000).gm > 0.012
assert analyse(h_old, load400, 1000).gm - analyse(h_est, load400, 1000).gm > 0.005
print("v3 KG estimate test passed")
