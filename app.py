"""Ballast-Free Ship Operations - Arova Engineering Challenge 2026 (ICT track).
Run: streamlit run app.py
"""
import json
import math
import random

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from hydro import (Hull, Cargo, analyse, seawater_density, WATER_PRESETS, ROUTES_BY_DEST, route_profile,
                   suggest_rebalance, simulate_roll, roll_stats, drag_force, load_limit, check_suggestion,
                   pick_route, wave_motions, roll_decay, k_from_period, inclining_gm, unload_to_fit)


def set_state(key, value):
    """Button callback: write a measured value into a sidebar input (runs before the widgets are rebuilt)."""
    st.session_state[key] = value

st.set_page_config(page_title="Ballast-Free Ship Ops", layout="wide")
st.title("Ballast-Free Ship Operations")
st.caption("Cargo & stability, hull comparison, route planning and roll monitoring for a ballast-free model vessel. "
           "Units: kg, m, s, N, kg/m³, degrees (inputs in g / mm for convenience). "
           "Labels: **calculated** = from hydro.py, **simulated** = model output, **measured** = from a physical test.")

# ---------------- sidebar: hulls, water, limits ----------------
with st.sidebar:
    st.header("Hull versions")

    def hull_inputs(key, name, n, L, B, D, gap, mass):
        with st.expander(name, expanded=key == "rev"):
            n = st.radio("Type", [1, 2], index=n - 1, horizontal=True, key=key + "n",
                         format_func=lambda v: "Monohull" if v == 1 else "Catamaran")
            L = st.number_input("Pontoon length (mm)", 50, 250, L, key=key + "L")
            B = st.number_input("Pontoon beam (mm)", 10, 250, B, key=key + "B")
            D = st.number_input("Hull depth (mm)", 10, 150, D, key=key + "D")
            gap = st.number_input("Gap between pontoons (mm)", 0, 200, gap, key=key + "g", disabled=n == 1)
            mass = st.number_input("Empty model mass (g)", 10, 2000, mass, key=key + "m")
            kg = st.number_input("Empty-hull VCG above keel (mm, 0 = 45% depth estimate)", 0.0, 300.0, 0.0, 0.5,
                                 key=key + "kg", help="Use the inclining-test result (tab 5).")
            kr = st.number_input("Roll radius of gyration k (mm, 0 = 0.4 x beam estimate)", 0.0, 400.0, 0.0, 0.5,
                                 key=key + "kr", help="Use the roll-decay result (tab 4, CSV).")
            st.caption(f"VCG: **{'measured' if kg else 'estimated'}** · k: **{'measured' if kr else 'estimated'}**")
            ov = n * B + (n - 1) * gap
            if max(L, ov, D) > 250:
                st.error("Exceeds the 250 x 250 x 250 mm print limit.")
        return Hull(name, L / 1000, B / 1000, D / 1000, n, gap / 1000 if n == 2 else 0, mass / 1000, kg / 1000,
                    kr / 1000)

    base = hull_inputs("base", "Baseline (v1)", 1, 235, 104, 55, 0, 250)
    rev = hull_inputs("rev", "Revised (v2)", 2, 235, 52, 55, 56, 250)

    st.header("Water")
    preset = st.selectbox("Condition", list(WATER_PRESETS) + ["Custom"])
    s0, t0 = WATER_PRESETS.get(preset, (6.0, 8.0))
    sal = st.number_input("Salinity (PSU)", 0.0, 42.0, s0, disabled=preset != "Custom")
    temp = st.number_input("Temperature (°C)", -2.0, 35.0, t0, disabled=preset != "Custom")
    rho = seawater_density(sal, temp)
    st.metric("Density (calculated, EOS-80)", f"{rho:.2f} kg/m³")

    st.header("Safety limits")
    lim = dict(min_freeboard_m=st.number_input("Min freeboard (mm)", 0, 50, 10) / 1000,
               max_heel_deg=st.number_input("Max heel (°)", 1.0, 30.0, 5.0),
               min_gm_m=st.number_input("Min GM (mm)", 0, 50, 5) / 1000)

# ---------------- cargo table ----------------
DEFAULT_CARGO = pd.DataFrame([
    dict(name="Container A", mass_g=150, x_mm=40, y_mm=0, len_mm=50, wid_mm=40, hgt_mm=25),
    dict(name="Container B", mass_g=100, x_mm=-40, y_mm=25, len_mm=50, wid_mm=40, hgt_mm=25),
    dict(name="Container C", mass_g=50, x_mm=-40, y_mm=-20, len_mm=40, wid_mm=30, hgt_mm=20),
])
if "cargo" not in st.session_state:
    st.session_state.cargo = DEFAULT_CARGO


def to_cargo(df):
    out = []
    for r in df.dropna(subset=["mass_g"]).itertuples():
        out.append(Cargo(str(r.name), r.mass_g / 1000, r.x_mm / 1000, r.y_mm / 1000,
                         r.len_mm / 1000, r.wid_mm / 1000, r.hgt_mm / 1000))
    return out


def fmt(r):
    return {"Total mass (g)": r.total_mass * 1000, "Draft (mm)": r.draft * 1000,
            "Freeboard (mm)": r.freeboard * 1000, "Lowest freeboard (mm)": r.min_freeboard * 1000,
            "GM (mm)": r.gm * 1000, "Heel (°)": r.heel_deg, "Trim (°)": r.trim_deg,
            "Roll period (s)": r.roll_period, "Reserve buoyancy (g)": r.reserve_buoyancy_kg * 1000,
            "Warnings": len(r.warnings)}


def deck_plot(hull, cargo, res, title):
    fig = go.Figure()
    half_l = hull.length / 2 * 1000
    for k in range(hull.n_pontoons):
        yc = (k - (hull.n_pontoons - 1) / 2) * (hull.beam + hull.gap) * 1000
        fig.add_shape(type="rect", x0=-half_l, x1=half_l, y0=yc - hull.beam * 500, y1=yc + hull.beam * 500,
                      line=dict(color="#4a7bd0"), fillcolor="rgba(74,123,208,0.15)")
    for c in cargo:
        fig.add_shape(type="rect", x0=(c.x - c.lx / 2) * 1000, x1=(c.x + c.lx / 2) * 1000,
                      y0=(c.y - c.ly / 2) * 1000, y1=(c.y + c.ly / 2) * 1000,
                      line=dict(color="#d08a2e"), fillcolor="rgba(208,138,46,0.45)")
        fig.add_annotation(x=c.x * 1000, y=c.y * 1000, text=f"{c.name}<br>{c.mass*1000:.0f} g", showarrow=False,
                           font=dict(size=10))
    fig.add_trace(go.Scatter(x=[res.xcg * 1000], y=[res.ycg * 1000], mode="markers+text", text=["CG"],
                             textposition="top center", marker=dict(size=12, color="red", symbol="x"), name="CG"))
    fig.update_layout(title=title, height=330, showlegend=False, margin=dict(l=10, r=10, t=40, b=10),
                      xaxis_title="x (mm, + bow)", yaxis_title="y (mm, + starboard)")
    fig.update_yaxes(scaleanchor="x", autorange="reversed")
    return fig


def section_plot(hull, res, title):
    """Midship section, heeled by the calculated angle, with the waterline."""
    ang = math.radians(0 if res.heel_deg != res.heel_deg else res.heel_deg)
    fig = go.Figure()
    for k in range(hull.n_pontoons):
        yc = (k - (hull.n_pontoons - 1) / 2) * (hull.beam + hull.gap)
        pts = [(yc - hull.beam / 2, 0), (yc + hull.beam / 2, 0), (yc + hull.beam / 2, hull.depth),
               (yc - hull.beam / 2, hull.depth), (yc - hull.beam / 2, 0)]
        rot = [(y * math.cos(ang) - (z - res.draft) * math.sin(ang), y * math.sin(ang) + (z - res.draft) * math.cos(ang))
               for y, z in pts]
        fig.add_trace(go.Scatter(x=[p[0] * 1000 for p in rot], y=[p[1] * 1000 for p in rot], fill="toself",
                                 line=dict(color="#4a7bd0"), showlegend=False))
    w = hull.overall_beam * 700
    fig.add_trace(go.Scatter(x=[-w, w], y=[0, 0], line=dict(color="#2a9fd6", dash="dash"), name="waterline"))
    fig.update_layout(title=title, height=260, margin=dict(l=10, r=10, t=40, b=10), showlegend=False,
                      xaxis_title="y (mm)", yaxis_title="z from waterline (mm)")
    fig.update_yaxes(scaleanchor="x")
    return fig


def show_warnings(res):
    if res.warnings:
        for w in res.warnings:
            (st.error if w.startswith(("SINKS", "UNSTABLE")) else st.warning)(w)
    else:
        st.success("All checks passed for the current load and water condition.")


tab_cargo, tab_cmp, tab_route, tab_dash, tab_val = st.tabs(
    ["1 · Cargo & stability", "2 · Hull comparison", "3 · Route planner", "4 · Ship dashboard", "5 · Validation"])

# ---------------- 1. cargo ----------------
with tab_cargo:
    st.subheader("Cargo layout (non-stacked boxes on deck)")
    st.caption("x from midship (+ bow), y from centreline (+ starboard). Boxes sit on the deck.")
    edited = st.data_editor(st.session_state.cargo, num_rows="dynamic", width="stretch", key="cargo_editor")
    cargo = to_cargo(edited)
    hull_choice = st.radio("Analyse hull", ["Revised (v2)", "Baseline (v1)"], horizontal=True)
    hull = rev if hull_choice.startswith("Revised") else base
    res = analyse(hull, cargo, rho, **lim)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Draft", f"{res.draft*1000:.1f} mm")
    c2.metric("Freeboard (lowest)", f"{res.min_freeboard*1000:.1f} mm")
    c3.metric("GM", f"{res.gm*1000:.1f} mm")
    c4.metric("Heel", "capsize" if res.heel_deg != res.heel_deg else f"{res.heel_deg:.1f}°")
    max_cargo, why = load_limit(hull, cargo, rho, **lim)
    cur_cargo = sum(c.mass for c in cargo)
    if max_cargo is None:   # invalid layout: no capacity claim
        c5.metric("Predicted load limit", "n/a")
        st.caption(f"Load limit: **{why}**")
    else:
        c5.metric("Predicted load limit", f"{max_cargo*1000:.0f} g",
                  f"{(max_cargo - cur_cargo)*1000:+.0f} g margin", delta_color="normal")
    if cargo and max_cargo is not None:
        st.caption(f"Load limit (calculated): cargo scaled up in the current positions and mass ratios until the first "
                   f"limit is hit → **{why}**  ·  Sinking reserve: {res.reserve_buoyancy_kg*1000:.0f} g.")
    show_warnings(res)

    sug = suggest_rebalance(cargo, res.total_mass, res.ycg, res.xcg)
    if sug and (abs(res.ycg) > 1e-4 or abs(res.xcg) > 1e-4):
        name, ny, nx = sug
        nx, ny = round(nx * 1000) / 1000, round(ny * 1000) / 1000
        ok, reason, after = check_suggestion(hull, cargo, rho, name, nx, ny, **lim)
        if ok:
            st.info(f"Correction: move **{name}** to x = {nx*1000:.0f} mm, y = {ny*1000:.0f} mm → heel "
                    f"{res.heel_deg:.1f}° → {after.heel_deg:.1f}°, lowest freeboard "
                    f"{res.min_freeboard*1000:.1f} → {after.min_freeboard*1000:.1f} mm.")
            if st.button("Apply correction"):
                df = edited.copy()
                i = df.index[df["name"] == name][0]
                df.loc[i, ["x_mm", "y_mm"]] = [nx * 1000, ny * 1000]
                st.session_state.cargo = df.reset_index(drop=True)
                st.session_state.pop("cargo_editor", None)   # drop stale editor deltas so the new table shows
                st.rerun()
        else:
            st.warning(f"Moving **{name}** alone cannot re-centre the load: {reason} "
                       "Try moving lighter items to the opposite side.")

    a, b = st.columns([3, 2])
    a.plotly_chart(deck_plot(hull, cargo, res, f"Deck plan - {hull.name}"))
    b.plotly_chart(section_plot(hull, res, "Midship section at calculated heel"))
    with st.expander("How it is calculated"):
        st.markdown(r"""
- CG: $x_{CG}=\sum m_i x_i/\sum m_i$ (same for y, z). Cargo VCG = deck height + box height / 2.
- Displacement $V = M/\rho$; wall-sided pontoons → draft $T = V/A_{wp}$; $KB = T/2$.
- $BM = I_T/V$, catamaran $I_T = 2\,(L b^3/12 + L b\,d^2)$, $d$ = centreline → pontoon centre.
- $GM = KB + BM - KG$; small-angle heel $\phi = \arctan(y_{CG}/GM)$; trim uses $GM_L$.
- Lowest freeboard = freeboard − (half beam)·tan(heel) − (half length)·tan(trim).
- Roll period $T_\phi = 2\pi k/\sqrt{g\,GM}$ with $k \approx 0.4\,B$ (first estimate, to be checked by test).
- Limits: small-angle theory; warning when the deck edge is immersed.""")

# ---------------- 2. comparison ----------------
with tab_cmp:
    st.subheader("Baseline vs revised hull - same cargo, same water")
    rb, rr = analyse(base, cargo, rho, **lim), analyse(rev, cargo, rho, **lim)
    lb, lr = load_limit(base, cargo, rho, **lim), load_limit(rev, cargo, rho, **lim)
    g = lambda l: float("nan") if l[0] is None else l[0] * 1000
    table = pd.DataFrame({base.name: {"Predicted load limit (g)": g(lb), **fmt(rb)},
                          rev.name: {"Predicted load limit (g)": g(lr), **fmt(rr)}})
    key_rows = ["Predicted load limit (g)", "Draft (mm)", "GM (mm)", "Lowest freeboard (mm)", "Heel (°)"]
    st.dataframe(table.style.format("{:.2f}", na_rep="n/a")
                 .set_properties(subset=pd.IndexSlice[key_rows, :], **{"font-weight": "bold"}),
                 width="stretch")
    if lb[0] is None or lr[0] is None:
        st.warning(f"No capacity verdict: {lb[1] if lb[0] is None else lr[1]}")
    else:
        gain = lr[0] - lb[0]
        pct = f"{gain / lb[0] * 100:+.0f}%" if lb[0] > 0 else "baseline carries nothing"
        st.markdown(f"**Verdict (calculated):** {rev.name} carries **{gain*1000:+.0f} g** ({pct}) more cargo "
                    f"than {base.name} in the same positions. Limits: v1 → *{lb[1]}*  ·  v2 → *{lr[1]}*")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**{base.name}**"); show_warnings(rb)
    with c2:
        st.markdown(f"**{rev.name}**"); show_warnings(rr)

    st.markdown("#### Stability vs load (sweep 0 → 400 g at the current cargo centre)")
    cx = sum(c.mass * c.x for c in cargo) / max(sum(c.mass for c in cargo), 1e-9)
    cy = sum(c.mass * c.y for c in cargo) / max(sum(c.mass for c in cargo), 1e-9)
    sweep = []
    for g in range(0, 401, 25):
        for h in (base, rev):
            r = analyse(h, [Cargo("load", g / 1000, cx, cy, 0.05, 0.04, 0.025)] if g else [], rho, **lim)
            sweep.append(dict(load_g=g, hull=h.name, gm_mm=r.gm * 1000, draft_mm=r.draft * 1000,
                              heel=r.heel_deg, min_fb_mm=r.min_freeboard * 1000))
    sw = pd.DataFrame(sweep)
    c1, c2 = st.columns(2)
    f1, f2 = go.Figure(), go.Figure()
    for h in (base.name, rev.name):
        d = sw[sw.hull == h]
        f1.add_trace(go.Scatter(x=d.load_g, y=d.gm_mm, name=h))
        f2.add_trace(go.Scatter(x=d.load_g, y=d.min_fb_mm, name=h))
    f1.add_hline(y=lim["min_gm_m"] * 1000, line_dash="dot", annotation_text="GM limit")
    f2.add_hline(y=lim["min_freeboard_m"] * 1000, line_dash="dot", annotation_text="freeboard limit")
    f1.update_layout(title="GM (mm) - calculated", xaxis_title="load (g)", height=320)
    f2.update_layout(title="Lowest freeboard (mm) - calculated", xaxis_title="load (g)", height=320)
    c1.plotly_chart(f1)
    c2.plotly_chart(f2)

    st.markdown("#### Drag at matched speed and load (first-pass)")
    c1, c2 = st.columns(2)
    v = c1.slider("Speed (m/s)", 0.05, 1.0, 0.3)
    cd = c2.number_input("Drag coefficient Cd (assumed, blunt box ≈ 1.0)", 0.1, 2.0, 1.0)
    drag = []
    for h, r in ((base, rb), (rev, rr)):
        area = h.n_pontoons * h.beam * r.draft                   # frontal submerged area
        drag.append({"hull": h.name, "frontal area (cm²)": area * 1e4, "drag F (N)": drag_force(rho, cd, area, v)})
    st.dataframe(pd.DataFrame(drag), width="stretch")
    st.caption("F = 0.5·ρ·Cd·A·v². Cd is assumed, not measured - state this in the presentation.")

    export = {h.name: {"hull": h.__dict__, "result": {k: v for k, v in r.__dict__.items()}}
              for h, r in ((base, rb), (rev, rr))}
    export["conditions"] = {"salinity_psu": sal, "temp_c": temp, "rho": rho,
                            "cargo": [c.__dict__ for c in cargo], "limits": lim}
    st.download_button("Export both versions (JSON)", json.dumps(export, indent=2, default=str),
                       "hull_comparison.json", "application/json")

# ---------------- 3. route ----------------
with tab_route:
    st.subheader("Route planner - density-aware draught vs real passage limits")
    st.caption("Salinity/temperature at waypoints are **typical November surface values (estimates)**; the Kiel Canal "
               "salinity is a **placeholder**. Passage limits are real full-scale values (source in the map tooltip). "
               "Full-scale draught = model draught × N.")
    c1, c2, c3 = st.columns(3)
    dests = list(ROUTES_BY_DEST)
    dest = c1.selectbox("Destination (from Turku)", dests, index=dests.index("Rotterdam"))
    hull_r = rev if c2.radio("Hull", ["Revised (v2)", "Baseline (v1)"], horizontal=True, key="rh").startswith("Rev") else base
    scale = c3.number_input("Model scale 1:N", 1, 2000, 400,
                            help="1:400 turns a ~22 mm model draught into ~9 m - a typical Baltic cargo ship.")
    routes = ROUTES_BY_DEST[dest]
    profiles = {n: route_profile(hull_r, cargo, w, scale=scale, **lim) for n, w in routes.items()}
    summ = {n: s for n, (_, s) in profiles.items()}
    best = pick_route(summ)

    st.caption(f"Full-scale ship at 1:{scale}: {hull_r.length * scale:.0f} m long × {hull_r.overall_beam * scale:.1f} m "
               "wide. Draught checks use the deepest point of the hull (static heel and trim included).")
    if best:
        s = summ[best]
        tight = f"; tightest passage {s['tightest'][0]} with {s['tightest'][1]:.2f} m to spare" if s["tightest"] else ""
        unv = (f" **Not verified:** permitted draught at {', '.join(s['unverified'])} - check before sailing."
               if s["unverified"] else "")
        st.success(f"Recommended: **Turku → {dest} {best}** - shortest route that passes every stability check and "
                   f"every known passage limit ({s['distance_km']:.0f} km, deepest full-scale draught "
                   f"{s['max_full_draft_m']:.2f} m{tight}).{unv}")
    else:
        st.error("No route passes every check and known passage limit with this load. See the advice below.")
    for n, s in summ.items():
        if not s["all_ok"]:
            st.warning(f"{n}: the ship fails a stability check with this cargo (tab 1).")
        elif s["blocked"]:
            st.warning(f"{n}: blocked at **{s['binding_point']}** - {s['blocked']}. Unloading cannot fix this; "
                       "use another route or a smaller scale.")
        elif not s["limit_ok"]:
            g = unload_to_fit(hull_r, cargo, routes[n], scale, **lim)
            if g is None:
                st.warning(f"{n}: too deep at **{s['binding_point']}** even when empty.")
            else:
                st.warning(f"{n}: too deep at **{s['binding_point']}** → unload **{g} g** of model cargo "
                           f"(all items reduced together; ≈ {g / 1000 * scale**3 / 1000:,.0f} t at full scale) "
                           "to use this route. Checked: the reduced load passes every limit.")

    summary = pd.DataFrame([{
        "route": n, "distance (km)": round(s["distance_km"]), "max model draught (mm)": round(s["max_draft_mm"], 2),
        "deepest full-scale draught (m)": round(s["max_full_draft_m"], 2), "deepest at": s["worst_point"],
        "tightest passage": s["tightest"][0] if s["tightest"] else "-",
        "margin there (m)": round(s["tightest"][1], 2) if s["tightest"] else None,
        "stability OK": s["all_ok"], "limits OK": s["limit_ok"]} for n, s in summ.items()])
    st.dataframe(summary, width="stretch", hide_index=True)

    layer = st.radio("Map colour", ["Water density (kg/m³)", "Salinity (PSU)"], horizontal=True)
    key = "rho" if layer.startswith("Water") else "salinity"
    all_rows = [r for rows, _ in profiles.values() for r in rows]
    cmin, cmax = min(r[key] for r in all_rows), max(r[key] for r in all_rows)
    fig = go.Figure()
    colors = ["#d0572e", "#2e8bd0", "#3aa35b"]
    for i, ((name, (rows, _)), col) in enumerate(zip(profiles.items(), colors)):
        fig.add_trace(go.Scattergeo(lat=[r["lat"] for r in rows], lon=[r["lon"] for r in rows], mode="lines",
                                    name=name, line=dict(width=5 if name == best else 2, color=col), hoverinfo="skip"))
        fig.add_trace(go.Scattergeo(
            lat=[r["lat"] for r in rows], lon=[r["lon"] for r in rows], mode="markers", showlegend=False,
            marker=dict(size=[16 if r["limit_m"] or r["blocked"] else 11 for r in rows],
                        symbol=["x" if r["blocked"] else "diamond" if r["limit_m"] else "circle" for r in rows],
                        color=[r[key] for r in rows], colorscale="Viridis", cmin=cmin, cmax=cmax,
                        line=dict(width=1, color=col), showscale=i == 0,
                        colorbar=dict(title=layer.split(" (")[0], x=1.0)),
            text=[f"{r['waypoint']}<br>S={r['salinity']} PSU, T={r['temp']} °C (estimate)<br>ρ={r['rho']:.1f} kg/m³"
                  f"<br>model draught {r['draft_mm']:.2f} mm (deepest {r['deepest_mm']:.2f} mm)"
                  f"<br>full scale: mean {r['mean_full_draft_m']:.2f} m, deepest {r['full_draft_m']:.2f} m"
                  + (f"<br><b>limit {r['limit_m']} m</b>" if r["limit_m"] else "")
                  + (f"<br><b>BLOCKED: {r['blocked']}</b>" if r["blocked"] else "")
                  + (f"<br>{r['limit_src']}" if r["limit_src"] else "")
                  for r in rows], hoverinfo="text"))
    fig.update_geos(fitbounds="locations", projection_type="mercator", showland=True, showcountries=True,
                    landcolor="#e8e4d8", showocean=True, oceancolor="#cfe3f3", resolution=50)
    fig.update_layout(height=500, margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h"))
    st.plotly_chart(fig)
    st.caption("◆ = passage or port with a draught limit · ✕ = blocked by ship size. "
               "Lines join waypoints (illustrative, not navigational tracks).")

    prof = go.Figure()
    for (name, (rows, _)), col in zip(profiles.items(), colors):
        prof.add_trace(go.Scatter(x=[r["cum_km"] for r in rows], y=[r["full_draft_m"] for r in rows], name=name,
                                  mode="lines+markers", line=dict(color=col), text=[r["waypoint"] for r in rows]))
        lr_ = [r for r in rows if r["limit_m"]]
        prof.add_trace(go.Scatter(x=[r["cum_km"] for r in lr_], y=[r["limit_m"] for r in lr_], mode="markers",
                                  marker=dict(symbol="line-ew-open", size=26, color=col, line=dict(width=3)),
                                  name=f"limit ({name})", text=[r["waypoint"] for r in lr_]))
    prof.update_layout(title="Full-scale draught along route vs passage limits", xaxis_title="distance (km)",
                       yaxis_title="draught (m)", height=340)
    st.plotly_chart(prof)
    rho_lo, rho_hi = min(r["rho"] for r in all_rows), max(r["rho"] for r in all_rows)
    st.caption(f"Draught is inversely proportional to density (T = M / (ρ·A_wp)): the {rho_lo:.1f} → {rho_hi:.1f} "
               f"kg/m³ range here changes draught by {(rho_hi / rho_lo - 1) * 100:.1f}% - at 9.5 m that is "
               f"{9.5 * (rho_hi / rho_lo - 1) * 100:.0f} cm, enough to fail the Kiel Canal limit.")

# ---------------- 4. dashboard ----------------
KG_MAX_MM, KR_MAX_MM = 300.0, 400.0   # must match the sidebar inputs' max_value


def offer_value(col, label, key, value_mm, max_mm):
    """Button that writes a measured value into a sidebar input - only if the input can hold it."""
    if 0 < value_mm <= max_mm:
        col.button(label, on_click=set_state, args=(key, round(value_mm, 1)))
    else:
        col.error(f"{value_mm:.1f} mm is outside the plausible range (0–{max_mm:.0f} mm) - check the test data.")


def read_motion_csv(up):
    """Parse and validate an uploaded motion CSV. Returns (df, error_message)."""
    try:
        df = pd.read_csv(up)
    except Exception as e:  # empty file, bad encoding, ragged rows ...
        return None, f"Could not read the CSV ({type(e).__name__}). Expected columns t, roll, pitch."
    df.columns = [str(c).strip().lower() for c in df.columns]
    if not {"t", "roll", "pitch"} <= set(df.columns):
        return None, "CSV must have columns t, roll, pitch (s, °, °); heave (mm) is optional."
    cols = ["t", "roll", "pitch"] + (["heave"] if "heave" in df.columns else [])
    num = df[cols].apply(pd.to_numeric, errors="coerce")
    bad = int((~np.isfinite(num.to_numpy(dtype=float))).any(axis=1).sum())
    if bad:
        return None, f"{bad} row(s) contain non-numeric or missing values - clean the file and upload again."
    if len(num) < 10:
        return None, "CSV needs at least 10 rows."
    if not (num.t.diff().dropna() > 0).all():
        return None, "Time column t must be strictly increasing (no repeated or reversed timestamps)."
    return num, None


with tab_dash:
    st.subheader("Ship dashboard - roll / pitch / heave monitoring")
    hkey = "rev" if st.radio("Hull", ["Revised (v2)", "Baseline (v1)"], horizontal=True, key="dh").startswith("Rev") else "base"
    hull_d = rev if hkey == "rev" else base
    res_d = analyse(hull_d, cargo, rho, **lim)
    lim_d, _ = load_limit(hull_d, cargo, rho, **lim)
    load_g = sum(c.mass for c in cargo) * 1000
    c1, c2, c3 = st.columns(3)
    c1.metric("Hull", hull_d.name)
    if lim_d is None:
        c2.metric("Cargo on board", f"{load_g:.0f} g")
        c3.error("Load limit n/a: invalid cargo layout (tab 1).")
    else:
        c2.metric("Cargo on board", f"{load_g:.0f} g", f"{lim_d*1000 - load_g:+.0f} g to limit")
        c3.progress(min(load_g / (lim_d * 1000), 1.0) if lim_d > 0 else 1.0,
                    text=f"Load {load_g / (lim_d * 1000) * 100 if lim_d > 0 else 100:.0f}% of predicted limit")
    src = st.radio("Data source", ["Simulated (regular waves, linear model)", "Upload CSV (MPU6050: t, roll, pitch)"],
                   horizontal=True)
    t = None        # stays None when there is nothing to plot; st.stop() would also hide the next tab
    heave = None
    problems = []   # every failed or uncomputable check; "within limits" only when this stays empty
    rel_motion = None
    if src.startswith("Sim"):
        c1, c2, c3, c4, c5 = st.columns(5)
        H = c1.slider("Wave height H (mm)", 0, 40, 10)
        Tw = c2.slider("Wave period (s)", 0.3, 3.0, 0.8)
        hw = c3.number_input("Tank water depth (mm, 0 = deep)", 0, 2000, 300)
        zeta = c4.slider("Damping ratio ζ", 0.02, 0.4, 0.1)
        push = c5.checkbox("Push test: start with a 10° roll", help="Hand-rocked model, like the tank demo.")
        if res_d.gm <= 0 or res_d.gm_long <= 0:
            st.error(f"{hull_d.name} is unstable with this load - nothing to simulate.")
        elif hw and hw / 1000 <= res_d.draft:
            st.error(f"Water depth {hw} mm is not more than the draught {res_d.draft*1000:.1f} mm: the hull sits on "
                     "the tank bottom. Increase the depth or reduce the load.")
        else:
            m = wave_motions(hull_d, res_d, H / 1000, Tw, hw / 1000 or None, zeta)
            label = "simulated"
            rel_motion = m["rel_motion_m"]
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Wavelength", f"{m['wavelength_m']*100:.0f} cm", f"H/λ = {m['steepness']:.3f}", delta_color="off")
            c2.metric("Heave amplitude", f"{m['heave_m']*1000:.1f} mm", f"Tn {m['T_heave']:.2f} s", delta_color="off")
            c3.metric("Pitch amplitude", f"{m['pitch_deg']:.1f}°", f"Tn {m['T_pitch']:.2f} s", delta_color="off")
            c4.metric("Roll amplitude (beam waves)", f"{m['roll_deg']:.1f}°", f"Tn {m['T_roll']:.2f} s", delta_color="off")
            if m["steepness"] > 1 / 7:
                problems.append("H/λ > 1/7: these waves break - linear results are not valid.")
            elif m["steepness"] > 0.05:
                st.warning("Steep waves (H/λ > 0.05): linear theory is approximate here.")
            if hw and m["keel_clearance_m"] <= m["heave_m"] + 0.002:
                problems.append(f"Keel clearance {m['keel_clearance_m']*1000:.1f} mm ≤ heave {m['heave_m']*1000:.1f} mm "
                                "+ 2 mm: the hull will touch the tank bottom.")
            elif hw and hw / 1000 < 3 * res_d.draft:
                st.warning("Shallow water (depth < 3 × draught): bottom effects are not modelled; results approximate.")
            t, roll, _ = simulate_roll(res_d.roll_period, res_d.heel_deg, m["roll_qs_deg"], Tw, zeta,
                                       initial_deg=10.0 if push else 0.0)
            w = 2 * math.pi / Tw
            pitch = [m["pitch_deg"] * math.sin(w * ti + math.pi / 2) for ti in t]
            heave = [m["heave_m"] * 1000 * math.sin(w * ti) for ti in t]
            with st.expander("Model & assumptions"):
                st.markdown(r"""
- Regular waves, linear dispersion $\omega^2 = g k \tanh(k h)$; amplitude $a = H/2$.
- Pressure attenuation to the keel: $\cosh k(h-T)/\cosh kh$ (finite depth) or $e^{-kT}$ (deep water).
- Quasi-static excitation averaged over the hull: heave $a\,\sin u/u$, pitch/roll $k a\,3(\sin u - u\cos u)/u^3$, $u = kL/2$ (or $kB/2$).
- Response = excitation × 1-DOF magnification $1/\sqrt{(1-r^2)^2+(2\zeta r)^2}$, $r = \omega/\omega_n$.
- Natural periods: heave $2\pi\sqrt{T(1+a_{33})/g}$, pitch $2\pi k_{yy}\sqrt{(1+a_{55})/(g\,GM_L)}$ with $a_{33}=a_{55}=0.5$, $k_{yy}=0.25L$ (assumed); roll from tab 1.
- Green water: wave surface minus hull motion at bow and stern, compared with the lowest freeboard.
- Stationary model (encounter = wave frequency). Heave/pitch for head waves, roll for beam waves. Phases quasi-static.""")
    else:
        up = st.file_uploader("CSV with columns t, roll, pitch (s, °, °) - optional heave (mm)", type="csv")
        if not up:
            st.info("Upload a CSV logged from the MPU6050 / phone, or try the sample file below.")
            rs = random.Random(1)
            tt, rr_, _ = simulate_roll(res_d.roll_period if res_d.gm > 0 else 0.5, 0, 0, 1.0, 0.08, initial_deg=10,
                                       duration_s=10.0, dt=0.01)
            sample = pd.DataFrame({"t": tt, "roll": [x + rs.gauss(0, 0.3) for x in rr_],
                                   "pitch": [rs.gauss(0, 0.2) for _ in tt]})
            st.download_button("Sample CSV (simulated free roll decay, with sensor noise)", sample.to_csv(index=False),
                               "sample_roll_decay.csv", "text/csv")
        else:
            df, err = read_motion_csv(up)
            if err:
                st.error(err)
            else:
                t, roll, pitch = df.t.tolist(), df.roll.tolist(), df.pitch.tolist()
                heave = df.heave.tolist() if "heave" in df.columns else None
                label = "measured"
                st.markdown("**Roll-decay analysis** - enter the condition the record was taken in:")
                c1, c2 = st.columns(2)
                test_load = c1.number_input("Load on board during the test (g, centred)", 0.0, 2000.0, 0.0, key="dec_load")
                test_temp = c2.number_input("Water temperature during the test (°C)", 0.0, 35.0, 15.0, key="dec_temp")
                res_test = analyse(hull_d, [Cargo("test", test_load / 1000, 0, 0, 0.05, 0.04, 0.025)] if test_load else [],
                                   seawater_density(0, test_temp), **lim)
                d = roll_decay(t, roll)
                if d is None:
                    st.info("No usable free decay: need ≥ 3 decaying cycles above the sensor noise "
                            "(a growing or steady oscillation is not a decay test).")
                else:
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Natural roll period Tn (measured)", f"{d['Tn']:.3f} s",
                              f"{(d['Tn'] / res_test.roll_period - 1) * 100:+.0f}% vs calculated" if res_test.gm > 0 else None,
                              delta_color="off")
                    c2.metric("Damping ratio ζ (measured)", f"{d['zeta']:.3f}", f"δ = {d['delta']:.3f}", delta_color="off")
                    if res_test.gm > 0:
                        k_eff = k_from_period(d["Tn"], res_test.gm)
                        c3.metric("Effective k (from Tn and test GM)", f"{k_eff*1000:.1f} mm",
                                  f"{k_eff / hull_d.overall_beam:.2f} × beam", delta_color="off")
                        offer_value(c4, "Use this k for the hull", hkey + "kr", k_eff * 1000, KR_MAX_MM)
                        st.caption(f"k uses GM = {res_test.gm*1000:.1f} mm of the test condition above. "
                                   "Apply the inclining-test VCG (tab 5) first so this GM is measured, not estimated.")
                    else:
                        c3.error("The hull is unstable in the test condition - check the inputs.")
                st.caption("Green water is not computed for measured data (no wave-surface record).")

if t is not None:
  with tab_dash:
    amp, period = roll_stats(t, roll)
    peak = max(abs(x) for x in roll)
    peak_p = max(abs(x) for x in pitch)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(f"Roll amplitude ({label})", f"{amp:.1f}°")
    c2.metric(f"Roll period ({label})", f"{period:.2f} s")
    c3.metric("Peak |roll|", f"{peak:.1f}°")
    c4.metric("Peak |pitch|", f"{peak_p:.1f}°")
    deck_edge = math.degrees(math.atan(2 * res_d.freeboard / hull_d.overall_beam))
    bow_edge = math.degrees(math.atan(2 * res_d.freeboard / hull_d.length))
    if peak > deck_edge:
        problems.append(f"Roll reaches {peak:.1f}° > deck-edge immersion {deck_edge:.1f}°. "
                        "Lower or centre the cargo (tab 1), or avoid waves near the roll period.")
    elif peak > lim["max_heel_deg"]:
        problems.append(f"Roll {peak:.1f}° exceeds the {lim['max_heel_deg']:.0f}° limit. "
                        "Lower / centre cargo (tab 1) or change heading to alter the wave period.")
    if peak_p > bow_edge:
        problems.append(f"Pitch {peak_p:.1f}° > bow/stern deck immersion {bow_edge:.1f}°.")
    if rel_motion is not None and rel_motion > res_d.min_freeboard:
        problems.append(f"Green water: the wave rises {rel_motion*1000:.1f} mm relative to the bow/stern against "
                        f"{res_d.min_freeboard*1000:.1f} mm lowest freeboard. Reduce load or avoid this sea state.")
    for p in problems:
        st.error("ALERT: " + p)
    if not problems:
        st.success("Motions within limits" + ("." if rel_motion is not None else " (green water not checked)."))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=t, y=roll, name=f"roll ({label}, °)"))
    fig.add_trace(go.Scatter(x=t, y=pitch, name=f"pitch ({label}, °)"))
    if heave is not None:
        fig.add_trace(go.Scatter(x=t, y=heave, name=f"heave ({label}, mm)", yaxis="y2", line=dict(dash="dot")))
        fig.update_layout(yaxis2=dict(title="heave (mm)", overlaying="y", side="right", showgrid=False))
    for s in (1, -1):
        fig.add_hline(y=s * lim["max_heel_deg"], line_dash="dot", line_color="orange")
        fig.add_hline(y=s * deck_edge, line_dash="dash", line_color="red")
    fig.update_layout(xaxis_title="time (s)", yaxis_title="angle (°)", height=400, legend=dict(orientation="h"))
    st.plotly_chart(fig)

# ---------------- 5. validation ----------------
with tab_val:
    st.subheader("Validation - calculated vs measured")
    hkey_v = "rev" if st.radio("Hull", ["Revised (v2)", "Baseline (v1)"], horizontal=True, key="vh").startswith("Rev") else "base"
    hull_v = rev if hkey_v == "rev" else base
    rho_v = seawater_density(0, st.number_input("Test-tank water temperature (°C)", 0.0, 35.0, 15.0))
    st.caption(f"Fresh water at this temperature: ρ = {rho_v:.1f} kg/m³ (EOS-80). Weigh the printed hull first - "
               "do not trust the slicer mass.")
    num_cfg = lambda label, lo, hi: st.column_config.NumberColumn(label, min_value=lo, max_value=hi)

    st.markdown("#### Test A - draught vs load (centred loads)")
    vkey = f"val_{hkey_v}"
    if vkey not in st.session_state:
        st.session_state[vkey] = pd.DataFrame([dict(test=f"{g} g centre", load_g=float(g), measured_draft_mm=None)
                                               for g in (0, 150, 250, 400)])
    vt = st.data_editor(st.session_state[vkey], num_rows="dynamic", width="stretch", key=vkey + "_ed",
                        column_config={"load_g": num_cfg("load (g)", 0.0, 5000.0),
                                       "measured_draft_mm": num_cfg("measured draught (mm)", 0.0, 300.0)})
    vt = vt.assign(load_g=pd.to_numeric(vt.load_g, errors="coerce"),
                   measured_draft_mm=pd.to_numeric(vt.measured_draft_mm, errors="coerce"))
    rows = []
    for r in vt.dropna(subset=["load_g"]).itertuples():
        if r.load_g < 0:
            st.error(f"Row '{r.test}': load cannot be negative.")
            continue
        p = analyse(hull_v, [Cargo("load", r.load_g / 1000, 0, 0, 0.05, 0.04, 0.025)] if r.load_g else [], rho_v, **lim)
        md = r.measured_draft_mm
        err = md - p.draft * 1000 if pd.notna(md) else None
        rows.append({"test": r.test, "calc draught (mm)": round(p.draft * 1000, 2),
                     "meas draught (mm)": md, "diff (mm)": None if err is None else round(err, 2),
                     "error (%)": None if err is None else round(err / (p.draft * 1000) * 100, 1),
                     "within ±1 mm (reading + meniscus)": None if err is None else abs(err) <= 1.0})
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

    st.markdown("#### Test B - inclining experiment (measures GM → real hull VCG)")
    st.caption("Empty hull + inclining weights on deck. Record the heel with the weights centred (0 offset row), then "
               "shift weight sideways and read the heel (phone inclinometer or plumb line, keep 1–4°). "
               "A straight line tanθ = tanθ₀ + w·d/(Δ·GM) is fitted, so an initial list does not bias GM.")
    c1, c2 = st.columns(2)
    W = c1.number_input("Total inclining weights on board (g)", 1.0, 1000.0, 50.0 if hkey_v == "rev" else 10.0,
                        key="W_" + hkey_v)
    zw = c2.number_input("Their height above keel (mm)", 0.0, 300.0, hull_v.depth * 1000 + 5, key="zw_" + hkey_v)
    ikey = f"incl_{hkey_v}"
    if ikey not in st.session_state:
        w0, d0 = (25.0, 60.0) if hkey_v == "rev" else (5.0, 30.0)
        st.session_state[ikey] = pd.DataFrame([dict(moved_g=w0, offset_mm=s * d0, heel_deg=None)
                                               for s in (0, 1, 2, -1, -2)])
    it = st.data_editor(st.session_state[ikey], num_rows="dynamic", width="stretch", key=ikey + "_ed",
                        column_config={"moved_g": num_cfg("moved weight (g)", 0.0, 1000.0),
                                       "offset_mm": num_cfg("sideways offset (mm)", -300.0, 300.0),
                                       "heel_deg": num_cfg("measured heel (°)", -20.0, 20.0)})
    it = it.apply(pd.to_numeric, errors="coerce").dropna()
    if (it.moved_g > W).any():
        st.error("A moved weight is larger than the total inclining weight on board - check the inputs.")
        it = it.iloc[0:0]
    probe = analyse(hull_v, [Cargo("weights", W / 1000, 0, 0, 0.02, 0.02, max(2 * (zw / 1000 - hull_v.depth), 0.001))],
                    rho_v, **lim)
    disp = hull_v.mass + W / 1000
    fit = inclining_gm((it.moved_g / 1000).tolist(), (it.offset_mm / 1000).tolist(), it.heel_deg.tolist(), disp) \
        if len(it) else None
    if fit is None:
        st.info(f"Enter at least 3 measured rows with different offsets. Calculated GM for this set-up: "
                f"{probe.gm*1000:.1f} mm.")
    else:
        gm_m, r2, th0 = fit
        kg_tot = probe.kb + probe.bm - gm_m
        kg_hull = (disp * kg_tot - W / 1000 * zw / 1000) / hull_v.mass
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("GM measured", f"{gm_m*1000:.1f} mm", f"R² = {r2:.3f} · θ₀ = {th0:+.2f}°", delta_color="off")
        c2.metric("GM calculated", f"{probe.gm*1000:.1f} mm",
                  f"{(gm_m / probe.gm - 1) * 100:+.0f}% diff" if probe.gm > 0 else None, delta_color="off")
        c3.metric("Hull VCG measured", f"{kg_hull*1000:.1f} mm", f"assumed {hull_v.vcg*1000:.1f} mm", delta_color="off")
        if r2 < 0.95:
            c4.warning("R² < 0.95: points are not on a straight line. Repeat readings (water inside? wind?) "
                       "before using this result.")
        elif not 0 < kg_hull < 2 * hull_v.depth:
            c4.error("Implausible VCG - check angles, offsets and masses.")
        else:
            offer_value(c4, "Use as hull VCG", hkey_v + "kg", kg_hull * 1000, KG_MAX_MM)

    st.markdown("#### Test C - roll decay")
    st.caption("Rock the model ~10° and release; log t, roll at ≥100 Hz (MPU6050 or phone). Upload the CSV in tab 4 and "
               "enter the test load → Tn, ζ and k are extracted automatically.")
    st.markdown("""**Report with the results:** ruler resolution and meniscus (±1 mm), water temperature, weighed hull
mass, sealant/water uptake (weigh again after testing), and why any mismatch occurs (e.g. rounded bottom → not wall-sided).""")
