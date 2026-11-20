"""Hydrostatics for a small box-pontoon model vessel. SI units: kg, m, s, N, kg/m^3, degrees.

Kept separate from the UI so every number can be checked by hand (see test_hydro.py).
Model: rectangular pontoons (wall-sided), small-angle stability. Valid for heel well below
deck-edge immersion; larger angles are flagged, not trusted.
"""
from dataclasses import dataclass, field, replace
from math import atan, degrees, radians, tan, tanh, cosh, sqrt, pi, cos, sin, exp, asin, isfinite, log, ceil
G = 9.81


# ---------- water density ----------
def seawater_density(salinity_psu: float, temp_c: float) -> float:
    """UNESCO EOS-80 one-atmosphere density (Millero & Poisson 1981). Valid S 0-42, T -2..40."""
    T, S = temp_c, salinity_psu
    rho_w = (999.842594 + 6.793952e-2 * T - 9.095290e-3 * T**2 + 1.001685e-4 * T**3
             - 1.120083e-6 * T**4 + 6.536332e-9 * T**5)
    A = 8.24493e-1 - 4.0899e-3 * T + 7.6438e-5 * T**2 - 8.2467e-7 * T**3 + 5.3875e-9 * T**4
    B = -5.72466e-3 + 1.0227e-4 * T - 1.6546e-6 * T**2
    C = 4.8314e-4
    return rho_w + A * S + B * S**1.5 + C * S**2


WATER_PRESETS = {  # (salinity PSU, temperature C) -> typical surface values, labelled as estimates
    "Fresh water (test tank)": (0.0, 15.0),
    "Baltic Sea (Archipelago, Nov)": (6.0, 8.0),
    "North Sea / Ocean": (35.0, 10.0),
}


# ---------- hull ----------
@dataclass
class Hull:
    name: str
    length: float          # m, each pontoon
    beam: float            # m, each pontoon
    depth: float           # m, pontoon height (deck at this height)
    n_pontoons: int = 1    # 1 = monohull, 2 = catamaran
    gap: float = 0.0       # m, clear gap between pontoons
    mass: float = 0.25     # kg, empty printed model incl. electronics
    kg_hull: float = 0.0   # m, empty-ship VCG above keel; 0 -> depth*0.45 (replace with inclining result)
    k_roll: float = 0.0    # m, roll radius of gyration; 0 -> 0.40*overall beam (replace with roll-decay result)
    lcg_hull: float = 0.0  # m, empty-ship LCG from midship (+ bow); 0 for symmetric box hulls
    # Optional exact hydrostatics for a non-box hull (e.g. the printed v3): rows of
    # (T, V, KB, LCB from midship, Awp, I_T, I_L about LCF), SI units, increasing T. None -> wall-sided box model.
    table: tuple = None
    deck_h: float = 0.0     # m, height of the cargo deck above the keel; 0 -> depth
    deck_len: float = 0.0   # m, usable deck length; 0 -> length
    deck_beam: float = 0.0  # m, usable deck width; 0 -> overall beam
    deck_xc: float = 0.0    # m, deck centre from midship (+ bow)

    @property
    def overall_beam(self):
        return self.n_pontoons * self.beam + (self.n_pontoons - 1) * self.gap

    @property
    def waterplane_area(self):
        return self.n_pontoons * self.length * self.beam

    @property
    def pontoon_offset(self):  # centreline -> pontoon centre
        return 0.0 if self.n_pontoons == 1 else (self.gap + self.beam) / 2

    @property
    def i_transverse(self):
        own = self.length * self.beam**3 / 12
        return self.n_pontoons * (own + self.length * self.beam * self.pontoon_offset**2)

    @property
    def i_longitudinal(self):
        return self.n_pontoons * self.beam * self.length**3 / 12

    @property
    def vcg(self):
        return self.kg_hull or self.depth * 0.45

    @property
    def deck_top(self):
        return self.deck_h or self.depth

    @property
    def max_volume(self):
        """Displaced volume with the hull immersed to its depth (m^3)."""
        return self.table[-1][1] if self.table else self.waterplane_area * self.depth


def hydrostatics_at(hull: Hull, V: float):
    """(T, KB, LCB, Awp, I_T, I_L) for displaced volume V. Box formulas, or linear interpolation in hull.table.

    Beyond the table the hull is extrapolated wall-sided, which only matters for the SINKS warning.
    """
    if not hull.table:
        T = V / hull.waterplane_area
        return T, T / 2, 0.0, hull.waterplane_area, hull.i_transverse, hull.i_longitudinal
    rows = hull.table
    if V >= rows[-1][1]:
        r = rows[-1]
        return (r[0] + (V - r[1]) / r[4],) + tuple(r[2:])
    if V <= rows[0][1]:
        r, f = rows[0], V / rows[0][1]
        return (r[0] * f, r[2] * f, r[3], r[4], r[5], r[6])
    lo, hi = 0, len(rows) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        lo, hi = (mid, hi) if rows[mid][1] <= V else (lo, mid)
    a, b = rows[lo], rows[hi]
    f = (V - a[1]) / (b[1] - a[1])
    return tuple(a[k] + f * (b[k] - a[k]) for k in (0, 2, 3, 4, 5, 6))


@dataclass
class Cargo:
    name: str
    mass: float   # kg
    x: float      # m, + toward bow, from midship
    y: float      # m, + to starboard, from centreline
    lx: float     # m, box length
    ly: float     # m, box width
    lz: float     # m, box height (sits on deck)


@dataclass
class Result:
    total_mass: float
    displaced_volume: float
    draft: float
    freeboard: float
    xcg: float
    ycg: float
    zcg: float
    kb: float
    bm: float
    gm: float
    gm_long: float
    heel_deg: float
    trim_deg: float
    min_freeboard: float
    reserve_buoyancy_kg: float
    roll_period: float
    warnings: list = field(default_factory=list)
    lcb: float = 0.0          # m, longitudinal centre of buoyancy from midship (0 for box hulls)


def check_layout(hull: Hull, cargo: list) -> list:
    """Out-of-bounds and overlap checks on the deck footprint."""
    msgs = []
    dl, db = hull.deck_len or hull.length, hull.deck_beam or hull.overall_beam
    for c in cargo:
        if abs(c.x - hull.deck_xc) + c.lx / 2 > dl / 2 + 1e-9 or abs(c.y) + c.ly / 2 > db / 2 + 1e-9:
            msgs.append(f"'{c.name}' is outside the deck ({dl*1000:.0f} x {db*1000:.0f} mm).")
    for i, a in enumerate(cargo):
        for b in cargo[i + 1:]:
            if abs(a.x - b.x) < (a.lx + b.lx) / 2 - 1e-9 and abs(a.y - b.y) < (a.ly + b.ly) / 2 - 1e-9:
                msgs.append(f"'{a.name}' overlaps '{b.name}'.")
    return msgs


def analyse(hull: Hull, cargo: list, rho: float,
            min_freeboard_m=0.010, max_heel_deg=5.0, min_gm_m=0.005) -> Result:
    items = [(hull.mass, hull.lcg_hull, 0.0, hull.vcg)] + [
        (c.mass, c.x, c.y, hull.deck_top + c.lz / 2) for c in cargo]
    M = sum(m for m, *_ in items)
    xcg = sum(m * x for m, x, _, _ in items) / M
    ycg = sum(m * y for m, _, y, _ in items) / M
    zcg = sum(m * z for m, _, _, z in items) / M

    V = M / rho                                    # Archimedes: V = M / rho
    T, kb, lcb, _, i_t, i_l = hydrostatics_at(hull, V)   # wall-sided box, or the hull's own table
    bm = i_t / V
    gm = kb + bm - zcg
    gm_l = kb + i_l / V - zcg

    heel = degrees(atan(ycg / gm)) if gm > 0 else float("nan")   # heel = atan(yCG/GM)
    trim = degrees(atan((xcg - lcb) / gm_l)) if gm_l > 0 else float("nan")   # trim lever: CG ahead of LCB
    fb = hull.depth - T
    edge = hull.overall_beam / 2
    if gm > 0 and gm_l > 0:
        min_fb = fb - edge * abs(tan(radians(heel))) - hull.length / 2 * abs(tan(radians(trim)))
    else:
        min_fb = 0.0  # unstable: assume capsize, deck edge at the water
    reserve = hull.max_volume * rho - M
    k_roll = hull.k_roll or 0.40 * hull.overall_beam   # measured, else common first estimate
    roll_T = 2 * pi * k_roll / sqrt(G * gm) if gm > 0 else float("nan")

    w = check_layout(hull, cargo)
    if T >= hull.depth:
        w.append(f"SINKS: draft {T*1000:.1f} mm >= hull depth {hull.depth*1000:.0f} mm. Remove {(-reserve)*1000:.0f} g or more.")
    if gm <= 0:
        w.append(f"UNSTABLE: GM = {gm*1000:.1f} mm <= 0. Lower the cargo or widen the hull.")
    elif gm < min_gm_m:
        w.append(f"Low GM {gm*1000:.1f} mm (limit {min_gm_m*1000:.0f} mm).")
    if gm_l <= 0:
        w.append(f"UNSTABLE (longitudinal): GM_L = {gm_l*1000:.1f} mm <= 0. Hull too short for this VCG; it will pitch over.")
    if not all(isfinite(v) for v in (M, T, gm, gm_l)):
        w.append("INVALID: non-finite result - check hull dimensions, masses and density.")
    if heel == heel and abs(heel) > max_heel_deg:
        w.append(f"Heel {heel:.1f} deg exceeds {max_heel_deg:.0f} deg limit.")
    if min_fb < min_freeboard_m:
        w.append(f"Lowest freeboard {min_fb*1000:.1f} mm below {min_freeboard_m*1000:.0f} mm limit (water on deck risk).")
    if heel == heel and abs(radians(heel)) > atan(2 * fb / hull.overall_beam):
        w.append("Deck edge immersed: small-angle model no longer valid.")
    return Result(M, V, T, fb, xcg, ycg, zcg, kb, bm, gm, gm_l, heel, trim, min_fb, reserve, roll_T, w, lcb)


def suggest_rebalance(cargo: list, total_mass: float, ycg: float, xcg: float):
    """Move the heaviest item so the overall CG returns to the centreline/midship."""
    if not cargo:
        return None
    c = max(cargo, key=lambda c: c.mass)
    return c.name, c.y - ycg * total_mass / c.mass, c.x - xcg * total_mass / c.mass


def check_suggestion(hull: Hull, cargo: list, rho: float, name: str, new_x: float, new_y: float, **limits):
    """Apply a move on a copy; return (feasible, reason, new_result).

    Feasible only if the move is on deck, overlap-free, does not lower the freeboard AND the result passes
    every active limit - an improving move that is still unsafe is not offered as a correction.
    """
    moved = [replace(c, x=new_x, y=new_y) if c.name == name else c for c in cargo]
    layout = check_layout(hull, moved)
    if layout:
        return False, " ".join(layout), None
    before, after = analyse(hull, cargo, rho, **limits), analyse(hull, moved, rho, **limits)
    if after.min_freeboard + 1e-9 < before.min_freeboard:
        return False, "Move does not improve heel/freeboard.", after
    if after.warnings:
        return False, "Still unsafe after the move: " + " ".join(after.warnings), after
    return True, "", after


def load_limit(hull: Hull, cargo: list, rho: float, **limits):
    """Largest total cargo mass (kg) that passes every limit, keeping the current positions and mass ratios.

    Returns (max_cargo_kg, limiting_warning); max_cargo_kg is None when the layout is invalid
    (a capacity for an impossible layout would be misleading). Binary search on a common scale factor.
    """
    total = sum(c.mass for c in cargo)
    if total <= 0:
        return 0.0, "No cargo defined."
    layout = check_layout(hull, cargo)
    if layout:
        return None, "Fix the layout first: " + " ".join(layout)

    def fails(k):
        return analyse(hull, [replace(c, mass=c.mass * k) for c in cargo], rho, **limits).warnings

    lo, hi = 0.0, 1.0
    while not fails(hi):          # grow until a limit is hit (sinking guarantees termination)
        lo, hi = hi, hi * 2
    for _ in range(40):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if not fails(mid) else (lo, mid)
    return lo * total, fails(hi)[0]


# ---------- routes ----------
def haversine_km(a, b):
    lat1, lon1, lat2, lon2 = map(radians, (*a, *b))
    h = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371.0 * asin(sqrt(h))


# Waypoint: (name, lat, lon, salinity PSU, temperature C, max permitted draught m or None, source).
# Salinity/temperature: typical November surface values (estimates from SMHI ranges, not live data).
# Draught limits are real passage/port limits for full-scale ships; checked via the model scale 1:N.
# A source containing "not verified" marks a port/passage whose permitted draught we could not confirm.
_W = {
    "Turku": (60.43, 22.22, 5.5, 7.0, 10.0, "Port of Turku main quay ~10 m (Dredgepoint)"),
    "Archipelago Sea": (59.95, 21.4, 6.0, 8.0, None, ""),
    "Aland Sea": (60.0, 19.6, 6.0, 8.0, None, ""),
    "Stockholm": (59.33, 18.07, 5.5, 8.0, None, "permitted draught not verified"),
    "Gulf of Finland W": (59.75, 23.2, 5.5, 8.0, None, ""),
    "Helsinki": (60.15, 24.95, 5.0, 7.5, None, "permitted draught not verified"),
    "Tallinn (Muuga)": (59.50, 24.95, 5.0, 7.5, None,
                        "water depth 18 m is not a permitted draught - permitted draught not verified"),
    "Gotland Basin": (57.5, 19.5, 7.0, 9.0, None, ""),
    "Gdansk": (54.40, 18.67, 7.0, 9.0, 16.5, "Gdansk DCT 16.5 m"),
    "Bornholm": (55.3, 15.0, 7.5, 9.5, None, ""),
    "Arkona": (54.9, 13.6, 8.0, 9.5, None, ""),
    "Fehmarn Belt": (54.6, 11.2, 12.0, 10.0, None, ""),
    "Kiel Bay": (54.5, 10.4, 16.0, 10.0, None, ""),
    "Kiel Canal": (54.1, 9.6, 3.0, 9.0, 9.5,
                   "Kiel Canal: max 235 x 32.5 m; draught 9.5 m up to ~160 m length, ~7 m for the largest ships "
                   "(simplified from the official table, WSV / Kuehne+Nagel); salinity is a placeholder"),
    "Elbe / Hamburg": (53.54, 9.97, 0.5, 9.0, 13.5, "Elbe ~13.5 m tide-independent"),
    "German Bight": (54.0, 7.5, 31.0, 11.0, None, ""),
    "Great Belt (Route T)": (55.35, 11.0, 15.0, 10.0, 17.0, "Route T ~17 m (Danish Maritime Authority)"),
    "The Sound (Drogden)": (55.55, 12.72, 10.0, 10.0, 8.0, "Drogden 8.0 m (Sjofartsverket)"),
    "Kattegat": (57.0, 11.5, 24.0, 10.5, None, ""),
    "Skagen": (57.9, 10.7, 30.0, 11.0, None, ""),
    "Skagerrak": (57.8, 8.0, 33.0, 11.0, None, ""),
    "Rotterdam": (51.98, 4.05, 30.0, 11.0, None, "permitted draught not verified"),
}

# Ship-size limits of locks/canals (full scale, m). draft_by_len: (max length, permitted draught) steps.
PASSAGE_SIZE = {
    "Kiel Canal": dict(max_len=235.0, max_beam=32.5, draft_by_len=((160.0, 9.5), (235.0, 7.0))),
}


def _route(*names):
    return [(n, *_W[n]) for n in names]


_BALTIC_S = ("Turku", "Archipelago Sea", "Aland Sea", "Gotland Basin", "Bornholm", "Arkona")
ROUTES_BY_DEST = {
    "Stockholm": {"Aland Sea": _route("Turku", "Archipelago Sea", "Aland Sea", "Stockholm")},
    "Helsinki": {"Gulf of Finland": _route("Turku", "Archipelago Sea", "Gulf of Finland W", "Helsinki")},
    "Tallinn": {"Gulf of Finland": _route("Turku", "Archipelago Sea", "Gulf of Finland W", "Tallinn (Muuga)")},
    "Gdansk": {"Gotland Basin": _route("Turku", "Archipelago Sea", "Aland Sea", "Gotland Basin", "Gdansk")},
    "Hamburg": {
        "via Kiel Canal": _route(*_BALTIC_S, "Fehmarn Belt", "Kiel Bay", "Kiel Canal", "Elbe / Hamburg"),
        "via Great Belt + Skagen": _route(*_BALTIC_S, "Fehmarn Belt", "Great Belt (Route T)", "Kattegat", "Skagen",
                                          "Skagerrak", "German Bight", "Elbe / Hamburg")},
    "Rotterdam": {
        "via Kiel Canal": _route(*_BALTIC_S, "Fehmarn Belt", "Kiel Bay", "Kiel Canal", "German Bight", "Rotterdam"),
        "via Great Belt + Skagen": _route(*_BALTIC_S, "Fehmarn Belt", "Great Belt (Route T)", "Kattegat", "Skagen",
                                          "Skagerrak", "Rotterdam"),
        "via The Sound + Skagen": _route(*_BALTIC_S, "The Sound (Drogden)", "Kattegat", "Skagen", "Skagerrak",
                                         "Rotterdam")},
}
ROUTES = {f"{d}: {r}": w for d, rs in ROUTES_BY_DEST.items() for r, w in rs.items()}


def route_profile(hull: Hull, cargo: list, waypoints, scale: float = 1.0, **limits):
    """Per-waypoint density, draught and passage checks at full scale (model x scale). Returns (rows, summary).

    The draught compared with a limit is the DEEPEST point of the hull (static heel and trim included),
    not the mean draught. Canal size limits (length/beam) block a route regardless of load.
    """
    if not waypoints:
        raise ValueError("route has no waypoints")
    if not (isfinite(scale) and scale > 0):
        raise ValueError("scale must be a positive number")
    L_full, B_full = hull.length * scale, hull.overall_beam * scale
    rows, dist = [], 0.0
    for i, (name, lat, lon, s, t, lim_m, src) in enumerate(waypoints):
        if i:
            dist += haversine_km(waypoints[i - 1][1:3], (lat, lon))
        rho = seawater_density(s, t)
        r = analyse(hull, cargo, rho, **limits)
        stable = r.gm > 0 and r.gm_long > 0
        deepest = max(r.draft, hull.depth - r.min_freeboard) if stable else hull.depth   # capsized: whole depth
        full = deepest * scale
        size, blocked = PASSAGE_SIZE.get(name), ""
        if size:
            if L_full > size["max_len"] or B_full > size["max_beam"]:
                blocked = (f"ship {L_full:.0f} x {B_full:.1f} m exceeds the {size['max_len']:.0f} x "
                           f"{size['max_beam']} m limit")
            else:
                lim_m = next(d for l, d in size["draft_by_len"] if L_full <= l)
        over = max(0.0, full - lim_m) if lim_m else 0.0
        rows.append(dict(waypoint=name, lat=lat, lon=lon, salinity=s, temp=t, rho=rho, cum_km=dist,
                         draft_mm=r.draft * 1000, deepest_mm=deepest * 1000, full_draft_m=full,
                         mean_full_draft_m=r.draft * scale, limit_m=lim_m, limit_src=src, blocked=blocked,
                         over_m=over, unverified="not verified" in src,
                         min_freeboard_mm=r.min_freeboard * 1000, ok=not r.warnings))
    worst = max(rows, key=lambda r: r["full_draft_m"])
    blocked = [r for r in rows if r["blocked"]]
    binding = blocked[0] if blocked else max(rows, key=lambda r: r["over_m"])
    lims = [r for r in rows if r["limit_m"] and not r["blocked"]]
    tightest = min(lims, key=lambda r: r["limit_m"] - r["full_draft_m"]) if lims else None
    limit_ok = not blocked and binding["over_m"] == 0
    return rows, dict(distance_km=dist, max_draft_mm=max(r["draft_mm"] for r in rows), worst_point=worst["waypoint"],
                      max_full_draft_m=worst["full_draft_m"],
                      min_freeboard_mm=min(r["min_freeboard_mm"] for r in rows),
                      all_ok=all(r["ok"] for r in rows), limit_ok=limit_ok,
                      blocked=binding["blocked"] if blocked else "",
                      binding_point=None if limit_ok else binding["waypoint"],
                      unverified=[r["waypoint"] for r in rows if r["unverified"]],
                      tightest=(tightest["waypoint"], tightest["limit_m"] - tightest["full_draft_m"]) if tightest else None)


def unload_to_fit(hull: Hull, cargo: list, waypoints, scale: float, **limits):
    """Smallest cargo reduction (g, rounded up; all items scaled together) that makes every passage limit pass.

    Returns None when unloading cannot help (size-blocked, or even the empty ship is too deep).
    Re-checks the result, so the advice is always feasible.
    """
    total = sum(c.mass for c in cargo)
    fits = lambda k: route_profile(hull, [replace(c, mass=c.mass * k) for c in cargo], waypoints, scale,
                                   **limits)[1]["limit_ok"]
    if fits(1.0):
        return 0
    if total <= 0 or not fits(0.0):
        return None
    lo, hi = 0.0, 1.0                     # lo fits, hi does not
    for _ in range(50):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if fits(mid) else (lo, mid)
    grams = ceil((1 - lo) * total * 1000)
    k = max(0.0, 1 - grams / (total * 1000))
    return grams if fits(k) else None


def pick_route(summaries: dict, max_draft_mm: float = None):
    """Shortest route that passes all checks and every known passage limit. Returns name or None."""
    ok = [(s["distance_km"], n) for n, s in summaries.items()
          if s["all_ok"] and s.get("limit_ok", True)
          and (max_draft_mm is None or s["max_draft_mm"] <= max_draft_mm)]
    return min(ok)[1] if ok else None


# ---------- motion ----------
def simulate_roll(roll_period_s, heel_deg, wave_amp_deg=4.0, wave_period_s=None,
                  damping=0.08, initial_deg=10.0, duration_s=20.0, dt=0.05):
    """Damped roll about the static heel + forced response to regular beam waves (linear, documented model)."""
    wn = 2 * pi / roll_period_s
    we = 2 * pi / (wave_period_s or roll_period_s * 1.3)
    amp = wave_amp_deg * magnification(we / wn, damping)
    wd = wn * sqrt(1 - damping**2)
    t, roll = [], []
    n = int(duration_s / dt)
    for i in range(n + 1):
        ti = i * dt
        free = initial_deg * exp(-damping * wn * ti) * cos(wd * ti)
        forced = amp * sin(we * ti)
        t.append(ti)
        roll.append(heel_deg + free + forced)
    return t, roll, amp


def magnification(ratio, damping):
    """Steady-state amplitude factor of a 1-DOF linear oscillator at frequency ratio w/wn (inf at undamped resonance)."""
    d = sqrt((1 - ratio**2) ** 2 + (2 * damping * ratio) ** 2)
    return float("inf") if d == 0 else 1 / d


def wave_number(period_s, depth_m=None):
    """Dispersion w^2 = g k tanh(k h); deep water when depth is None."""
    if not (isfinite(period_s) and period_s > 0):
        raise ValueError("wave period must be a positive number")
    if depth_m is not None and depth_m <= 0:
        depth_m = None
    w = 2 * pi / period_s
    if not depth_m:
        return w * w / G
    f = lambda k: G * k * tanh(k * depth_m) - w * w     # increasing in k
    lo, hi = 0.0, w * w / G + w / sqrt(G * depth_m)
    while f(hi) < 0:
        hi *= 2
    for _ in range(80):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if f(mid) < 0 else (lo, mid)
    return (lo + hi) / 2


def _avg_slope_factor(u):
    """Hull-length average of the wave slope: 3(sin u - u cos u)/u^3 (-> 1 as u -> 0)."""
    return 1.0 if u < 1e-4 else 3 * (sin(u) - u * cos(u)) / u**3


def wave_motions(hull: Hull, res, wave_height_m, wave_period_s, water_depth_m=None,
                 damping=0.1, added_mass=0.5, x_points=()):
    """Linear heave/pitch/roll amplitudes in regular waves (head waves for heave/pitch, beam waves for roll).

    Quasi-static excitation averaged over the hull (long-wave limit: heave -> a, pitch/roll -> wave slope k*a),
    multiplied by the 1-DOF magnification at each natural period. Pressure attenuation to the keel uses
    cosh(k(h-T))/cosh(kh) in finite depth, exp(-kT) in deep water. Assumptions: wall-sided hull, added-mass
    coefficient `added_mass`, k_yy = 0.25 L, stationary model (encounter = wave frequency), quasi-static phases.

    Also returns keel clearance and the largest relative motion (wave surface minus hull) at bow/stern,
    which is what decides green water on deck.
    """
    a = wave_height_m / 2
    k = wave_number(wave_period_s, water_depth_m)
    lam = 2 * pi / k
    w = 2 * pi / wave_period_s
    if water_depth_m:
        att = cosh(k * max(water_depth_m - res.draft, 0)) / cosh(k * water_depth_m)
    else:
        att = exp(-k * res.draft)
    u_l, u_b = k * hull.length / 2, k * hull.overall_beam / 2
    heave_qs = a * att * (1.0 if u_l < 1e-4 else sin(u_l) / u_l)
    pitch_qs = degrees(k * a * att * _avg_slope_factor(u_l))
    roll_qs = degrees(k * a * att * _avg_slope_factor(u_b))
    T_heave = 2 * pi * sqrt(res.draft * (1 + added_mass) / G)
    T_pitch = 2 * pi * 0.25 * hull.length * sqrt((1 + added_mass) / (G * res.gm_long)) if res.gm_long > 0 else float("nan")
    out = dict(wavelength_m=lam, steepness=wave_height_m / lam, T_heave=T_heave, T_pitch=T_pitch,
               T_roll=res.roll_period, heave_qs_m=heave_qs, pitch_qs_deg=pitch_qs, roll_qs_deg=roll_qs,
               keel_clearance_m=(water_depth_m - res.draft) if water_depth_m else float("inf"))
    # Signed values keep the phase (a hull longer than half a wave moves against it); amplitudes are reported >= 0.
    heave_s = heave_qs * magnification(w * T_heave / (2 * pi), damping)
    pitch_s = pitch_qs * magnification(w * T_pitch / (2 * pi), damping) if T_pitch == T_pitch else float("nan")
    roll_s = roll_qs * magnification(w * res.roll_period / (2 * pi), damping) if res.gm > 0 else float("nan")
    out.update(heave_m=abs(heave_s), pitch_deg=abs(pitch_s), roll_deg=abs(roll_s),
               heave_qs_m=abs(heave_qs), pitch_qs_deg=abs(pitch_qs), roll_qs_deg=abs(roll_qs))
    # Relative motion: wave eta = a sin(wt - kx); hull z = heave sin(wt) - x*theta cos(wt) (head waves, x + bow).
    th = radians(pitch_s) if pitch_s == pitch_s else 0.0
    def rel_at(x):
        return max(abs(a * sin(2 * pi * j / 72 - k * x) - (heave_s * sin(2 * pi * j / 72) - x * th * cos(2 * pi * j / 72)))
                   for j in range(72))
    out["rel_motion_m"] = max(rel_at(hull.length / 2), rel_at(-hull.length / 2))
    out["rel_at"] = {x: rel_at(x) for x in x_points}     # e.g. the deck ends, to check where cargo sits
    return out


def _noise_sigma(x):
    """Sensor-noise estimate from second differences (robust to the smooth signal): median|d2| / (0.6745*sqrt(6))."""
    d2 = sorted(abs(x[i + 1] - 2 * x[i] + x[i - 1]) for i in range(1, len(x) - 1))
    return d2[len(d2) // 2] / (0.6745 * sqrt(6)) if d2 else 0.0


def roll_decay(t, x):
    """Free-decay analysis without SciPy. Returns dict(Td, Tn, delta, zeta, n_peaks) or None.

    None means "not a usable free-decay record": too short, non-increasing or non-finite time, fewer than
    3 cycles above the noise floor, or a growing (not decaying) oscillation.
    """
    if len(t) != len(x) or len(t) < 10:
        return None
    if not all(isfinite(v) for v in list(t) + list(x)) or any(b <= a for a, b in zip(t, t[1:])):
        return None
    first = _decay_fit(t, x)
    if first is None:
        return None
    # Sensor noise biases each cycle's max upward (most at small peaks -> damping underestimated).
    # Second pass on a centred moving average ~1/10 of the period removes most of it.
    dt = (t[-1] - t[0]) / (len(t) - 1)
    half = int(0.05 * first["Td"] / dt)
    if half < 1:
        return first
    sm = [sum(x[max(0, i - half):i + half + 1]) / len(x[max(0, i - half):i + half + 1]) for i in range(len(x))]
    # The smoothed record's own second differences understate the noise; carry the raw estimate over.
    return _decay_fit(t, sm, _noise_sigma(x) / sqrt(2 * half + 1)) or first


def _decay_fit(t, x, sigma=None):
    mean = sum(x) / len(x)
    y = [v - mean for v in x]
    peak = max(abs(v) for v in y)
    if peak == 0:
        return None
    sigma = _noise_sigma(y) if sigma is None else sigma
    h = max(0.01 * peak, 3 * sigma)          # hysteresis tied to the noise floor, not a fixed 10 %
    floor = 5 * sigma                        # a cycle peak must stand clearly above the noise
    ups, armed = [], False
    for i in range(1, len(y)):
        if y[i] < -h:
            armed = True
        elif armed and y[i] > h:
            j = i
            while j > 0 and y[j - 1] > 0:      # walk back to the actual crossing
                j -= 1
            ups.append(j)
            armed = False
    if len(ups) < 4:
        return None
    peaks = []
    for a, b in zip(ups, ups[1:]):           # keep the leading run of cycles above the noise; stop at the first
        p = max(y[a:b])                      # one that sinks into it (later "cycles" are noise, not decay)
        if p <= max(floor, 0):
            break
        peaks.append(p)
    if len(peaks) < 3:
        return None
    ups = ups[:len(peaks) + 1]
    n = len(peaks)
    xs, ys = list(range(n)), [log(p) for p in peaks]
    mx, my = sum(xs) / n, sum(ys) / n
    delta = -sum((a - mx) * (b - my) for a, b in zip(xs, ys)) / sum((a - mx) ** 2 for a in xs)
    if delta <= 0:                           # growing or steady oscillation is not a free decay
        return None
    Td = (t[ups[-1]] - t[ups[0]]) / (len(ups) - 1)
    zeta = delta / sqrt(4 * pi**2 + delta**2)
    return dict(Td=Td, Tn=Td * sqrt(1 - zeta**2), delta=delta, zeta=zeta, n_peaks=n)


def k_from_period(Tn, gm):
    """Effective roll radius of gyration from a measured natural period: k = Tn*sqrt(g*GM)/(2*pi).

    GM must be the GM of the condition in which the decay was recorded (same load and water).
    """
    return Tn * sqrt(G * gm) / (2 * pi)


def inclining_gm(weights_kg, offsets_m, angles_deg, displacement_kg):
    """GM from an inclining test: least-squares line tan(theta) = tan(theta0) + slope * M, M = w*d (kg*m).

    The intercept absorbs an initial list (theta0), so a model that floats slightly heeled does not bias GM.
    GM = 1 / (displacement * slope). Returns (GM_m, r2, theta0_deg) or None (fewer than 3 points,
    no spread in moment, or non-positive slope).
    """
    pts = [(w * d, tan(radians(a))) for w, d, a in zip(weights_kg, offsets_m, angles_deg)
           if all(isfinite(v) for v in (w, d, a))]
    if len(pts) < 3 or displacement_kg <= 0:
        return None
    n = len(pts)
    mx, my = sum(m for m, _ in pts) / n, sum(s for _, s in pts) / n
    sxx = sum((m - mx) ** 2 for m, _ in pts)
    if sxx == 0:
        return None
    slope = sum((m - mx) * (s - my) for m, s in pts) / sxx
    if slope <= 0:
        return None
    c = my - slope * mx
    ss_res = sum((s - c - slope * m) ** 2 for m, s in pts)
    ss_tot = sum((s - my) ** 2 for _, s in pts)
    return 1 / (displacement_kg * slope), (1 - ss_res / ss_tot) if ss_tot else 1.0, degrees(atan(c))


def roll_stats(t, roll):
    """Amplitude and mean period from zero-crossings about the mean (no SciPy needed)."""
    mean = sum(roll) / len(roll)
    ups = [t[i] for i in range(1, len(roll)) if roll[i - 1] - mean < 0 <= roll[i] - mean]
    period = (ups[-1] - ups[0]) / (len(ups) - 1) if len(ups) > 1 else float("nan")
    return (max(roll) - min(roll)) / 2, period


def drag_force(rho, cd, area_m2, speed_ms):
    """First-pass drag F = 0.5*rho*Cd*A*v^2 (N)."""
    return 0.5 * rho * cd * area_m2 * speed_ms**2


def load_v3_hull(config: str, mass: float, kg_hull: float = 0.0, k_roll: float = 0.0, path=None) -> Hull:
    """The printed v3 wave-piercer as a table hull. config: a key of data/v3_hydrostatics.json["configs"]."""
    import json
    from pathlib import Path
    data = json.loads(Path(path or Path(__file__).parent / "data" / "v3_hydrostatics.json").read_text())
    g, cfg = data["geometry"], data["configs"][config]
    n, gap = cfg["n_hulls"], cfg["gap_m"]
    overall = n * g["demihull_beam_m"] + (n - 1) * gap
    return Hull(f"v3 {config}", g["length_m"], g["demihull_beam_m"], g["depth_m"], n, gap, mass, kg_hull, k_roll,
                table=tuple(tuple(r) for r in cfg["rows"]),
                # empty-ship LCG ~ centroid of the solid hull = LCB at full depth (fine bow puts both aft)
                lcg_hull=cfg["rows"][-1][3],
                deck_h=g["deck_top_m"] if n == 2 else g["depth_m"],
                deck_len=g["deck_length_m"] if n == 2 else 0.0,
                deck_beam=overall + 2 * g["flange_m"] if n == 2 else 0.0,
                deck_xc=g["deck_centre_x_from_midship_m"] if n == 2 else 0.0)


def v3_configs(path=None):
    import json
    from pathlib import Path
    return list(json.loads(Path(path or Path(__file__).parent / "data" / "v3_hydrostatics.json").read_text())["configs"])
