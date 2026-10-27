# Domain Research: Where the Constants Come From

This file backs up every domain constant in `airdrop/model.py` and the [Parameters](PROBLEM.md#parameters) table with a source or a derivation.
The drop weight `w` is left out for now.

Unit conversions used throughout: 1 lb = 0.45359237 kg, 1 US gal = 3.785411784 L, 1 kt = 1.852 km/h.

## Summary

| Constant | Value in code | Where it comes from | Trust |
|---|---|---|---|
| `E` | 33,600 kg | Lockheed Service News V16N1: C-130H operating, equipped weight 74,078 lb = 33,601 kg | High (manufacturer) |
| `C` | 19,630 kg | Same table: maximum payload @ 2.5 g 43,274 lb = 19,629 kg | High (manufacturer) |
| `MTOW` | 70,300 kg | Same table: maximum takeoff 155,000 lb = 70,307 kg. Also in a C-130H ops-limits card | High (manufacturer) |
| `F` | 21,100 kg | Same issue: 6,960 US gal usable internal fuel, at 0.80 kg/L (JP-8) = 21,077 kg | High (capacity), medium (density) |
| `c` | 7.0e-5 /km | ≈ 2,270 kg/h at ≈ 537 km/h = 4.2 kg/km, divided by `M_REF` = 60,000 kg | Medium |
| `M_REF` | 60,000 kg | Mass range over which the 2,270 kg/h figure was observed (NCAR: 70.3 t down to 59.0 t) | Medium (our assumption) |
| `a`, `b` | `c × E`, `c` | Fuel flow proportional to total mass (Breguet range equation) | High (standard physics), linear form is a simplification |
| `R` | 1,700 kg | 45 minutes at ≈ 2,270 kg/h = 1,701 kg | Medium (rule is conservative for a turboprop) |
| `EARTH_RADIUS_KM` | 6,371.0088 km | IUGG mean Earth radius R₁ of the GRS 80 ellipsoid | High |
| Rural base filters | 1–150 m, 20–40 km | Our design choice, see [Base selection](#base-selection-filters) | Design choice, not sourced |

## Aircraft: why the C-130H

- The C-130 Hercules is the standard tactical airlifter for airdrops, and the Royal Malaysian Air Force flies C-130H aircraft.
- Lockheed published a full C-130H specification sheet (Service News V16N1, 1989), so every weight and the fuel capacity come from one manufacturer source.
- A turboprop at medium altitude flying straight legs fits our model better than a jet: drops happen at low speed, and the plane does not need a runway at the town.

## Weights: `E`, `C`, `MTOW`

**Source:** Lockheed Aeronautical Systems Company, *Service News* Vol. 16 No. 1 (January–March 1989), "C-130H and L-100-30 Specifications and Systems", p. 6, WEIGHTS table.

| Row in the source (C-130H column) | lb | kg | Code |
|---|---|---|---|
| Operating, equipped | 74,078 | 33,601 | `E = 33,600` |
| Maximum payload @ 2.5 g | 43,274 | 19,629 | `C = 19,630` |
| Takeoff: maximum | 155,000 | 70,307 | `MTOW = 70,300` |
| Landing: maximum | 130,000 | 58,967 | not used |

- The code rounds each value to the nearest 10 kg. The rounding error is under 0.05%.
- "Operating, equipped" includes crew and equipment but no fuel or cargo. That is exactly what `E` means in our model: the mass that is always on board.
- `MTOW = 155,000 lb` is confirmed independently by a C-130H ops-limits card ("Max T/O Weight 155,000 lbs"), and by the NCAR C-130Q table (same airframe, "Maximum gross weight for takeoff 155,000 lb").
- The 175,000 lb emergency overload weight is not used. An aid mission should plan to normal limits.

**Why the takeoff limit matters:** full internal fuel plus maximum payload is 21,100 + 19,630 = 40,730 kg, but `MTOW − E` allows only 36,700 kg.
So the plane cannot carry a full tank and a full load at the same time.
This is a real C-130H limit, and it is why the model has the constraint `F₀ ≤ MTOW − E − w × k`.

## Fuel cap: `F`

**Source:** *Service News* V16N1, p. 6 (FUEL CAPACITY, usable) and the Fuel System article.

- Four main wing tanks: 2 × 1,340 + 2 × 1,230 = 5,140 US gal.
- Two centre-wing auxiliary tanks: 2 × 910 = 1,820 US gal.
- Internal total: **6,960 US gal** usable.
- Two pylon (external) tanks add 2 × 1,360 = 2,720 US gal, for 9,680 US gal total. **Not used**, see below.

**Gallons to kilograms:** 6,960 US gal = 26,346 L.

| JP-8 density (kg/L at 15 °C) | Fuel mass |
|---|---|
| 0.775 (spec minimum) | 20,419 kg |
| **0.800 (typical)** | **21,077 kg** |
| 0.840 (spec maximum) | 22,131 kg |

- JP-8 density is specified as 0.775–0.840 kg/L at 15 °C (MIL-DTL-83133). Refinery data sheets give about 0.80 kg/L as typical.
- `F = 21,100 kg` matches 0.80 kg/L. Any density inside the spec moves `F` by at most 5%.

**Why internal tanks only:** with pylon tanks the fuel capacity (about 29,300 kg) is far above what `MTOW − E` lets the plane load with cargo on board, so the tank stops being a binding limit.
Using the internal tanks keeps the tank limit and the takeoff limit both meaningful.

## Fuel burn: `c`, `M_REF`, `a`, `b`

### Model form: burn proportional to mass

The model sets fuel per km to `c × total mass`, so `a = c × E` and `b = c`.

- This comes from the **Breguet range equation**.
  In level cruise at a fixed lift-to-drag ratio `L/D`, drag is `W / (L/D)`, so the power or thrust the engines must give scales with the weight `W`.
  With constant specific fuel consumption, fuel flow scales with `W` too: `dW/dx = −(SFC / (η · L/D)) · W` for a propeller aircraft.
- Integrating that gives the exponential decay in our fuel model (`du/dx = −b u`). The closed form in [PROBLEM.md](PROBLEM.md#fuel-model) is this equation, plus the step down in mass at each drop.
- **Known simplification:** real engines burn some fuel that does not scale with weight (accessories, bleed air: about 5–10% of fuel flow). Textbooks handle this by adding a fixed "accessory weight". Our `a` term can carry such an offset because `a` is a separate input from `c × E`.
- Climb, descent, wind and changes in altitude or speed are ignored (see [Limitations](PROBLEM.md#limitations)).

### Cruise fuel flow: about 2,270 kg/h

| Source | Figure | In kg/h |
|---|---|---|
| NCAR *C-130 Investigators Handbook*, ch. 1 §1.4 (C-130Q N130AR, "similar to a standard model C-130H") | "trading in-flight endurance … at a rate of roughly 5,000 lb per hour of fuel" | 2,268 |
| Same handbook | "with maximum gross weight at take off, requires approximately 5 hours of flying time to reach the maximum landing weight" (155,000 → 130,000 lb, so 25,000 lb in 5 h) | 2,268 |
| Former C-130 pilot (Warbird Information Exchange forum) | "about 4,500 lbs … per hour, cruise power, at about 23,000 feet" | 2,041 |

- Two independent statements in the NCAR handbook give the same 5,000 lb/h. We use 2,270 kg/h.
- The forum figure is 10% lower and comes from one person, so it is a sanity check only. It shows our value is not optimistic: if anything, we burn a little too much fuel.

### Cruise speed: about 537 km/h (290 kt)

- 537 km/h = 290 kt true airspeed.
- Corroboration: about 292 kt quoted for C-130H cruise (Infinite Flight community), 300 kt for the C-130J (SKYbrary), and 345 mph = 300 kt economical cruise (U.S. Navy C-130 page; variant not stated).
- The project first took this figure from SKYbrary's C-130 page. That page refused automated access when this file was written, so the figure rests on the corroborating sources above.

**Burn per km:** 2,268 kg/h ÷ 537 km/h = **4.22 kg/km**.

### Reference mass `M_REF = 60,000 kg`

The 2,270 kg/h figure does not state a gross weight. To turn kg/km into `c` (kg/km per kg of mass), we need the mass it was measured at.

- The NCAR handbook ties 5,000 lb/h to a plane flying from 155,000 lb down to 130,000 lb, so from 70.3 t down to 59.0 t.
- `M_REF = 60,000 kg` sits at the light end of that range.
- `c = 4.22 / 60,000 = 7.04 × 10⁻⁵` per km, which the code rounds to **7.0 × 10⁻⁵**.

**Sensitivity:**

| Assumed reference mass | `c` |
|---|---|
| 59,000 kg (NCAR landing weight) | 7.2 × 10⁻⁵ |
| **60,000 kg (code)** | **7.0 × 10⁻⁵** |
| 64,600 kg (middle of the NCAR range) | 6.5 × 10⁻⁵ |
| 70,300 kg (MTOW) | 6.0 × 10⁻⁵ |

A lighter `M_REF` gives a larger `c`, so the plane burns more and reaches fewer towns.
Our choice is at the conservative end: it never overstates how far the plane can fly.

### What `c` implies

| Mass | Burn per km (`c × mass`) |
|---|---|
| Empty, `E` = 33,600 kg | 2.35 kg/km (this is `a`) |
| `M_REF` = 60,000 kg | 4.20 kg/km |
| Full, `MTOW` = 70,300 kg | 4.92 kg/km |

- A full plane burns about 2.1 times as much per km as an empty one. This is the size of the weight effect the project is about (see [DECISIONS.md](DECISIONS.md), "No control experiment").
- The empty-plane value is an extrapolation: a C-130H never flies at `E`, since it always carries fuel. It only enters the model as the intercept `a`.

## Fuel reserve: `R = 1,700 kg`

`R` = 45 minutes of cruise: 0.75 h × 2,268 kg/h = **1,701 kg**.

| Rule | Final reserve |
|---|---|
| U.S. 14 CFR 91.167 (IFR, all aircraft) | Fuel to the destination, then the alternate, then 45 minutes at normal cruising speed |
| ICAO-style rules (e.g. South Africa CAR 91.07.12, UK CAA NCC.OP.131) | 30 minutes holding at 1,500 ft for turbine aeroplanes; 45 minutes for reciprocating-engine aeroplanes |
| USAF AFI 11-202 Vol 3 | Cited in the project as the source for a 45-minute reserve. The text could not be retrieved to confirm; treat as low trust |

- The C-130H is a turbine (turboprop) aircraft, so ICAO-style rules would allow 30 minutes. 45 minutes is the stricter, U.S. IFR figure.
- We keep 45 minutes because the model has no alternate airport and no contingency fuel. A larger final reserve partly covers those missing margins.
- Using cruise burn for the reserve is a simplification: the rules measure holding fuel, which is usually a little lower than cruise burn.

## Distances: `EARTH_RADIUS_KM = 6,371.0088`

- This is the **IUGG mean Earth radius R₁ = (2a + b) / 3** of the GRS 80 ellipsoid (Moritz, *Geodetic Reference System 1980*), with `a` the equatorial and `b` the polar radius.
- It is the standard radius for great-circle (haversine) distance on a sphere. Many libraries round it to 6,371 km; the difference is 0.0001%.
- Haversine treats the Earth as a sphere, so it differs from the true ellipsoid distance by up to about 0.5%. That is far smaller than the uncertainty in the burn rate.
- Straight lines are realistic for an airdrop flight: the plane does not follow roads, and the sea between Peninsular and East Malaysia is not an obstacle.

## Base selection filters

These filters pick the three rural base sites from `MY.txt` (see [Bases](PROBLEM.md#bases)).
They are design choices, not values from a source. Each has a stated reason.

| Filter | Value | Reason |
|---|---|---|
| Population | `== 0` | A new airbase should not be built on a town. GeoNames uses 0 for "not recorded", so these may be small villages or plantation land |
| Feature class | `P` or `L` | Places and areas only. Excludes hills, caves and islands, where a runway cannot be built |
| Elevation (`dem`) | 1–150 m | A proxy for flat lowland. Malaysian high ground is steep and forested. Above 0 m excludes sea and swamp-level points |
| Distance to nearest town | 20–40 km | Far enough to be a rural site (no land acquisition in a town, less noise), close enough to be supplied by road |
| Tie-break | Farthest from towns in each region | Makes the rural-versus-airport comparison as sharp as possible |

- Long Geng already has an airstrip (`S.AIRF` row in `MY.txt` at the same point), which suggests the filters pick plausible sites.
- The non-rural bases need no filter: they are the main existing international airport of each region (`S.AIRP` rows).

## Experiment ranges

| Range | Value | Reason |
|---|---|---|
| Base comparison | `F = 21,100 kg` | The full internal tank, so the base location, not the tank, limits the route |

## Numerical constants (not domain values)

These are implementation choices. They do not need a domain source, but each has a reason.

| Constant | Value | Reason |
|---|---|---|
| `_EXP_MAX` | 709.0 | `ln(DBL_MAX) ≈ 709.78`; `math.exp` overflows a 64-bit float just above it |
| `TIE` (exact DP) | 1e-9 relative | Far above float rounding (about 1e-16), far below any real fuel difference |
| `max_n` (exact DP) | 15 | `O(n² · 2ⁿ)` time and `O(n · 2ⁿ)` memory: 15 towns is about 7.4 million operations and 0.5 million states |
| `L` (Approach B) | 20 | Candidate set for "replace 1 with 2": 20 × 19 = 380 ordered pairs per removed town. Lower it to speed up the search |
| `max_rounds` (Approach B) | 10,000 | Safety stop only. On all 745 towns the search ends after about 127 rounds |

## Sources

- Lockheed Aeronautical Systems Company, *Service News* Vol. 16 No. 1, January–March 1989 (C-130H weights, fuel capacity, fuel system): <https://www.lockheedmartin.com/content/dam/lockheed-martin/aero/documents/sustainment/csc/service-news/sn-mag-v11-v20/V16N1.pdf>
- NSF/NCAR Earth Observing Laboratory, *C-130 Investigators Handbook*, Chapter 1, Basic Specifications (weights, fuel trade rate): <https://www.eol.ucar.edu/sites/default/files/files_live/private/c130.investigators_handbook.chapter1.pdf>
- C-130H Ops Limits card, BaseOps (maximum weights): <https://www.baseops.net/wp-content/uploads/2015/08/c130h1_Ops_Limits-1.pdf>
- Warbird Information Exchange forum, former C-130 pilot on fuel burn: <https://www.warbirdinformationexchange.org/phpBB3/viewtopic.php?p=123746>
- Infinite Flight community, C-130H altitude and speed: <https://community.infiniteflight.com/t/c-130-h-altitude-and-speed/396550>
- SKYbrary, C-130 and C-130J pages: <https://skybrary.aero/aircraft/c130>, <https://skybrary.aero/aircraft/c30j>
- U.S. Navy, C-130 Hercules: <https://history.navy.mil/research/histories/naval-aviation-history/naval-aircraft/current-aircraft-inventory/c-130-hercules.html>
- JP-8 density limits (MIL-DTL-83133): Attock Refinery data sheet <https://www.arl.com.pk/wp-content/uploads/8a2.pdf>; DTIC <https://apps.dtic.mil/sti/pdfs/ADA554221.pdf>; Repsol JP-8 <https://www.repsol.com/en/products-and-services/aviation/jp-8/index.cshtml>
- Breguet range equation: MIT 16.001 lecture notes <https://www.ocw.mit.edu/courses/16-001-unified-engineering-materials-and-structures-fall-2021/mit16_001_f21_lec_driver_art.pdf>; TU Delft aircraft performance notes <https://www.aerostudents.com/courses/intro-to-aerospace-1/aircraftPerformance2FullVersion.pdf>
- U.S. 14 CFR 91.167, fuel requirements for IFR flight: <https://www.ecfr.gov/current/title-14/chapter-I/subchapter-F/part-91/subpart-B/section-91.167>
- South Africa Civil Aviation Regulations 91.07.12 (fuel): <https://www.acts.co.za/civil-aviation-act-2009/nr425_91_07_12_fuel_>
- UK CAA NCC.OP.131 (fuel scheme): <https://regulatorylibrary.caa.co.uk/965-2012/Content/Document%20Structure/06%20NCC/2%20Regs/15210_NCCOP131_Fuel_and_oil_supply_helicopters.htm>
- H. Moritz, *Geodetic Reference System 1980*, Bulletin Géodésique (mean radius R₁).
