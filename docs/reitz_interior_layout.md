# J. Wayne Reitz Union: interior layout (reference research)

Status: reference research. Since it is built: the Reitz Union interior is **area 2 of Course 2** (`levels/wf`, entered through the real doors of the exterior landmark by instant warps; `tools/campus/interiors/reitz.py`, `docs/flow.md` §9.2.1). The build uses its own vertical frame (the Ground Level at game 0 m, the stage centre (−470, −293), not the `center_m` below) and deviates where `reitz.py` NOTES say so. It is also the reference for the reviewers who check the build against the real building.

Files:

| File | What |
|---|---|
| `data/uf/reitz_interior_layout.json` | The layout as data (schema `sgl64.reitz_interior_layout/1`): 8 floors (Lower Level to Level 6) with z levels, outlines, every room/corridor polygon, walls, doors, windows, fixtures, wayfinding POIs, exterior entrances, elevator/stair cores, the atrium, SwampHacks XII room uses, finishes from the photos, photo coverage, deviations, sources. Map metres, same origin as `campus.json`. |
| `art/levels/reitz_interior/layout_ll.png`, `layout_g.png`, `layout_l1.png` … `layout_l6.png` | One sketch per floor, drawn from the JSON. |
| `art/levels/reitz_interior/layout_stack.png` | Schematic west→east stack of the levels (game heights). |
| `art/levels/reitz_interior/reference_sheets/reitz_ref_*.jpg` | 17 contact sheets: the official level maps + one sheet per space group (109 photos). |
| `reference/interiors/reitz/` (gitignored) | The photos, the official level-map PDF + renders, the wayfinding-map bundle, and `index.json` (file, source page, image URL, credit, licence, caption, space, floor, view direction, era). |

How confident each item is (every zone, prop and door in the JSON carries one of these labels):

- **sourced**: stated in a cited source (text, photo or OSM tag).
- **plan**: from the official indoor wayfinding geometry (S2), registered to the OSM footprint (±1.5 m at the outer walls); room names cross-checked against the printed 2025 level maps (S1).
- **inferred**: my reading of the sources, not stated anywhere (positions, sizes, colours).
- **gameplay**: nothing yet; section 9 lists the suggested deviations.

Coordinates: map metres, x east, y north, origin Century Tower (as `campus.json`). `z_game_m` is the height above the **Ground Level** floor. `center_m` = (−441.5, −289.5), so game `X = (x + 441.5)·100`, `Y = z·100`, `Z = −(y + 289.5)·100`. Yaw: 0 faces +Z (south), 0x4000 east, 0x8000 north.

---

## 1. Summary

1. **The geometry is the real building plan.** The Reitz Union publishes an indoor wayfinding map (Mappedin) and links each bookable room to it from its *Our Spaces* page. Its public data bundle has georeferenced polygons for every room, wall, door and fixture on 11 floors (S2). I registered it to the OSM footprint that the exterior landmark extrudes (section 3), and every label on the official 2025 printed level maps (S1) lands in the matching room. Room areas agree with the published square footage (2315: 723 sq ft = 67.2 m², plan 67.5 m²; Grand Ballroom 11,562 sq ft = 1,074 m², plan 1,119 m² including walls).
2. **Eight levels:** Lower Level (LL), Ground (G), Level 1, 2, 3, 4 (tower), 5 and 6 (Reitz Union Hotel, 36 rooms). OSM's level 0 is Ground.
3. **The site slopes, so both Ground and Level 1 are "front doors".** The 2016 north entrance and the North Lawn tabling area are on Level 1, recessed ~14 m under the overhang of the upper floors. The South Terrace / amphitheater doors, the breezeway (circle drive and garage side), the hotel entrance and the north doors by Subway are on Ground. The Lower Level only opens at the south end (loading dock, garage route).
4. **The atrium** (2016 wing, just east of the Orange elevators) runs from the Ground-level lounge up to the roof over Level 3, with two voids on Level 1 (~170 + ~220 m²), balconies on L1-L3 and open scissor stairs. Its look, from photos: cedar-slat ceiling with dark curved ribs (patterned on a gator's underbelly), white curved balcony fronts, metal picket railings with gator-shaped cut-outs, terrazzo with inlaid gator tracks, and giant orange UF letters on a gator-skin wall. A "Swamp Boss" gator-head statue and a free library stand on the atrium floor.
5. **Game Room (Ground) is under the food court (Level 1)** in the south wing. Its 14 bowling lanes run north-south with the pins at the south wall. The billiards area (9 tables + 1 snooker) is in the north-west part, and the Gator Esports Center is a long narrow room along the west side (2,555 sq ft, 44 stations).
6. **Food court (Level 1):** an enclosed vendor block (~743 m²) with a curved storefront, wrapped by the seating hall along the curved SE glass. The vendors are Starbucks, Panda Express, Sonic (opened 2025), Baba's Pizza, The Halal Shack, Mi Apa, Mac Shack and Shake Smart. Their wayfinding and OSM pins disagree, so treat the list as "who is there", not exact positions.
7. **Ballrooms:** the Grand Ballroom (L2, west wing) is double height, because Level 3 has no floor over it. The Rion Ballroom is on L3 in the south wing. The Auditorium (299 seats) and The Gallery are on L2 north of the core.
8. **Meeting rooms:** G310-G330 sit in the 2016 wing on Ground, next to the Senate Chamber. 2315-2365 are on L2 above the food court, 2101-2108 on L2 in the 2016 wing, and 3305-3320 on L3 north of the core.
9. **Photos:** 109 photos from public sources. Coverage is good for the atrium, Game Room, esports, ballrooms, auditorium, meeting rooms, the Level 4 rooms, the hotel rooms and both exteriors. It is thin or missing for the hotel lobby, Orange & Brew, the Info Desk, the current Starbucks, Subway/The Market, enclosed stairs, elevators and restrooms (section 8).
10. **Three findings about the existing exterior landmark** (`reitz_reitz_union.py`, not changed here):
    - It puts an enterable food court at deck 2.0 m behind the curved glass. The real food court is on Level 1.
    - Its tower block is 40 × 22 m at y −274..−252. The real Level 4-6 floor plate is about 35 × 34 m at y −291..−255.
    - The old Colonnade building it names was demolished in 2013.

---

## 2. Sources and what they say

- **Official level maps 2025 (S1).** Six pages (Lower, Ground, 1, 2, 3, 4) give room names per level. They are drawn with page-up = west and right = north. I rendered them at 100/300 dpi and registered each page to the plan outline by mask overlap (IoU 0.95 for L2/L3, 0.88-0.89 for LL/L4, 0.81 for L1, 0.75 for G; Ground is lowest because the printed page includes the breezeway). Every label was mapped to metres (`printed_map_labels`).
- **Indoor wayfinding map (S2).** Mappedin venue `67bdc505679a9d000bfacd1d`, linked from union.ufl.edu. The public viewer downloads one data bundle (`mappedin-public-mvf-prod…/mvf?venue=…` → zip, updated 2026-07-31), and I downloaded it the same way. It contains floors, spaces (rooms/corridors/voids), obstructions (walls + named fixtures such as "Bowling Lanes", "Billiards & Pool Area", "UF Letters", "Swamp Boss - Gator Head Statue", "Info Desk", "Florida Hall of Fame Wall"), doors (exterior flag), windows, elevator/stair connections and POIs. The bundle is in `reference/interiors/reitz/maps/mappedin_mvf/`.
- **Our Spaces (S3).** Square footage and capacities. Grand Ballroom 11,562 sq ft (¾ 8,610; ½ 5,740; ¼ 2,870). Rion 8,669 (½ 4,335). Auditorium 2,400 / 299 seats. Chamber 3,271. G310 1,268, G315 1,037, G320 1,424, G325 986, G330 1,278. 2315 723, 2320 678, 2325 700, 2330 722, 2335 1,185, 2340 1,199, 2345 339, 2350 377, 2355 1,742, 2360 895, 2365 1,782. 3305 667, 3310 738, 3315 1,487, 3320 1,503. Arredondo Café 2,400, Matthews Suite 1,096. The page also has one or more photos per room.
- **Game Room / Esports / Arts & Crafts / Gallery / Dining pages (S4-S8).** 14 lanes, 9 billiards + snooker, 2 foosball, air hockey, table tennis. Esports has 44 stations (12 arena PCs, 24 game pods, 6 couch co-op, 2 stream pods). The ACC (ceramics, kilns, sewing) is on the Lower Level, The Gallery on Level 2 by the Auditorium, the barbershop on Ground and the UF Bookstore on Level 1.
- **History (S9, S11-S13).**
  - Opened 1967. The 2013-16 project ($70.7 M, CannonDesign + Walker Architects, Skanska) demolished the Colonnade building and built about 126,000 sq ft in its place, plus about 90,000 sq ft of renovation (ENR).
  - The old central staircase was removed in 2014 and replaced by stacked restrooms (Alligator).
  - The foyer railings have gator cut-outs on all three floors, and the wooden ceiling mimics a gator's underbelly (Alligator photo captions, 2015-16).
  - The Bryan Lounge is "on the first floor" (S9). It is not on the current maps.
- **OSM (S14).** Building outline w863211313 (the landmark footprint), food court outline w1315821081 (level 1), level-tagged doors, rooms and vendor POIs. These confirm the level numbering.

---

## 3. Plan fit (wayfinding map → OSM footprint)

The raw wayfinding geometry sits about 2.0 m east of the OSM outline and, on Levels 2-3, up to about 2 m north of it. Each floor is also rotated 0.5-1.1° from the OSM axis. OSM's own indoor Level 2 outline (w1323490478) agrees with the raw data on the north wall, so the upper floors may really overhang the ground-level line.

So that the interior fits inside the exterior landmark:

1. Each floor is rotated about the shared elevator core (−430, −269) so that its main wall axis matches the OSM axis (G 1.12°, L1 0.65°, L2 0.52°, L3 0.60°, LL 1.15°, L4-L6 0.84-0.87°).
2. All floors then get **one** translation, (−2.04, −1.96) m, which puts opposite exterior walls evenly on either side of the OSM edges. A single translation keeps the floors stacked: the elevators line up within 0.5 m on every floor.

Residuals (outermost plan wall minus OSM edge, + = outside), from `plan_fit.per_floor`:

| Floor | W wall | E wall | N (ballroom wing) | N (core) | N (2016 wing) | S (ballroom wing) | S wing south |
|---|---|---|---|---|---|---|---|
| G | −1.5 | +0.7 | +0.3 | −1.7 | −0.6 | −1.5 | +0.5 |
| L1 | −1.8 | +1.3 | +0.2 | −1.2 | 0.0 | +0.3 | +0.5 |
| L2 | −0.8 | +0.2 | +0.3 | −1.3 | +0.2 | +1.3 | −1.8 |
| L3 | −0.3 | +0.3 | −0.1 | −1.3 | +0.1 | – | −1.3 |

A −1.3 at the core's north wall is real: the Level 1 covered bridge / colonnade runs outside it. The −3.6 to −4.6 on the south wing's west and east walls at L2/L3 are real setbacks above the food court. The raw, unregistered bundle stays in `reference/` if a later builder prefers a different fit.

---

## 4. Floors

| Floor | Game z | Real z (est.) | Plan area | What is there |
|---|---|---|---|---|
| LL | −6.0 | −4.5 | 5,774 m² | Arts & Crafts Center, Dance Studios A/B, SG Print Lab, DSL Technology Services, lockers, restrooms; south doors to the loading dock / garage |
| G | 0.0 | 0.0 | 6,949 m² | Atrium lounge, hotel reception, Subway, The Market, SG Bike Repair, barbershop, Game Room, Gator Esports Center, Orange & Brew (Cabo Mexican Grill POI), Senate Chamber, G310-G330, Career Connections Center (lower), breezeway |
| L1 | 6.0 | 4.5 | ~9,500 m² in the footprint (15,503 with the Bookstore / Constans links) | North entrance, Info Desk, tabling area, atrium balconies, food court, GatorWell, Administration, Catering, Event Services, Career Connections Center |
| L2 | 12.0 | 9.0 | 8,551 m² | Grand Ballroom, Auditorium, The Gallery, 2315-2365, Brown Center, Student Engagement, 2101-2108, SG Graphics |
| L3 | 18.0 | 13.5 | 8,190 m² | Rion Ballroom, 3305-3320, Reflection Room, Student Legal Services, SG + SG Finance, Sorority & Fraternity Life, Student Engagement L3 |
| L4 | 24.0 | 18.0 | 1,158 m² | Arredondo Café, Matthew's Suite (tower) |
| L5 | 28.0 | 21.2 | 1,151 m² | Hotel rooms 501-520, balconies |
| L6 | 32.0 | 24.4 | 1,160 m² | Hotel rooms 601-620, balconies |

Real elevations are not published. 4.5 m per floor below the tower and 3.2 m on the hotel floors are estimates. The game spacing (6.0 m, hotel 4.0 m) does not depend on them.

![Lower Level](../art/levels/reitz_interior/layout_ll.png)
![Ground Level](../art/levels/reitz_interior/layout_g.png)
![Level 1](../art/levels/reitz_interior/layout_l1.png)
![Level 2](../art/levels/reitz_interior/layout_l2.png)
![Level 3](../art/levels/reitz_interior/layout_l3.png)
![Level 4](../art/levels/reitz_interior/layout_l4.png)
![Level 5](../art/levels/reitz_interior/layout_l5.png)
![Level 6](../art/levels/reitz_interior/layout_l6.png)
![Stack](../art/levels/reitz_interior/layout_stack.png)

What each floor record in the JSON holds:

- `zones`: every room and corridor polygon, keeping the plan's space id.
- `props`: named fixtures and the breezeway columns.
- `pois`: wayfinding pins.
- `openings`: exterior doors with their facing.
- `windows`: only where the plan maps them. Most curtain walls are not mapped; use the photos.
- `walls_m`: wall centre-lines. Doors are not cut out of them.
- `doors_m`: door segments lying on the walls. Cut these out of `walls_m`.
- `connections_mvf`: raw stair/elevator nodes. These are incomplete; use `vertical` instead.
- `printed_map_labels`: the S1 labels mapped into map metres.

### Entrances (`entrances`)

| Entrance | Floor | Where (map m) | Faces |
|---|---|---|---|
| North entrance (2016, main) | L1 | (−384.6..−378.2, −258) | N |
| South Terrace doors | G | (−389.5..−381.2, −286.3) | S |
| Hotel entrance from the breezeway | G | (−462.2, −272..−269) | W |
| North doors by Subway / The Market / Bike Repair | G | (−445.8..−420, −245) | N |
| South exit to the terrace stairs | L1 | (−373.5, −283) | S |
| Food court → Level 1 Outdoor Walkway (to the Bookstore) | L1 | (−463, −330) | W |
| North exit stair | L2 | (−461, −244) | N |
| Loading dock / garage side | LL | (−439..−426, −330..−332) | S |

---

## 5. Elevators and stairs (`vertical`)

- **Blue elevators:** 4 cars in two facing pairs at x −448.8 / −441.3, y −269.6 / −272.3. They serve LL to L6 and are the only bank that reaches the hotel. On Ground they open beside the hotel reception desk.
- **Orange elevators:** 2 cars at x −416.3, beside the atrium. They serve LL to L3.
- **Service elevator:** at (−441.8, −279.6). It serves LL to L6.
- **Atrium stairs:** open scissor flights from G to L3 across the voids.
- **Enclosed stairs:**
  - core west (−452, −279.4) and core east (−428, −279.6), the east one running to the hotel floors
  - west bump (−519, −265.5)
  - north-west (−461.5, −243.5)
  - south wing south-west (−457.5, −331) and south-east (−426.5, −331.5)
  - 2016 wing north and south ends (−364.2, −260 / −283)
  - Career Connections Center internal stair (−473, −260.8)

---

## 6. Key spaces: what they look like (from the photos)

Contact sheets: `art/levels/reitz_interior/reference_sheets/`. The `materials_and_light` block in the JSON repeats these notes per zone, adds suggested vertex-colour light, and lists the new textures a builder would need.

- **Atrium (G-L3).**
  - Floor: white terrazzo with a blue patterned carpet inset under orange, grey and navy lounge furniture.
  - Balconies: white curved fronts with LED coves and vertical-picket metal railings.
  - Ceiling: cedar-tone wood slats with dark curved ribs, with a clerestory band at the top.
  - Stairs: white scissor stairs crossing the void.
  - Art: giant extruded orange UF letters on a blue base in front of a grey/white gator-skin wall, and navy gator footprints inlaid in the terrazzo.
- **Game Room (G).**
  - Floor: grey wood-look planks.
  - Lanes: 14 maple-look lanes with Brunswick ball returns and white round columns. A black overhead truss with monitors hangs over the approaches, and a video/banner strip sits above the pins with a gator mural on the masking units (Kosmic blacklight mode).
  - Seating: navy curved booths behind the approaches.
  - Billiards: blue-felt tables under square LED frames on blue/orange patterned carpet.
  - Walls: dark navy, with a "GAME ROOM - The University of Florida" space-themed wall graphic.
- **Gator Esports Center (G).** A long narrow room:
  - dark ceiling, wood-look floor
  - black desks with blue edge light
  - white hex neon panels on hex-textured walls and lit "GATOR ESPORTS CENTER" letters
  - glass streaming booths and a red-orange bench.
- **Food court (L1).**
  - The hall has white columns and white tile.
  - A diamond-checker (tan/brown/grey) queue ring runs along the curved servery front, under a curved soffit.
  - Each storefront has its own colours (Sonic: navy + red neon).
  - The curved SE glass wall has white horizontal bands.
- **Grand Ballroom (L2).**
  - Floor: royal-blue carpet with flowing white lines.
  - Walls: light grey with a band of white 3-D triangular acoustic panels, pilasters, and walnut double doors with transoms.
  - Fittings: 4 drop-down screens.
  - Ceiling: coffered, each coffer a field of white luminous slats.
  - A high clerestory band runs along one long wall.
- **Rion Ballroom (L3).**
  - Floor: maple hardwood.
  - Walls: white with dark-grey vertical panels.
  - Ceiling: acoustic tile crossed by red-brown wood slat beams.
- **Auditorium (L2).**
  - Seats: navy with honey-wood arms and backs on a raked floor.
  - Walls: wood panels by the screen, navy accents.
  - Ceiling: dark wood slat bands with LED coves.
- **Senate Chamber (G).**
  - Seating: curved tiers of grey desks with navy high-back chairs.
  - Dais: cherry wall with chevron reveals behind it, US and Florida flags.
  - Walls: cream.
- **Meeting rooms (typical).**
  - Floor: blue/grey patchwork carpet tile.
  - Walls: white with a white chair rail and one accent wall (royal blue on G310-G330, pale grey-blue on L2).
  - Ceiling: 2×2 acoustic tile with linear LEDs.
  - Doors: honey-wood with a narrow vision panel.
  - Framed art.
- **Level 4.**
  - Arredondo Café: olive carpet, full-height windows.
  - Matthew's Suite: grey-blue walls, white millwork, framed historic photos.
- **Hotel rooms.** Royal-blue accent wall, cherry furniture and blue bed skirts. The balconies have white slotted concrete balustrades.
- **Lower Level.**
  - Dance studios: black sprung floor, mirror walls.
  - Arts & Crafts Center: entrance with a hand-drawn colour mural and the ACC roundel.

---

## 7. SwampHacks XII (`swamphacks_xii`)

From the hacker guide, as relayed in the task brief. The Notion page needs JavaScript, so I did not re-read it here.

| Use | Floor | Rooms |
|---|---|---|
| Workshops | G | G310, G320, G325, G330 |
| Hacking | G | G315, G325, G330, Senate Chamber |
| Hacking | L2 | 2315-2340 |
| Main stage / ceremonies | L2 | Auditorium |
| Hacking, meals, expo | L2 | Grand Ballroom |
| Mentors | L2 | 2345, 2350 |
| Sleep | L2 | 2355, 2365 |
| Quiet room | L2 | 2360 |
| Volunteers | L3 | 3310 |
| SwampHacks rooms | L3 | 3315, 3320, Rion Ballroom |
| Showers | LL | No public plan names the room |
| Overnight entrance | G | Reitz Hotel ground floor near Subway: the ground-level north doors next to Subway, or the hotel entrance from the breezeway |

The sketches mark these rooms with a yellow star.

---

## 8. Photo coverage (honest)

109 photos in `reference/interiors/reitz/photos/` (index: `reference/interiors/reitz/index.json`), plus the official maps.

| Space | Photos | Status |
|---|---|---|
| Atrium / lobby | 7 (incl. the UF letters and the gator-track floor) | good (ENR 2016, Flickr, Alligator, UF) |
| North entrance + north facade | 5 + 12 context | good |
| Game Room | 24 | good (2025-26, after the renovation) |
| Gator Esports Center | 10 | good (UF + builder) |
| Grand Ballroom | 4 | good |
| Auditorium | 3 | good |
| Meeting rooms G310-G330 / 2315-2365 / 3305-3320 | 4 / 5 / 3 | good (one typical photo per room group) |
| Level 4 (Arredondo Café, Matthew's Suite) | 5 | good |
| Hotel rooms | 3 | good |
| Food court | 6 | thin (closed counter 2023, Sonic 2025, Starbucks counter 2017, older dining shots); no current overview |
| Breezeway | 3 | thin (2023 Flickr + one night shot) |
| Rion Ballroom, The Gallery, Senate Chamber | 1 each | thin |
| Arts & Crafts, dance studios | 2 each | thin |
| Career Connections Center, GatorWell, Bookstore link, Student Engagement | 1 each | thin (CCC from its 2018 opening; the GatorWell corridor location is not confirmed) |
| Starbucks | 2 | thin (2017 counter close-up before the 2018 refit + one pre-2016 shot); current counter not photographed |
| The Colonnade | 1 | pre-2016 only (demolished 2013) |
| **Hotel reception / lobby** | 0 | **none found** |
| **Orange & Brew / Cabo Mexican Grill** | 0 | **none found** |
| **Info Desk** | 0 | **none found** |
| **Meeting rooms 2101-2108** | 0 | **none found** |
| **Subway, The Market, barbershop, SG Bike Repair** | 0 | **none found** |
| **Showers (LL)** | 0 | **none found** (location unknown too) |
| **Enclosed stairwells, elevator lobbies, restrooms** | 0 | **none found** |

The whole table is in the JSON as `photo_coverage`, with per-photo file lists. There, `status` is count-based (3+ photos = good); the statuses in this table are my judgement of how useful the photos are. Sources searched:

- union.ufl.edu (every page in its sitemap)
- UF News archive, ENR, the Alligator (30 articles)
- Wikimedia Commons (category + search)
- Flickr Creative Commons through the Openverse API (≈120 hits)
- the hotel, builder (Oelrich), Student Engagement, Career, GatorWell and Business Services sites

Mainstreet Daily News blocks scripted access (403), so I skipped it. I did not use Google Images, paywalled pages or anything behind a login.

---

## 9. Deviations a builder should expect (`deviations`)

- **Floor height.** Floors are 6.0 m apart in the game (4.0 m on the hotel floors) against about 4.5 m real; plan dimensions stay 1:1.
- **Grand Ballroom.** It keeps its real double height: about 11 m clear in the game, against about 7 m real (estimated from photos).
- **Atrium.** It is real and already camera-friendly: Ground to the roof over L3, about 23.4 m in the game.
- **Bowling lanes.** They stay at regulation length, 18.29 m from foul line to head pin. The plan's 15.5 m lane block is extended north to y −303.9 (inferred).
- **Registration.** Every floor carries the shift described in section 3.

---

## 10. Open questions (`open_questions`)

- Real floor elevations, and the ceiling heights of the Grand Ballroom and Rion Ballroom.
- Which Lower Level room has the showers. The south half of the LL has two big unlabelled rooms.
- What the hotel lobby, Orange & Brew (now "Cabo Mexican Grill" per the wayfinding POI), the Info Desk and the current Starbucks look like.
- Exact vendor positions in the food court.
- The gator-shaped railing cut-outs are described in the Alligator, but the available photos are not sharp enough to show them.
- The north overhang of Levels 2-3 relative to the OSM building line.

---

## 11. Sources

See `sources` in the JSON (S1-S21) for URLs and what each was used for. The main ones:

- S1: [Reitz Union Level Maps 2025](https://union.ufl.edu/wp-content/uploads/2025/06/Reitz_Union_Level_Maps_2025.pdf)
- S2: the [indoor wayfinding map](https://app.mappedin.com/map/67bdc505679a9d000bfacd1d)
- S3: [Our Spaces](https://union.ufl.edu/event-services/our-spaces/)
- S4: [Game Room](https://union.ufl.edu/gameroom/)
- S5: [Gator Esports Center](https://union.ufl.edu/gatoresportscenter/)
- S10: [ENR 2016](https://www.enr.com/articles/40792-higher-education-best-project---univ-of-florida-j-wayne-reitz-union-student-center-expansion-and-renovation)
- S11: [UF News 2016](https://archive.news.ufl.edu/articles/2016/02/reitz-union-renovation-expansion-now-complete-1.html)
- S12: [The Independent Florida Alligator](https://www.alligator.org/)
- S14: OpenStreetMap (© OpenStreetMap contributors, ODbL)
- S15: [Wikimedia Commons](https://commons.wikimedia.org/wiki/Category:J._Wayne_Reitz_Union) and Flickr CC photos
- S18: the [SwampHacks XII hacker guide](https://swamphack.notion.site/p/29a3b41de22f8061a741c84448a3f5ce)
