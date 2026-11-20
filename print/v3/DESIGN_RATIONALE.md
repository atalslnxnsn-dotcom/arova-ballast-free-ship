# Why the v3 ballast-free catamaran — evidence for each claim

Every claim below is backed by one of two things: a number our own scripts produce from the printed geometry
(the script is named, so anyone can re-run it), or a cited source. Claims that rest on neither are marked
**design intent**: the organisers' CFD and the tank tests will confirm or reject them.

## 1. Stability without ballast comes from hull spacing
- **Evidence (`challenge_check.py`):** with 400 g centred, the transverse GM rises with the gap between the hulls:
  - gap 40 mm: 13 mm
  - gap 70 mm: 56 mm
  - gap 100 mm: 109 mm

  This uses the same two hulls; only the deck changes.
- **Why:** the waterplane inertia of two hulls grows with the square of their spacing. For two box hulls,
  BM = (b² + 3s²) / (12T), where b is the hull beam, s the hull centre spacing and T the draught (derived in our
  research notes from BM = I_T / V). Ballast is not needed: the hull layout gives the righting moment
  ([Britannica, metacentric stability](https://www.britannica.com/technology/naval-architecture/Metacentric-stability)).
- **Demo:** one demihull alone with 50 g on top has GM −28.6 mm and tips over. The catamaran with 150 g has
  GM 192 mm (`challenge_check.py`).

## 2. Why ballast-free matters (sustainability)
- Ballast water moves invasive species between ecosystems. IMO's Ballast Water Management Convention entered
  into force on 8 September 2017
  ([IMO](https://www.imo.org/en/mediacentre/hottopics/pages/bwm-default.aspx),
  [IMO press briefing](https://www.imo.org/en/MediaCentre/PressBriefings/Pages/21-BWM-EIF.aspx)).
- Real ballast-free and low-ballast concepts, such as Japan's NOBS hull form, get their stability from the
  shape of the hull instead of ballast tanks ([SRC Japan, NOBS](https://www.srcj.or.jp/system/wp-content/uploads/2021/12/NOBS.pdf),
  [Marine Insight](https://www.marineinsight.com/ballast-free-ship-designs/)). v3 applies the same principle with
  hull spacing.
- **Light ship = less power.** At a given speed, power scales with displacement^(2/3) (Admiralty coefficient,
  [Wärtsilä](https://wartsila.com/encyclopedia/term/admiralty-coefficient-admiralty-constant)). We cut the deck from
  3 to 2 mm after a strength check: 25 g lighter, still a 10× bending margin (`make_v3.py` comment, FIKIRLER.md).
  The whole ship is about 355 g of PLA (`print_estimate.py`), and the parts are reusable and swappable.

## 3. Safe in waves, and we know where the limit is
- **Evidence (`wave_map.py`):** over wave heights of 5–40 mm and periods of 0.4–1.6 s, at 250 g and 400 g, both decks
  keep the cargo deck dry and roll far below the windward-hull lift-off angle up to **H = 30 mm at every period**.
- **Honest limit:** very short, steep beam waves (T ≈ 0.4–0.5 s, H ≥ 35 mm) hit the catamaran's roll period. The
  risk disappears with a roll damping of 0.20 instead of 0.10. Answer: the **gap 70 backup deck**, swapped in a minute.
- The hulls are sealed solids. Water over the bow tips is shed and cannot flood the ship.

## 4. Built to be validated, not just drawn
- The app's hydrostatic table matches the printed hull mesh to **0.15 %** over 14 draughts (`verify_v3.py`).
- The files are already in print orientation, with 0 cm² of unsupported overhang. A 0.8 mm bed-edge chamfer absorbs
  elephant foot, so the deck still slides on with 0.30 mm clearance (`verify_v3.py`).
- In the tank, the team app compares prediction with measurement:
  - draught vs load
  - inclining test → measured GM and KG
  - roll decay → measured period and damping

## 5. Design intent (to be confirmed by CFD and the tank)
- Slender demihulls (length/beam ≈ 4.7) with a fine entry and a raised, wave-piercing bow: expected lower wave
  resistance and less slamming than a box hull of the same displacement. The judges' CFD leaderboard is the test.
  Send `arova_v3_CFD_hulls_gap100.stl`.
- Rounded bilges (6 mm) instead of sharp corners: expected less flow separation in turbulent water.
