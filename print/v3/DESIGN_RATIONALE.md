# Why the v3 ballast-free catamaran — evidence for each claim

Every claim below is backed by one of two things: a number our own scripts produce from the printed geometry
(the script is named, so anyone can re-run it), or a cited source. Claims that rest on neither are marked
**design intent**: the organisers' CFD and the tank tests will confirm or reject them.

## 1. Stability without ballast comes from hull spacing
- **Evidence (`challenge_check.py`):** with 400 g centred, the transverse GM rises with the gap between the hulls:
  - gap 40 mm: 38 mm
  - gap 70 mm: 91 mm
  - gap 100 mm: 156 mm

  This uses the same two hulls; only the deck changes.
- **Why:** the waterplane inertia of two hulls grows with the square of their spacing. For two box hulls,
  BM = (b² + 3s²) / (12T), where b is the hull beam, s the hull centre spacing and T the draught (derived in our
  research notes from BM = I_T / V). Ballast is not needed: the hull layout gives the righting moment
  ([Britannica, metacentric stability](https://www.britannica.com/technology/naval-architecture/Metacentric-stability)).
- **Demo:** one demihull alone with 50 g on top has GM −22.2 mm and tips over. The catamaran with 150 g has
  GM 256 mm (`challenge_check.py`).

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
  The whole ship is about 450 g of PLA with 4 watertight walls (`print_estimate.py`), and the parts are reusable and swappable.

## 3. Safe in waves, and we know where the limit is
- **Evidence (`wave_map.py`):** over wave heights of 5–40 mm and periods of 0.4–1.6 s, at 250 g and 400 g, both decks
  keep the cargo deck dry and roll far below the windward-hull lift-off angle up to **H = 30 mm at every period** (35 mm with roll damping 0.20). Our research suggests catamaran damping of about 0.15–0.25; the roll-decay test will measure it.
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
- Slender demihulls (length/beam ≈ 3.9; widened from 4.7 to favour load capacity and wave stability, the two tests the event scores directly) with a fine entry and a raised, wave-piercing bow: expected lower wave
  resistance and less slamming than a box hull of the same displacement. The judges' CFD leaderboard is the test.
  Send `arova_v3_CFD_hulls_gap100.stl`.
- Rounded bilges (6 mm) instead of sharp corners: expected less flow separation in turbulent water.

## 6. What we took from the team's other concepts (Electrical Layout, Print Assembly) - and why
| Idea | Decision | Reason |
|---|---|---|
| Battery low on the centreline, IMU flat on a rigid pad with its forward axis marked, strain relief on every cable | **Taken** | Small mass changes, much better measurements; the electronics cradle sits on the deck centreline |
| Leak test of the empty hulls first, then trim check with dummy loads, then electronics | **Taken** | Matches our validation plan (tab 5 of the app) |
| Battery in a bay recessed 28 mm below the deck | Not taken | Measured: a 50 g pack 28 mm lower raises GM by only ~1.7 mm on a 156 mm GM, but adds a part close to the water that must be sealed |
| 270 mm hull length (Electrical Layout) | Rejected | Breaks the 250 × 250 × 250 mm rule |
| Stern motors, shaft tubes, servo | Rejected | No propulsion is tested; every shaft through a hull is a leak path; the rubric gives no extra points for servos |
| Open hull shells closed by a screwed deck | Rejected | The deck seam becomes the waterline seal; our hulls are closed solids that cannot flood |
| Wider hulls for capacity (Print Assembly is 172 mm wide with 124 mm spacing) | **Taken further** | Our sweep chose 60 mm demihulls with a 100 mm gap (225 mm overall): highest load limit and wave margin inside the 250 mm limit |

## 7. Tested and rejected: smaller bow rocker (16 → 8 mm)
- A research note suggested a smaller keel rocker to regain waterline length and cut resistance.
- **Measured on our geometry:** the rocker tip rises only 16 mm, and the draught is 23–33 mm. The whole keel is already underwater, so the waterline length stays 235 mm either way.
- The change also made the ship slightly worse:
  - load limit 918 → 895 g (3-wall print mass)
  - lowest freeboard at 400 g 36.6 → 35.9 mm
  - safe wave height at 400 g (damping 0.10) 35 → 30 mm
- Decision: kept 16 mm (`challenge_check.py`, `wave_map.py`).
