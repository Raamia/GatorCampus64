# Marston Science Library: interior layout (Course 4)

Status: layout research. This is input for the Course 4 stage build (slot `ccm`, `LEVEL_CCM`, door 4, 8 stars) and for the Marston mission author. Nothing in the game uses it yet.

Files:

| File | What |
|---|---|
| `data/uf/marston_layout.json` | The layout as data (schema `sgl64.marston_layout/1`): floors with z levels, outlines, zones, props, doors, windows, columns, stair/elevator cores, atrium, terraces, mission anchors, backdrop, deviations, sources. Map metres, same origin as `campus.json`. |
| `art/levels/marston/layout_floor1.png` … `layout_floor5.png` | One sketch per floor, drawn from the JSON. |
| `art/levels/marston/layout_section.png` | Two sections (west→east through the atrium, north→south on the hub-door line). |

How confident each item is. Every zone, prop and door in the JSON carries one of these labels, and the sketches draw them differently:

- **sourced**: stated in a cited source (text or photo).
- **plan**: measured from the official UF floor-plan images, which I registered to the OSM footprint (±1 m; ±2 m on the west half of floor 3).
- **inferred**: my reading of the sources, not stated anywhere (positions, sizes, colours).
- **gameplay**: invented or changed for fun, the camera or a mission. Section 11 lists all of these.

Coordinates: map metres, x east, y north, origin Century Tower (as `campus.json`). `z_game_m` is the height above the hub's grade. The stage centre is (−59.6, −98.9) (`stages.json`), so game `X = (x + 59.6)·100`, `Y = z·100`, `Z = −(y + 98.9)·100`. Yaw: 0 faces +Z (south), 0x4000 east, 0x8000 north.

---

## 1. Summary

1. **The 2nd floor is the entrance floor and the 1st floor is a basement.** The official plans are titled "1st Floor (Basement)" and "2nd Floor (Entrance Floor)", and the 1987 article puts the entrance on Level 2 (S2, S3, S10). The hub door at z 0 therefore opens onto **floor 2**, and floor 1 is at z −6 in the game.
2. **The main doors are at the north-west corner of the north wing**, at X −69.2..−65.2, in a glass wall recessed to **Y −75.5**. That is 6.5 m behind the OSM north edge (−69.0) and 8.7 m west of the hub door (−58.5, −69.0). A second set of doors opens into the glass-roofed court between Marston and the CSE building, and Starbucks has its own court door (S3, photo S20).
3. **The terraces step down to the south-east, and each setback is exactly one 30-ft module.** Floor 4 is set back one module on the east and south sides; floor 5 is set back two modules on the east and to the SW tower's line on the south (S5, S6). The 1987 article confirms the 30-ft planning module (S10).
4. **The atrium is real but small.** It is a two-storey, 30-ft-square void above the old reference desk (S10). On the floor-3 plan it measures exactly one module cell: X −60.97..−51.83, Y −106.71..−97.57. The architect wanted three storeys with a central stair, and staff removed the stair. The game enlarges the atrium to 13.2 × 14.8 m and opens it through floors 3-5 to a roof skylight.
5. **Floors:**
   - Floor 1: Collaboration Commons: 21 glass group-study rooms, makerspace, two computer labs, L136 conference/visualization room.
   - Floor 2: entrance, service desk, Starbucks, group rooms 201D-H, computer lab, new books, collection highlights, sci-fi.
   - Floor 3: journals, theses, classroom L308, wellness room, the 150-gallon fish tank across from the elevators.
   - Floor 4: quiet floor, books A-Z.
   - Floor 5: silent floor with the best views.
   - Floors 1-3 are group-study floors, floor 4 quiet, floor 5 silent (S1, S7, S8).
6. **Cores.** On every floor there is a stair + restrooms in the NE tower, a stair in the SW tower, and a west core (stair + elevators, doors facing south) at the court corner. The 1987 article says stairs, restrooms and offices sit on the perimeter and the middle is open (S10).
7. **Game scale.** Plan dimensions stay 1:1. Floors are **6.0 m apart in the game** against about 4.2 m in reality, which leaves 5.4 m of clear height for the camera.
8. **Stacks.** Ranges are 1.2 m deep and 2.3 m tall (every second one is 3.6 m in this layout; the build caps those at 3.0 m so a jump on top still fits under the 5.4 m ceiling, and adds book-cart bridges across the aisles at the climbing ends), two per 30-ft bay, so the inferred columns stand in about 3.4 m aisles.
9. **Wide stairs.** The NE and SW towers become wide 30° stair halls with 5-6 m lanes. The west core keeps a steep (35°) secondary stair and two elevators. Elevator 1 is the "out of order" wall-kick shaft for Act 1.
10. **Area check.** The five registered plan outlines add up to 10,944 m² (117,800 sq ft). The 1987 article gives 112,000 sq ft gross over five floors, so the mapping is within 5 %.

---

## 2. What the sources say

### 2.1 The building

- **History:** Robert Q. Marston Science Library, 444 Newell Drive. It opened in February 1987 and merged the agriculture, biology, physical/earth science and mathematics branch libraries (S10, S11).
- **Architect:** VOA Associates of Orlando, which also designed the Computer and Information Science (CSE) building it is connected to (S18).
- **Size and seats:** 112,000 sq ft gross (91,000 assignable) on five floors, with 1,295 seats in 1987 (S10). Today there are over 2,000 seats (S7).
- **Layout principle (1987):** stairwells, restrooms and offices sit on the perimeter so the middle stays open and modular. Each floor had its own accent colour. Compact shelving was installed on floors 1 and 5, and a receiving room led to a freight elevator (S10).
- **First-floor renovation (2014):** the floor that held journals, government documents and the map library became the Collaboration Commons, about 26,000 sq ft and $5.7M. It added group rooms, a conference room, 3D printing, a multi-touch visualization wall and the MADE@UF lab (S11, S12).
- **2022 renovation:** floors 3-5 got new furniture and power and were closed for months. The first-floor "Makery" lost part of a wall, with the goal of a new entrance (S13).
- **Footprint (OSM w150860048):** 2,589 m², 57.3 × 57.6 m. Its parts:
  - a main block (X −89.3..−33.5, Y −87..−125)
  - a north wing (X −71..−39.6, Y −69..−87)
  - two chamfered brick towers, NE (stairs + restrooms) and SW
  - a zig-zag north-west face toward the CSE court
  - a loading-dock notch on the south (X −79.5..−71.2, Y −115.9..−125)
- **The court:** the glass-roofed court (OSM w859919297, roof from 10 m) runs diagonally between Marston and CSE. The yellow "French Fries" (*Alachua*, John Henry, 1987, 9.75 m) stands at its south-west mouth in the Marston Courtyard (S18, S19, S20).

### 2.2 Floor by floor

| Floor | Use | What is there | Sources |
|---|---|---|---|
| 1 (basement) | group | Collaboration Commons: 700+ seats, 21 group study rooms (L115-L135), L136 conference/visualization room, makerspace, North Lab (50 PCs) and South Lab (30 PCs), printing help desk, gender-inclusive/family restroom in the NE corner, supply vending | S1, S2, S7, S15, S16 |
| 2 (entrance) | group | Entrance & exit (north and court doors), book return, service desk (books, textbooks, tools and tech lending), Starbucks (own court door), group rooms 201D-H, 40+ computers incl. Macs, course reserves, new books, collection highlights, science fiction, exhibit cases, most staff offices | S1, S3, S10, S19 |
| 3 | group | Journals (north and south blocks), theses & dissertations, state agricultural documents, classroom L308 in front of the elevators, wellness room L307 (prayer, meditation, lactation), data consultation room, 6-ft fish tank across from the elevators, the real atrium opening; 320 seats after 2022 | S1, S4, S7, S13, S14 |
| 4 | quiet | General collection A-QC (north block) and QC-Z (south block), oversize, computers along the west wing, new quiet-study furniture | S1, S5, S13 |
| 5 | silent | Open silent-study plate, computers along the west wing, upper floors billed as having some of the best views on campus | S1, S6, S7 |

The fish tank holds 150 gallons and is home to rainbowfish, tiger barbs, corydoras and snails. A student club, the Florida Aquaculture and Aquarium Club, keeps it (S14). The Starbucks sits directly above the makerspace: construction at the Starbucks closed the makerspace for summer 2025 (S17).

### 2.3 Where the north main entrance is

- **North doors:** the 2nd-floor plan (S3) shows two "Entrance & Exit" door sets. One faces north at X −69.2..−65.2, with a vestibule to Y −78.8 and a book-return box beside it at the court corner.
- **Court doors:** the other set faces north-west into the court, on the zig-zag face.
- **Starbucks door:** Starbucks has its own door from the court.
- **Recessed north wall:** registered to OSM, the 2nd- and 3rd-floor north wall sits at Y −75.5 (measured −75.9 and −74.4), while floors 4-5 reach the OSM line at −69.0. The doors therefore open onto a **two-storey covered porch** about 6.5 m deep under the upper floors. OSM also maps covered picnic tables there.
- **Night photo (S20):** the 2022 photo captioned "Center of Marston" shows the court side. It shows the glass storefront doors, the zig-zag glazed bays stacked above them, the Starbucks sign beside them and the glass space-frame roof over the court.
- **Hub door:** the hub's door 4 sits 8.7 m further east, on the OSM line. That does no harm, because the warp is a teleport. Section 12 suggests an optional move.

### 2.4 The stepped exterior, the towers and the atrium

- **Terraces:** the terraces are on the **south-east**. Floor 4's east wall is the NE tower's notch line (X −42.6) and its south wall is the loading-dock line (Y −115.9); both are one module in from the outer walls. Floor 5's east wall is at X −51.83 (two modules in), and its south wall lines up with the SW tower's north face (Y −107.8). A 2011 photo shows the building stepping down in terraces (S20).
- **North-west face:** this face is a zig-zag of glass bays on floors 3-5, stacked over the court doors (S4-S6, S20).
- **Towers:** blank chamfered brick with bronze bands, rising about 5.7 m above the roof (S20; 22.5 m hub model).
- **Atrium:** see summary item 4. Floor 3 shows the opening as an empty square; the floor-4 plan has stacks over it.
- **No skylight is sourced over the atrium.** The hub model's "hipped glass skylight in the middle" happens to sit over the game atrium, so the game keeps one.

### 2.5 Group study rooms and how they are booked

- **Room count:** 21 rooms on floor 1 and 4 bookable rooms on floor 2, 25 in total. The floor-2 plan draws five (201D-H) (S1, S9).
- **Booking rules:** rooms are booked online in LibCal with a GatorLink login. Each booking runs 30-120 minutes, with up to two bookings (two hours) a day, one room at a time, and up to two weeks ahead. Groups need at least two people. The service desk helps with bookings (S7, S8, S9).
- **Room sizes (plan):** mostly about 3.9 × 4 m (10-19 m²). Corner rooms L118, L120 and L121 are about 30 m², and L136 is about 100 m².
- **There are no physical booking kiosks.** The Act 3 kiosks are a game device.

---

## 3. How the plans were mapped

The five plan images (Canva drawings, 2023-24) are schematic but drawn roughly to scale. I scanned each one for long dark wall lines. Then I fitted a piecewise-linear x and y mapping through the walls that match OSM edges:

- the NE tower's top, right and bottom
- the NE notch
- the east and south walls
- the SW tower
- the loading-dock notch
- the west wing

An overlay of the OSM outline on every plan agreed to about ±1 m. Floor 3's drawing squeezes its west half, so the error there is about ±2 m. The anchors are stored in `plan_fit` in the JSON. The plan images themselves were only used for measuring and are not copied into the project.

What the mapping showed:

- **Setbacks:** they are whole 30-ft modules (9.144 m). With the module grid running from the SE corner (east wall X −33.54, south wall Y −125.0), the grid lines are:
  - X: −33.54, −42.68, −51.83, −60.97, −70.12, −79.26, −88.40
  - Y: −125.0, −115.86, −106.71, −97.57, −88.42, −79.28, −70.14

  These also line up with the SW tower, the loading dock and the NE tower. The columns in the JSON (`columns_m`) sit on this grid inside the open floor. That placement is inferred.
- **Atrium:** the floor-3 atrium is exactly one cell of that grid.
- **North Lab:** the basement's North Computer Lab runs about 17 m north of the OSM outline (to Y −52.5), under the court and the south end of CSE. OSM gives CSE one underground level, and S18 says the two buildings are connected. Nothing else confirms it, but the layout follows the plan.
- **Elevators:** they sit at about (−72.6, −89.7) on every floor, doors facing south.

---

## 4. Game rules for this interior

| Rule | Value | Why |
|---|---|---|
| Plan dimensions | 1:1 map metres | project rule |
| Floor-to-floor | **6.0 m** game (real ≈ 4.2 m, estimate) | SM64 camera headroom; air above 2.3 m stacks. One backflip (4.8-6 m peak) no longer clears a floor, so routes go through stairs, shelves and the atrium. |
| Floor z (game / real) | F1 −6 / −4.2, F2 0 / 0, F3 +6 / +4.2, F4 +12 / +8.4, F5 +18 / +12.6, roof +24 / +16.8 | F2 = hub grade |
| Clear height | 5.4 m (0.6 m slab) | |
| Stack ranges | 1.2 m deep, 2.3 m tall (real 90 in); every 2nd range 3.6 m (built 3.0 m); two per 30-ft bay; aisles about 3.4 m with a column in every other aisle | single jump + ledge grab onto 2.3 m; from the 2.29 m step onto the 3.0 m top; tops wide enough to run on; book-cart bridges join the tops of a row |
| Low shelves / display cases | 1.2 m | step-ups |
| Doors | ≥ 2.0 m wide (real reading-room halls were 3 ft in 1987) | co-op traffic |
| Stairs | 30° stair halls (rise 3 m, run 5.2 m per flight); the core stair is 35° (run 4.3 m) | keep ramps under SM64's 38° slide limit; give stair ramps a not-slippery surface |
| Railings | 1.0 m on atrium balconies and terraces (1.1 m parapets) | |
| Fall damage | > 11.5 m: dropping from F4 or F5 into the atrium hurts | intended risk |
| Budgets | about 4,000 collision tris estimated (hint 7,000) | box collision for ranges and rooms |

---

## 5. Floor plans (game layout)

Each sketch draws the zones, the 30-ft column grid, ranges, stair halls (hatching = flights), elevators (a yellow E marks the out-of-order car), windows (blue), doors (orange; red = locked; green = main entrance) and mission anchors (stars). The dotted red line is the OSM footprint. Zone borders are solid for sourced/plan items, grey dashed for inferred ones and orange dashed for gameplay additions.

### Floor 1, basement: Collaboration Commons (z −6)

![Floor 1](../art/levels/marston/layout_floor1.png)

- **Commons:** a big open hall with the 21 glass group rooms around it.
  - L115-L117 sit north, in the stretch under the porch.
  - L118-L121 sit NE.
  - L122-L129 run down the east wall.
  - L130-L135 run along the south wall.
  - L136 (conference, with the visualization wall) is in the SW. [plan]
- **Study-room fronts (#38, #36):** clear glass in aluminium frames with a pale blue film band at 1.05-1.40 m, up to 2.9 m. Above that a white drywall bulkhead runs to the 5.4 m game ceiling, over the doors too, and brings the tall glass back to the photo's proportions. Each room's name is lettered on the bulkhead over its door in dark grey serif. Heisenberg, Carson and Jemison are photographed; Franklin, Curie, Darwin, Hopper and Newton fill the cycle [inferred]. White piers stand between the rooms, a small dark 'L1xx' plaque sits on the glass beside each door at about 1.5 m, and the open door leaves are honey maple. [photo]
- **Inside the rooms (#44-#46):** they alternate between lounge rooms and high-table rooms. A lounge room has the teal-blue accent across a whole side wall, a low round maple coffee table, two taupe metallic shell chairs on thin splayed legs and a slim maple side table. A high-table room has plain white walls, a counter-height maple table with a rounded end, and black Caper stools. Every room has a wall TV with its white input plate. [photo] Fix round 2 (fidelity pass, #44 #46): the shell chairs are bulky padded tub shells (a 0.13 m seat cushion and a 9 cm upholstered shell wrapped from wing tip to wing tip, its top falling from 0.90 m at the back to 0.54 m at the wings), not thin planes. The coffee table is a 0.90 m round maple disc (0.80 m in narrow rooms) on a short steel column and a round foot plate (`coffee_disc`), and the chairs sit as far apart as the room allows. The teal is a muted slate teal (`T_TEAL_ROOM`, #44 RGB 80/105/124). In the east window rooms (L122-L128) the teal is the wall that carries the window, painted round the opening, as in #44; the side walls stay white. Interior lounge rooms keep it on a side wall.
- **L136 (#47):** looking west at the twin screens (about 3.0 × 1.7 m, 0.2 m apart, bottoms at 1.0 m), the lectern with dual monitors is on the left (south) and the whiteboard is on the right (north) wall, west of the door. The projectors hang on rods of about 2 m. The 2014 tiled visualization wall (#48) is kept on the unphotographed east wall as 3 × 2 displays, about 3.0 × 1.5 m [inferred; S15 still calls the room a visualization space]. [photo] Fix round 2: the wall is on, as in #48. One bright GIS aerial image (`int_ms_gis_map`) spans the 3 × 2 grid of thin-bezel displays (2.5 cm bezels, 3.3 × 1.7 m, bottom at 0.85 m so a standing user reaches it). It used to be six dark TVs. Fix round 2 (fidelity pass, #47): the projected slide (`int_ms_projector`) is a bright pale periwinkle with a soft hot spot (about RGB 135/170/243; it was a deep royal blue that read as a sign) and a small centred white wordmark, a bold 'UF' and 'FLORIDA' in small capitals, instead of letters across the whole screen. The north whiteboard is wiped clean, as in #47.
- **Elevator lobby (#69):** on the brick west of elevator 1 (1.2 m in the plan; the photo shows about 2 m) are the white service door with its red sign and a wall clock above it. There is no big '1' over elevator 2, only the small blue sign beside its door. The wave ribbons are 1.25-1.35 m wide, have a white edge and hang in two overlapping layers of pale, unstreaked blue acrylic. [photo] Fix round 2: the core's darker bake band (negative lights) is no longer used on F1. Its south face is the lobby's wall-washed red brick, and five warm wall-washers 0.5 m off the brick at 2.8 m, plus a softer fill row, light it about as bright as in #69. The other floors keep the band. Fix round 2 (fidelity pass, #69 #39): each ribbon's cross-section is rolled 18 degrees about its length. The low edge stays at its old height and the ribbons alternately rise north and south. From the game camera, which sits at about the ribbons' own height, they now show a broad face instead of reading as thin strands. The upper layer is 0.10 m higher, so the layers never touch (minimum gap 0.11 m). The bi-level drinking fountain on the lobby's west wall is white enamel with a stainless basin and bubbler, on a white back plate; the stainless boxes did not read. A brushed stainless recycling / waste pair (blue and grey stream labels) stands right of the stanchions with its back 0.2 m off the brick at the core's SE corner, clear of elevator 2's keep-out.
- **Commons centre (#37, #36):** eight more round maple tables, each with four grey Sayl chairs (grey Y spine, as photographed), fill the gaps between the core, the lounge, the layout's table clusters and the coin lines. Four of the six centre clusters (01, 05, 06 and 09) are the grey upholstered pods of #36, and a fifth pod stands in the gap between clusters 02 and 06. The big rings use 24 segments. The blue ring by L120 sits at (−48.0, −93.8), 1 m south-west of its plan spot, to clear L120's bulkhead. [photo] Fix round 2 (fidelity pass, matched view of #37 4243): two more round tables stand in the foreground gap at (−55.2, −92.3) and (−60.5, −90.5), outside the coin ring round (−56.4, −88.0) and its keep-outs, so the ~2.5-3 m grid of the photo runs right up to the lounge. Round table tops are 16-sided (they read as decagons up close); their collision keeps its octagon. The Sayl backs are a mid grey (mesh tint 0.66, Y frame 0.38; they read nearly black from a distance, lum 31-67 against 62-111 in 4243). The ring over the bar tables (−47.25, −111.3) has a blue inner face, as in #41; it was purple.
- **West side:** the makerspace (the Act 5 Printer Jam bay, its east wall open onto the Commons) and the South Computer Lab. [plan] A full-height wall with no door separates them at Y −106.8 (X −80.2..−71.3): red brick on the makerspace face with the TV in its middle, white drywall on the lab face (plan_f1_2024; #51, #56). Light-well windows on their west wall look into a sunken planted court. [inferred/gameplay]
- **Makerspace (#51-#60):**
  - The storefront on the elevator lobby has dark-grey frames with mullions about 1.75 m apart and a transom bar at 2.4 m. The glass runs to a 3.4 m head under a white drywall bulkhead, with warm string lights along the head. Fidelity-2 fix 2 (#51 #52): the string is tied up at each mullion and at the door gap's jamb and hangs in catenary swags bay by bay (0.30 m in a 1.75 m bay, scaled with the span; `string_lights(knots=...)`).
  - The two-line yellow neon is centred on the 8.9 m front (X −75.7), over the butcher-block counter right behind the glass. Two black wire racks of small 3D printers (dark frames, lit open fronts) stand inside the glass west of it.
  - The 2.4 m door gap is at the east end of the front (#53 shows the door east of the neon). The hexagon pinboards hang on a brick pier at the front's west end (#51: from the lobby the photo's right is west).
  - The east wall to the Commons is white drywall with a black-framed clerestory band at 2.4-3.4 m (clear glass). Below it are the pegboard tool wall and a wire rack of 3D printers (#53, #58). The documented 4.8 m gameplay opening stays.
  - Fix round 2 (#51 #52 #53 #60): the storefront and the clerestory use clear glass (`int_ms_glass_clear`), so the neon and the warm room read through it. The mullions are placed (`MAKER_POSTS_X` -78.4, -76.65, -74.75) so the neon sits alone in a 1.9 m bay. The bay next to the pier holds a black-framed glass door with a push bar and a red OPEN sign, the second entrance of #51 (drawn closed; the east door gap of #53 stays the opening). The thread and ribbon spool wall and the long butcher-block sewing table with two machines stand on the west wall's north end facing east, so they show through the west bays from the lobby (#51) and run toward the glass (#60). The small 3D printers stand east of the neon counter (one wire rack between it and the door gap, one on the east wall), not in the west bays.
  - Brick is only on the south wall, with the TV and a perimeter work bench. Fidelity-2 fix 2 (#56): the TV is the bigger set of the photo, 1.8 × 1.0 m with its bottom at 2.0 m, switched on: a bright light-blue slide (`int_ms_tv_maker`, unshaded; the old 1.4 m set's dark navy wallpaper read as switched off).
  - Six butcher-block islands on grey steel frames, with bin shelves and Sayl chairs on both sides, stand in two north-south rows (#54, #56).
  - The ceiling is 2' × 4' lay-in tile with 2 × 4 lensed troffers and hanging EXIT signs. The Commons' linear LED slots stop at the room (the labs have their own, see below).
  - The layout's inferred printer benches, sewing bench and maker-books shelf are not built. The Act 4 red coin stands on the NW island (top 0.92 m). [photo]
- **South Computer Lab (#63):** two double rows of two 4-seat blocks (32 seats; the SW stair hall takes the room's west 0.7 m), grey fabric screens with frosted-glass tops, large monitors showing a blue desktop wallpaper, and dark charcoal carpet. The olive south wall is plain. [photo]
- **Computer labs, fidelity-2 fix 2 (r2_g2 review; #61-#64):**
  - **LED slots.** Three or four long, bright linear LED slots per lab are the labs' main ceiling feature in the photos, but the Commons grid never fitted a whole run inside a lab, so both labs had bare tile. Each lab now has its own parallel lines (`LAB_LED_LINES`): in the North Lab three N-S lines at X −80.55, −78.40 and −76.25 (#61 and #62 look north along them), six 6.1 m runs; in the South Lab two E-W 4.6 m runs on the Commons grid's rows Y −108.24 and −114.33 (#63 looks west), stopping 0.9 m short of the Commons runs that reach into the lab's east side. The olive rings keep their radius + 0.4 m clearance, so the middle lines break round them. A Commons run whose midpoint lies in a lab is now left to the lab lines (two such straddling runs went).
  - **Dividers.** The North Lab's screens are grey fabric only, up to 1.24 m under the aluminium cap, with no glass band (#61 and #62 show none; `lab_cubicles(band=False)`). In the South Lab the top band (and the Commons / F2 benching dividers and the 120-degree benching) is pale white-grey frosted glass (`int_ms_glass_frost`, alpha 0.72), as in #63 and #64; the streaky blue `int_glass` gave a cyan stripe on every row.
  - **Chairs.** The lab Sayls are light grey mesh on a light grey frame (`MP.LAB_CHAIR`: mesh 0.90, frame 0.70, seat 0.86), as in #61 and #63. The Commons keeps the design review's mid-grey chairs.
- **East study rooms L122-L128:** each room has an exterior window in the east wall (X −33.54, sill 0.95 m, head 2.9 m, a pier at every partition). The windows look onto a sunken planted court: lawn, three live oaks, a campus lamppost and a planted bank up to grade, open to the sky (#38 photo 4272, #44). The court's depth and planting are inferred. In these rooms the wall TV hangs on the north side wall. [photo; court inferred] Fix round 2: the panes are a pale daylit glass (`int_ms_glass_day`, alpha 0.55, drawn unshaded), so from inside a room they read about 0.76 of the white wall as in #44 and the room backs glow from the Commons as in #38. The court has its own kit group (`court`), lit with outdoor daylight rather than the basement bake. Its bank is a short steep slope at the very back (foot 2.2 m from the top), and the top moved back to X −23.6. Newell Drive's west curb (about X −22.35) stops it going deeper.
- **Ring pendants and wave ribbons:** these hang at the photographed heights on long cables from the raised 5.4 m ceiling. The ring bands are 0.28 m deep (fix round 2; #38 shows about 0.25-0.3 m on a ring of about 4.6 m, and the 0.42 m band read as a big grey drum across a third of the game camera's view) and sit 3.08-3.36 m above F1. The lower ribbon layer's low points are 3.06-3.22 m, and the upper layer now hangs 0.10 m higher than before, and each ribbon is rolled 18 degrees (see the elevator lobby). The photos show these at about 2.4-2.7 m under a ceiling of about 3 m. [photo; heights raised with the ceiling]
- **North Computer Lab:** a long room under the court with a walk-in vent duct along its west wall at z −3.4..−1.4. The duct is open at its south end through the lab / sorting-room wall (Y −74.6..−74.4). From the sorting table step (top 1.2 m) you climb 1.4 m up to the duct floor. Both long walls of the lab are white drywall (#61, #64), including the west wall of L115, and so is the lab's south end. Outside, the duct is clad as a white drywall bulkhead up to the ceiling, so the west wall reads white as in #61. Five double rows (50 PCs as in S15) have large blue-wallpaper monitors, on dark charcoal carpet. EXIT signs on F1 are white with red letters (#54, #61, #64). [plan; duct gameplay]
- **Book sorting room:** in reality a staff room. In the game the book chute from the 2nd-floor vestibule lands here. [gameplay]
- **Restrooms and vending:** the gender-inclusive restroom is in the NE corner and the men's room is south of the NE tower; supply vending stands beside them. [plan] Each block is closed but has a door on its Commons side: a wood-veneer leaf in a grey hollow-metal frame, with the dark grey ADA pictogram plaque and the blue accessibility plaque beside the latch at about 1.5 m. That wall is white; purple is the accent on the other walls (#70-#72). The gender-inclusive door is on the south face and the men's door on the west face. Fidelity-2 fix 2 (#71, view wc_gi): the leaf is the honey maple of the F1 study-room doors (it rendered dark cherry), the blue accessibility sign is a round disc on the leaf at 1.5 m (the pictogram plaque stays on the wall by the latch), two small lights in front of each door lift the white wall out of the bake's mid grey, and a 1.5 m apron of grey plank tile (`WC_TILE_PATCHES`, `int_ms_plank` tinted grey) lies in front of each door.
- **Stairs:** the NE stair hall, the west core (stair + elevators) and the SW stair (door in the west wall).

### Floor 2, entrance floor (z 0)

![Floor 2](../art/levels/marston/layout_floor2.png)

- **Porch:** a two-storey covered north porch (X −71..−52.6, Y −69..−75.5). It is outdoors and walkable, closed off by an invisible wall at −69. [plan]
- **Entrance:** the north doors lead into the vestibule and then the lobby hall. **Spawn** is in the lobby at (−67.5, −83.8), facing south toward the atrium. The return slot for Act 6 is in the vestibule's west wall; a hatch below it opens the book chute. [plan; slot gameplay]
- **Service desk:** east of the lobby, with the counter along its SW edge. Staff offices fill the north. [plan]
- **Atrium court:** the floor of the game atrium (X −65..−51.83, Y −93..−107.8). It holds:
  - the grand stair up to floor 3 along its west edge [gameplay]
  - collection highlights and new-books shelves at 1.2 m [plan]
  - four exhibit cases along its south edge [plan; moved]
  - two free-standing module columns
- **Starbucks:** on the west, with its court door (locked) and an interior door from the west aisle. [plan; the interior door is real: the Alligator (2015) says the court doors are used by day and the interior doors after sundown and on weekends]
- **Other rooms and shelves:**
  - computer lab [plan]
  - three sci-fi ranges by the south windows [plan]
  - course reserves [plan]
  - group rooms 201D-H on the east [plan]
  - the SE staff block (closed) [plan]
  - the NE hall, opened from staff space so the NE stair hall meets the floor [gameplay]
  - the SW corridor from the SW stair hall to the computer lab [gameplay]
  - receiving + the freight elevator (closed) [inferred]
- **Windows:** the north storefront and the court-side glass (both full height), the Starbucks west glass onto the arcade, and ribbon windows on the east and south walls.
- **Fidelity-3 details (photo pass):**
  - Porch (#1 #2): the storefront bays east of the doors (offices behind) are near-black glass (`int_ms_glass_black`, about RGB 28,32,36, one soft diagonal sheen per 1.25 m bay) with dark-grey mullions standing proud of the glass. The bronze box over them and the cladding above the storefront use smooth dark bronze panels with fine horizontal seams 0.6 m apart (`int_ms_copper`, redrawn; the faces tinted dark, the soffit underside left lighter, four round downlights). Black door leaves stand pinned open, square to the storefront, at each jamb of the wide door gap, with the white name vinyl (`int_ms_door_vinyl`) on the face toward the doorway [photo; the real leaves close inside the gap]. Fix round 2: the leaf glass sits 2 cm proud of the 6 cm leaf, with the vinyl 2 cm in front of it; the old 0.5 cm offsets rounded to 0 game units and z-fought. The OPEN 24 HOURS neon is centred in the transom's east bay (X −66.53..−65.2, over the east leaf as in #3), so no mullion crosses it. The backdrop ground grid is also cut on the porch's and the F2 footprint's edges. A cell is dropped whole when its centre falls inside them, and the court's split lines had shifted cells, which opened holes north of the porch, at the NE re-entrant corner and under the SW F3 overhang.
  - Lounge (#23 #24 #26 #28, fix round 2): all the lounge photos look EAST (the golden-yellow stretch beyond is the x -33.54 window wall), so the S lies across their view. Its lobes are stacked north-south on x -57 (inner radius 1.15 m, outer 1.77 m, centres 2.98 m apart, filling the 6.5 m between the Highlights / New Books shelves and the atrium's south edge). The north lobe opens west, so its orange seats face the lobby, the grand stair and the photo viewpoints; the south lobe opens east. There is a yellow ottoman in each lobe. Five orange tub chairs on the group's west side face the lobby, two more close the south lobe's east side, and there are two end tables with plants. The backs are a charcoal upholstery with a small grey diamond repeat (`int_ms_fab_dark`, redrawn).
  - Copper soffit lantern (fix round 2, #23 #24 #26 #30): it hangs low, on longer cables. The band runs 3.2-3.7 m above F2 (it was 4.3-4.8 m, out of every eye-level frame), so it fills the top of the lounge view as in the photos. Its walkable no-camera frame top (3.7 m), the `lantern_top` anchor and the coin ring moved down with it. It is reached by dropping from the F3 balcony (2.3 m down). It moved 5 cm east, so its NW copper corner box sits wholly inside the atrium pillar it meets; its face had been coplanar with the pillar's, a copper/white z-fight. Also on F3, the slab edge face under the grand stair's top riser (Y −104.9) is left to the riser, because the two were coplanar.
  - East floor (#29): the south face of the R201G/H block (Y −96.6, X −37.5..−33.5) is a solid teal wall with a 3.4 × 1.4 m wall whiteboard, meeting the golden-yellow window wall at the window band. Facing the windows from the lounge, teal is now on the left and the yellow runs south from that corner; the staff block keeps teal only in its printer bay (#28; fix round 2 below).
  - Service desk (#23): a light-grey solid-surface top (it was charcoal) with a raised transaction ledge 0.28 m deep and 0.10 m high all round the L.
- **Fidelity-3 fix round 2 (matched east views of the lounge, porch, desk, cafe):**
  - F2 ribbon windows (#25 #29): `f2_east` and `f2_south` run 1.2-4.9 m (`F2_RIBBON`; the layout's 1.0-3.6 m band left a 1.8 m golden band over the heads). The sill is over the seated heads at the round tables, as in #29, and the head meets the ceiling: the 0.5 m of wall above it is ceiling white (`F2_HEAD_WHITE`, the outline walls' `head_tint` on F2, no dark trim). The golden yellow now shows only under the glass and on the full-height corner pier at Y −105.7. [photo; the glass is taller than the real band because the game ceiling is raised]
  - Staff block (#24 #25 #28): its west face (X −46.4, square to the lounge's east views; it was the large teal plane right of the yellow wall) is white, and so is its north face (Y −105.7) except the printer bay, X −44.9..−40.6 (`STAFF_TEAL_X`), where the printer / scanner station and the How-to-Print poster stand on teal, as in #28. From the lounge the only teal is the R201G/H face, LEFT of the yellow, as in #24.
  - Porch storefront (#1 #2 #3 #4): every fixed pane on both sides of the door gap and the transom over it is the near-black `int_ms_glass_black`, one-sided toward the porch, with a clear inner pane (`int_ms_glass_clear`) 0.2 m further in, so the lobby still looks out through glass. The OPEN 24 HOURS neon stands on the porch face of the transom glass (2 cm proud), a square 0.76 m sign in the east bay, its blue now saturated (`int_ms_neon_open`, #3F6EFF). The 444 / NEWELL DRIVE vinyl sits at the top of the pane next to the brick pier, at transom level (3.22-3.77 m), on the porch face of the glass.
  - Service desk (#23): the base is the mid-grey laminate of the photo (`DESK_FRONT`, 0.64; it read white). The ring (`SERVICE_RING`) is a slimmer 0.30 m band of radius 1.55 m hung lower, 2.6-2.9 m (it was 0.46 m at 3.55-4.01 m), under the lounge lantern's 3.2-3.7 m band. `int_ms_sign_service` reads title-case "Service Desk" in black on yellow, repeated four times round (lowercase glyphs drawn on the capitals' 5 × 7 grid, so the words keep their texture widths).
  - Starbucks counter (#34 #35): it stood 0.3 m inside the storefront glass along 8.5 m and walled the cafe off from the library side. It now runs east-west in front of the slat / menu wall (X −78.0..−74.6, Y −96.0..−95.25, `PROP_MOVES`), customers on the south, its pickup end by the Order Status screen; a short counter lays its pastry case, espresso machine and pickup plate out end to end (`cafe_counter_ms`). The cove-lit soffit and its three downlights follow it. The first table pair stepped 0.6 m south. From the library (#34) the view through the door crosses open cafe floor to the court glazing. The Act 4 red coin (R7) sits over the pickup end (−77.53, −95.62); the customer point is at (−75.5, −96.92), facing north. [inferred orientation]
  - Starbucks (#34 #35): the storefront is clear glass (`int_ms_glass_clear`) with slim black mullions every ~1.5 m. The round decal is a 24-sided disc with a generic emblem. The slat wall's wood soffit runs up to the ceiling, and a warm cove-lit wood soffit with four recessed downlights hangs over the counter.
  - Science fiction stacks: mid-grey steel (0.6 grey uprights, shelves and ends), fiction spines (`int_ms_fiction`: darker mixed colours, white labels, red genre stickers), three face-out covers per range face and a SCIENCE FICTION end-panel sign (`int_ms_sign_scifi`).
  - Coffers (#23 #29, F3 computers): on F2 and F3 every other coffer carries a 2' × 4' lay-in troffer (two 2' × 2' lens panels) in one facet; F4-F5 keep the 2' × 2' panels.

### Floor 3, journals, classroom, aquarium (z +6)

![Floor 3](../art/levels/marston/layout_floor3.png)

- **Atrium balcony:** a ring with railings round the void; the top of the grand stair lands on its west side. The real 30-ft atrium cell is marked in blue on the sketch.
- **Stacks:** five periodical ranges north of the atrium and five south of it (the agriculture documents are the west end). Two theses ranges run east-west east of the atrium. [plan; ranges gameplay-spaced]
- **Around the elevators:** classroom L308 sits in front of the elevators, with the wellness room L307 beside it. The **fish tank** is across from the elevator doors (red coin R6). A data consultation room stands next to the core. [plan / inferred]
- **Wellness room L307 (#73-#75), fidelity-2 fix 2:** warm cream walls (a visual skin 1.2 cm in front of the room's own wall faces, `T_WELLNESS_CREAM`; the partitions' outer faces stay white) over the wood-look plank floor. The white sink counter (1.5 m, a solid-surface top with an inset stainless sink and gooseneck faucet on a white base cabinet, `sink_counter`) stands on the south wall with a dark navy paper-towel dispenser and a blue soap dispenser above it (#74). The tan glider with upholstered arms under wooden arm rails, on a wooden glider base (`glider_chair`), stands against the west wall facing the door, with the round white side table on dark X legs (`x_side_table`) beside it (#75). The rug is a patterned blue (`int_ms_rug_blue`: navy border, mid-blue field, light-blue trellis). Only the counter has collision.
- **Other:** a computer row and display cases west of the atrium, reading tables along the east windows, and staff space plus the zig-zag bay offices along the west (closed).
- **Windows:** north windows look over the porch roof void; the zig-zag bays face the court roof; ribbon windows run along the east and south.
- **Fidelity-4 (#76-#80):**
  - The east open study's guitar-pick tables are 1.8 m wide maple slabs on solid maple end panels, with 10 seats each (#76).
  - L308 (#78) has a dropped 2' x 4' tile ceiling at 3.5 m with lensed troffers. Its three displays fill the west wall at head height (bottoms 1.2 m; 1.6, 1.6 and 2.1 m wide). The training tables stand on chunky grey pedestals, and its wood door stands open into the room.
  - The data room (#77) has a maple desk with a big monitor and a Sayl chair on each side of the east door, set against the door wall and facing into the room (before, there was one desk on the south wall). The door has a grey hollow-metal casing (`thin_partition(casing=...)`), and its white leaf, with a tall narrow vision panel, stands open into the room. The passage from the core stair's west door to the east door stays open between the desks.
  - The fish tank (#79 #80) is built in depth behind clear glass: a densely planted back, two layers of plant fronds, black rock, driftwood, gravel and three large rainbowfish per side, plus a frosted engraved plaque. Its lid (red coin R6) is unchanged.
  - The bound journals (int_ms_bound) are deep red, maroon, teal, tan, navy and black with gilt bands and lettering (#83 #87).
- **Fidelity-4 fix round 2 (r2_g4 review):**
  - L308's tile ceiling now reads white (#78). It was one big quad, shaded only at the room corners and darkened by the underside AO (0.72), so it read mid-grey: ceiling/wall 0.52 in g4_L308, against 0.78 in the photo. It is now a grid of about 1.2 m cells with full AO. The lensed troffers' lights, 0.6 m below, light it, and the tint `L308_CEIL_TINT` (0.73, 0.74, 0.77) brings the ratio to 0.80.
  - L308's chairs are a muted plum-grey, `T_PLUM` (0.42, 0.31, 0.37); the photo measures 92/68/78. The old value read raspberry.
  - The theses ranges have light-grey steel end panels (0.94, 0.95, 1.0); the photo measures 179/177/183. The coral belongs to the periodicals only. `int_ms_theses` is now near-black slate/navy-green bindings (the photos' dark pixels measure about 42-55, 44-57, 46-58) with a 2-texel white call-number label on each spine and no gilt band.
  - The fish tank is dark and dense, as in #79 #80 (the plaque photo averages lum ~28):
    - `int_ms_aquarium` has darker water and plants. The glowing back, the water tint on the glass, the gravel, the rock (black, 0.17) and the fronds (deep greens) are all darker. In g4_fish the tank's centre went from lum 86 to 50.
    - Two of the three rainbowfish on each side are orange-red with yellow-orange tails; one is blue-and-yellow. All three have a taller, rounded hexagon body.
    - The frosted plaque carries four dark engraved lines.
    - A tall potted floor plant (`floor_plant`, a charcoal planter, collision on the pot only) stands on the tank's east side. The west one is refused by the keep-out round the point at (-75.8, -95.85), so there is one plant.

### Floor 4, quiet floor, books A-Z (z +12)

![Floor 4](../art/levels/marston/layout_floor4.png)

- **Stacks:** three A-QC ranges north of the atrium, with every second one 3.6 m tall (red coin R1 on top). West of the atrium are two QC-Z ranges plus the oversize range. [plan]
- **Moved stacks:** the QC-Z ranges the game atrium displaces move to a new band of five ranges on the south. [gameplay]
- **Quiet study:** carrel rows along the east band, using the 2022 furniture with power. [plan / inferred]
  - Fidelity-4 (#97 #98): the perforated panels are 1.5 m between every carrel, and every other carrel has an overhead perforated shelf. The rows stop 1.2 m short of the east glass. A counter-height maple window bar with black stools on the room side runs along the glass in ten segments of about 3 m, in two runs either side of the east terrace door. No hanging QUIET signs (no F4 photo shows one).
- **Computers:** along the west wing's north wall. [plan]
- **Terraces:** doors open onto the east terrace (X −42.6..−33.54) and the south terrace (Y −115.9..−125), both at z 12. They are walkable outdoor decks with 1.1 m parapets. [gameplay; the setbacks are plan]
  - Fidelity-4 fix round 2 (g4_f4_carrels_b, lakitu_f4): the terrace doors read as unglazed 2.4 m holes in the ribbon glazing, which #97 #98 show continuous. Every terrace door (F4 east and south, F5 south; `terrace_doors`) now sits in the glazing:
    - a black mullion of 0.08 m (`TERRACE_DOOR_MULLION`; it was 0.3 m of white wall) on each side;
    - a black 0.10 m transom bar (`TERRACE_TRANSOM_BAR`) with glass above it, up to the band's head;
    - a pair of black-framed glass leaves (`storefront_leaf`: stiles, rails, a push bar on each face), swung 170 degrees outward so they lie almost flat against the outside glazing.
    - The leaves are visual only. The gameplay gap and its collision are unchanged.
- **Atrium chandelier:** a ring light hangs in the atrium with its top at z 15; reach it by long jump from this balcony. [gameplay]

### Floor 5, silent floor, reading rooms with a view (z +18)

![Floor 5](../art/levels/marston/layout_floor5.png)

- **Reading rooms:** an L-shaped silent floor round the atrium's top storey: the north reading room and the west reading room with carrel rows. The atrium's east and south sides here are the building's own exterior glass, which looks down the terraces.
- **North view windows:** these face Century Tower (bearing 31°, 114 m), the Auditorium and Turlington. The Act 1 star sits over the reading tables there, and the window counter runs along the glass. [plan / inferred]
- **West window desk:** the Act 2 goal; Shusher loops run between the carrel rows. [gameplay]
- **Lounge (fidelity-4, #100 #102):** in the north room's south strip, three clusters of three grey geometric cubes are angled round a maple side block between the two felt pods. The slate blue-grey seats (fix round 2) face the room (S, SW, SE), with their backs to the carrels and windows. All of it stays clear of the Shushers' loop (y −90.5).
- **Ribbon windows (fidelity-4, F3-F5, #76 #97 #100 #104):** the bands run from the sill (0.9-1.0 m) to a 2.6 m head. They have black mullions every 1.25 m and the deep white sill. The Century Tower view still reads through them. Fix round 2: the wide photos (#97, #104, f3_open_study_windows) show the heads right under a white ceiling soffit, so the 2.8 m dark grey band is gone. Only a 0.28 m dark head trim remains, the wall above it is ceiling white, and a white down-facing soffit (`int_ms_coffer`, visual only) runs 1.3 m deep at 3.0 m along every windowed F3-F5 wall. The piers keep their grey and the mullions stay black. A camera above 3 m sees the white wall, because the soffit is back-face culled.
- **Lounge cushions (fidelity-4 fix round 2):** `T_BLUE_CUSHION` is a dusty slate blue-grey (0.36, 0.45, 0.50). The photos (#100 #102) measure 64-74, 82-90, 86-94; the old 0.22/0.55/0.68 read saturated teal (43/97/109 in cu_cube2).
- **Upper terraces:** at z 18, reached from the NE stair hall (east) and through a south door. Red coin R8 is on the east terrace. [gameplay]

### Roof (z +24, gameplay)

The roof is a flat deck with a 1.0 m parapet and the atrium skylight (hipped glass, ridge z 27) in its SE corner. The NE and SW towers rise 5.7 m above it. The NE stair hall reaches the roof.

Design fix round 2 (s3_roof): the deck and the tower tops are a grey single-ply membrane, `int_ms_roof_membrane` (2 m tile, 16 texels/m, a welded lap seam with its shadow line and staggered end laps; `roof_gravel`'s 32 px over 4 m read as a blurry flat plate from Mario's camera). Between the roof coin ring (−61, −82; r 3 m) and the NE AC steps there are three low climbable pieces, all at least 3.6 m from the ring's centre and camera-transparent (COL_NOCAM): an exhaust-fan curb (X −62.2..−61.0, Y −77.6..−76.4, 0.45 m) carrying a louvred fan housing (to 0.95 m), a roof-hatch curb (X −58.6..−57.2, Y −78.6..−77.4, 0.40 m) and a 0.70 m duct run with standing seams (X −61.8..−59.4, Y −74.0..−73.2) 0.6 m short of the first 1.4 m AC step, so the climb to the NE tower starts 0.7 → 1.4 → 2.8 → 4.2 m.

---

## 6. Vertical circulation

| Id | Where (map m) | Floors | Real | Game |
|---|---|---|---|---|
| `stair_ne` | NE tower X −52.6..−39.6, Y −67.4..−79.0 | F1-F5 (+roof) | stairwell + exit + restrooms on every floor (S2-S7) | switchback, flights run N-S. Two 5.85 m lanes (X −52.25..−46.4 and −45.8..−39.95). Floor landing on the south, turn landing on the north, 30°. Doors on the south face at X −52.3..−49.7 (F1-F4); on F5 the door is in the west face, plus a terrace door; roof door. Restrooms dropped. |
| `stair_sw` | SW tower X −90.82..−79.46, Y −107.8..−118.95 | F1-F5 | stairwell + exit on every floor (S2-S6) | switchback, flights run E-W. Two 4.95 m lanes, floor landing on the east, 30°. Doors: east face (F1-F3), north face (F4-F5). |
| `core` | X −77.8..−69.7, Y −83.2..−90.6 | F1-F5 | stair + exit + elevators at the court corner (S2-S6) | steep secondary stair, 35°, with 2.2 m lanes and its door to the east. Elevators 1 and 2 are 2.7 × 2.4 m with doors on the south. Elevator 1 is OUT OF ORDER in Act 1: doors stuck open, no car, a wall-kick shaft F2→F5. |
| `freight_elevator` | X −76.8..−73.8, Y −115.9..−112.9 | F2-F4 | a receiving room led to a freight elevator (S10); loading dock at the south notch (S19) | closed shaft; position inferred. It does not reach F1: plan_f1_2024 and #63 show the South Computer Lab as a clear rectangle there |
| `atrium` | game X −65.0..−51.83, Y −107.8..−93.0; real cell X −60.97..−51.83, Y −106.71..−97.57 | floor F2, open through F3-F5 | two storeys, 30 ft (S10) | 13.2 × 14.8 m, 24 m tall, skylight. Two free-standing module columns inside. |
| `grand_stair` | X −65.0..−61.5, Y −94.5 → −104.9, landing to −107.8 | F2→F3 | the central stair drawn by the architect and cut in 1987 (S10) | straight 3.5 m stair, 30° |
| `book_chute` | from the vestibule (−69.6, −77.2, z 0.8) to the sorting room (−80.0, −77.2, z −6.0) | F2→F1 | none | slide, 1.6 m wide, 33°; red coin R5 (as built: a 1.2 × 1.6 m hatch in the F2 floor at (−71.0..−69.8, −78.0..−76.4) over a 24° slide from z −2.0 at x −69.85 to z −6.0 at x −78.8, so it clears the F2 slab's underside by 1.9 m; see `tools/campus/interiors/marston.py` `CHUTE`) |


**Floor identity (design fix round 2; g6-g8 and s1_ne_stair read alike from the game camera).** Each floor has a wayfinding colour, `FLOOR_STRIPE` in marston.py: F1 olive (the Commons accent), F2 teal (the accent walls, #24 #29), F3 coral and F4 steel blue (the stack end panels, #83 #91 / #84-#86), F5 purple (the floor's accent). The tower walls keep the pastel `wall_tint`.
- NE stair hall: on each floor's landing wall (Y −79.0, X −43.3..−41.5, the east lane the arriving flight walks down, 0.3 m clear of the F5 door) a full-height stripe in the floor's colour with a 1.1 m floor number (`K.floor_sign`) at 1.5-2.6 m; the old 0.7 m sign at X −45 hung half over the F5 doorway. On the north wall over each half landing (Y −67.4, X −50.4..−48.6, the west lane the climbing flight faces) the same stripe from the half landing to the next slab, with the number at 4.3-5.4 m above the floor.
- SW stair hall: the same stripe behind a 0.9 m number on the landing's south wall (X −82.2..−80.6), and on F1-F4 the stripe and a 1.1 m number on the west wall over the half landing (X −90.82, Y −117.2..−115.4, the south lane the climbing flight faces).
- Core, F2-F5: a 0.9 m floor number beside the core stair door (east outer face X −69.39, Y −87.75..−86.85, 1.45-2.35 m) and one on the elevator block's brick toward the atrium (the east filler, X −70.70..−69.80 at Y −90.61, 1.5-2.4 m). Not on F1: #37 (4243) shows its brick core with no sign, and the lobby face has only the small blue sign by elevator 2 (#69).
- The F4 end panels stay the photographed steel blue (T_STEEL_BLUE 0.60/0.70/0.82): the blue pixels of #84-#86 measure (145, 162, 181), (158, 173, 188) and (129, 147, 166), already less saturated than the game's, so a bluer panel would contradict the photos. The F3 coral reads from the balconies (f3 renders).

---

## 7. Sections

![Sections](../art/levels/marston/layout_section.png)

The same stacking in text, for a terminal (north is right; the atrium sits roughly in the middle):

```
 z (game) south north
  +27 /\ skylight
  +24 +--(roof)---+---------+ +----------------------+..
  +18 | terrace | F5 |AT| F5 silent reading |
  +12 |terr.| F4 quiet / stacks |RI| F4 A-QC stacks | <- F4/F5 overhang
   +6 | F3 journals, aquarium |UM| F3 | porch | the porch
    0 | F2 sci-fi, comp lab | | desk, lobby | doors -> north porch
   -6 | F1 Collaboration Commons (basement) |
```

---

## 8. Mission anchors

These are anchors for docs/game_design.md §7.3. The design act numbers are listed; the course act order (solo acts first, co-op last, no gaps) is the mission author's call. Heights are the floor (Mario's feet) plus the offset shown, and all are in the JSON under `missions`.

| Anchor | Floor | Map (x, y) | z game | Game (X, Y, Z) | Note |
|---|---|---|---|---|---|
| spawn (0x0A) | F2 | (−67.5, −83.8) | 0 | (−790, 0, −1510) | lobby, facing south (yaw 0x0000) |
| A1 star | F5 | (−62.5, −73.0) | 19.2 | (−290, 1920, −2590) | over the north reading tables |
| A2 start / goal | F5 | (−54.0, −77.5) / (−87.2, −99.0) | 18 | (560, 1800, −2140) / (−2760, 1800, 10) | NE stair door → west window desk |
| A3 K1 | F1 | (−40.0, −114.2) | −6 | (1960, −600, 1530) | outside star room L129 |
| A3 K2 | F2 | (−56.0, −94.2) | 0 | (360, 0, −470) | atrium court, tip of the service desk |
| A3 K3 | F3 | (−72.6, −93.2) | 6 | (−1300, 600, −570) | elevator lobby, by the fish tank |
| A3 K4 | F5 | (−85.0, −91.0) | 18 | (−2540, 1800, −790) | west wing, by the computers |
| A3 star | F1 | (−35.5, −121.9) | −5 | (2410, −500, 2300) | inside glass room L129 |
| A4 R1-R8 | F4, F1, F1, F4, F1, F3, F2, F5 | see JSON | | | range top, 3D printer (now on the NW makerspace island, top 0.92 m), vent duct, chandelier, book chute, fish tank lid, Starbucks counter, upper terrace |
| A5 arena | F1 | X −80.2..−56.0, Y −115.4..−96.8 | −6 | | makerspace + west Commons; gantry rail at z −1.4. The makerspace / South Lab wall at Y −106.8 (X −80.2..−71.3) now closes the arena's SW corner (the South Lab is reached through the Commons). The ring at (−56.4, −102.15) hangs 3.08-3.36 m up, below the rail; its west band edge (X −58.7) sits under the rail's east end (X −58.0), so keep a print head's travel at X ≤ −59.2 |
| A6 book / slot | F5 / F2 | (−63.0, −83.0) / (−69.2, −77.2) | 18.8 / 1.0 | (−340, 1880, −1590) / (−960, 100, −2170) | throw it down the atrium |

Act notes:

- **Act 1 (Out-of-Order Elevator):**
  - The JSON lists three book-cart tracks (F2 floor, F3 N-S across the void, F4 W-E across the void), the chandelier and two falling-encyclopedia spots.
  - Block the stair doors on F2/F3 with act-masked barriers marked "closed for renovation"; floors 3-5 really were closed for months in 2022 (S13).
- **Act 2 (Quiet Floor):** floor 5 is the real silent floor. The carrel rows and the core give cover, and the JSON has three patrol loops.
- **Act 3 (Group Study Room Booking):**
  - Kiosk sets by player count: K1+K4 for 2 players, K1+K3+K4 for 3, all four for 4.
  - Every kiosk pair is at least two floors apart, or at least 30 m of running plus a stair.

---

## 9. Outside the windows

Window bands per floor are in the JSON (`windows`: endpoints, sill/head height, facing, view). The interior shell needs a simple backdrop at these places (bearing from the stage centre):

| Near (scale vertically ×1.43 with the floors) | Far (true height) |
|---|---|
| CSE building (313°, wraps the court on the NW, 22 m) | Century Tower (31°, 114 m, 47.9 m tall), the 5th-floor view |
| court glass space-frame roof (315°, from 10 m) | University Auditorium (37°, 160 m) |
| the French Fries sculpture (275°, 39 m) | Music Building (72°, 102 m) |
| Marston Courtyard planters and oaks (260°) | Turlington Hall (342°, 126 m), Rolfs Hall, Newell Hall |
| the north entry plaza with brick planters (hub planters at (−53.5, −64.2), (−63.5, −64.2)) | Rinker Hall (146°), FSHN (201°), Aquatic Food Pilot Plant (188°), Dairy Pond (232°, water), The Hub (284°) |
| the terraces themselves (z 12 and 18) | |

The hub already models most of these. A low-poly ring baked from the hub (the finale's approach in stages.json) would also work.

Fidelity-4 fix round 2 (f3_open_study_windows_2020): in the photo, the F3 east windows look into tree canopy at eye level. The render instead looked down on a lawn and brick buildings beyond. The changes:
- The OSM oak row along Newell Drive's east side (`EAST_OAKS`, x −17..−9, y −128..−82) is drawn as mature live oaks (scale 1.75-2.05: canopy 5.3-13 m up, about 7 m radius, reaching over the drive). They draw from their own rng, so every other tree is unchanged.
- Two more such oaks stand at (−14.2, −134) and (−14.0, −143).
- Two lines of trunkless canopy masses, 5.2-12.8 m up at x ≈ −17 and −12 from y −146 to −84, fill the gap between the oaks' tiers. They stay at least 2 m east of the east court's bank top.
- In g4_open_study3, the left (east) window band went from brick and lawn to canopy: 0 brick-red pixels.

Fidelity-4 (#99 #104): from the F4/F5 north windows, the plaza reads as one lumpy, dark-green oak canopy. Trunkless canopy masses 7-14 m high on a 6 m grid fill the gaps between the oaks, over the walks too, so only a few slivers of walk show. They stay clear of the tower, the other buildings, the library and the entry plaza. Their positions are inferred.

---

## 10. Materials and light

- **Shell:**
  - brick_red / brick_dark on the exterior, towers and interior feature walls
  - bronze fascias and piers (photos)
  - window_glass, white_trim, concrete
  - *New textures needed:* carpet (tinted per floor), wood shelving, ceiling tile (`make_textures.py`, not done here).
- **Floor accents:** each floor had its own accent colour in 1987 (S10). The photos show some of today's: floor 2 is teal-blue and golden yellow (photos #24, #29; not UF orange), floor 3's stack ends are coral (#83, #91) and floor 4's steel blue (#84-#86). The original game picks (F1 lime, F2 UF orange, F3 coral, F4 sky blue, F5 violet, from the plan legends) were corrected to the photos in the Marston upgrade (`marston.py` NOTES `sourced_now`). [sourced for F2-F4; F1 and F5 gameplay]
- **Vertex-colour lighting:**
  - cool daylight within 3 m of windows
  - warm interior
  - darker stack aisles with lighter range tops
  - a bright atrium fading down from the skylight
  - a cooler basement with warmly lit glass study rooms
  - full daylight on the terraces

  The JSON gives RGB factors for each (`materials_and_light`).

  Design fix round 1 (the bake read flat edge to edge): about 5 % less ambient; a stronger, shorter daylight band at the windows (bake lights 1.2 m in, every 2.5 m, radius 4.6 m); a warm pool on the floor under each F1 ring pendant; a darker band round the brick core on every floor (negative bake lights 1.2 m off its faces); a brighter atrium shaft.
- **Copper (design fix round 1):** `int_ms_copper` is now flat copper panels, one 1.2 m panel per tile with a thin two-pixel joint, no grain (the 0.6 m seams read as stained boards). The F2 atrium bulkhead, the lantern's corner and mid-side blocks, the F2 column caps and the bulkhead over the service desk use it untinted (#24); the porch box and soffit tint it back to the darker fidelity-3 bronze (`PORCH_BRONZE`, `PORCH_SOFFIT`).
- **Stack end panels (design fix round 1):** one slim 0.30 × 0.08 m label strip near the top (0.88 h) of each end of a range's tall section, none on the climbing steps (#83-#86); the two 0.24 m squares per end read as pairs of eyes.
- **Design fix round 2 (gameplay camera):**
  - Chairs: the default Sayl mesh is 0.92 (0.66 before; texel mean 0.57, so it read near-black under the vertex shade in p_f4_carrels and the commons) and the Y spine 0.64, about 0.1 darker in the render (#97 shows mid-grey mesh). The lab chairs (`LAB_CHAIR`) are unchanged.
  - No-mip shimmer: `int_ms_pegboard` holes on a 4 px pitch at half the contrast (1 px every 2 px before); `int_ms_fab_dark` diamonds, dots and weave at about half the contrast; `int_ms_mesh` lattice at half the contrast about the same mean (146).
  - F1 ring pendants: the top face of each band is the ring's inner colour, lit, inside a 2.5 cm aluminium lip. A readability cheat: Lakitu sits at about 3.6 m, just over the 3.08-3.36 m band, and saw a plain metal tray with the purple / blue / olive only as a thin far-side line. The height stays the photographed one (a ring hid Mario in 3.1 % of 2,528 camera samples near the rings).
  - Z-fighting (stats.coplanar_overlap 2.85 m² / 133 pairs → 2.34 m² / 131): no teal accent on a glass room's glazed wall (R201D's west wall at X −47.45 had an opaque teal face 3 cm inside the glass, see-through from the west and coplanar with the mullions, 0.38 m²); the F2 staff-room clock face 1 cm off its rim (0.14 m²); the porch newspaper box's window and label 1.2 cm off its front (0.11 m²).
  - Vent-duct breadcrumb (s2_duct_find, where the camera pulls in to 1.5 m): one coin on the sorting-table step top and one in the duct mouth, so the route reads from the North Lab doorway (coins 188 → 190).
- **Chairs (design fix round 1):** the Sayl task chairs have a charcoal mesh back (0.42) with a dark grey Y (0.22), as in #36 and #100; the Starbucks tables have wood-and-black-steel cafe chairs. (Fix round 2 lifted them to 0.66 / 0.38. Fidelity-2 fix 2: the computer labs' chairs are light grey, `MP.LAB_CHAIR`, as in #61 and #63.)

---

## 11. Deviations from 1:1

| What | Real | Game | Why |
|---|---|---|---|
| Floor-to-floor | ≈ 4.2 m (estimate) | 6.0 m, 5.4 m clear | camera, stacks, jump heights |
| Atrium | one 9.14 m cell, floors 2-3 | 13.2 × 14.8 m, F2 → roof skylight (24 m) | central void, castle-hall moment, Act 1/6 routes; echoes the architect's three-storey design |
| Grand stair | drawn in 1987, removed before building | straight stair F2→F3 on the atrium's west edge | readable main route; sourced intent |
| F4 QC-Z stacks | one block X −77.8..−50.2 | west part kept, the rest moved south | the atrium takes the block's middle |
| Ranges and aisles | ~0.6 m deep, ~1 m aisles | 1.2 m deep, ~3.4 m aisles, two per bay; zones on F3/F4 stretched up to 2.6 m east | running on tops, camera |
| Doors, halls | 3-ft halls and doors (1987) | ≥ 2.0 m doors, ≥ 3 m halls (2.2 m core stair lanes) | co-op, camera |
| NE / SW towers | stair + restrooms / stair + staff | whole towers become stair halls | 6 m storeys need room |
| Terraces, roof | roofs, access unknown | walkable decks at z 12 and 18; roof deck at z 24 | outdoor views, coins |
| Staff spaces | NE offices, SW receiving corridor, F1 NW staff room | NE hall, SW corridor, book sorting room | connect the stairs; chute gag |
| Exhibit cases, highlights shelf | 2×2 cases in the lobby; shelf 3.3 m further west | cases along the atrium's south edge; shelf moved east | clear the lobby and the grand stair |
| Basement windows | photographed in the east study rooms (#38, #44) | light-well windows on the west; east windows in L122-L128 onto a sunken planted court (court inferred) | daylight on F1 |
| F1 ring pendants, wave ribbons | about 2.4-2.7 m up under a ~3 m ceiling | ring bands 3.08-3.36 m and ribbon low points from 3.06 m up under the 5.4 m game ceiling, on long cables | keep them in view with the raised ceiling |
| Window bands | narrow ribbons under a white ceiling soffit | F3-F5: sill 0.9-1.0 m, head 2.6 m, a 0.28 m dark head trim, white wall above and a white soffit 1.3 m deep at 3.0 m (fix round 2; the layout JSON keeps the old 3.6-4.4 m heads, WINDOW_OVERRIDES). F2 east / south: sill 1.2 m, head 4.9 m, ceiling white above (fidelity-3 fix round 2, #25 #29: the head meets the ceiling, the yellow is under the glass) | photo proportions; the 5.4 m game ceiling is kept for the camera |
| Terrace doors | no door photographed; the ribbon glazing is continuous (#97 #98) | 2.4 m door gaps in the glazing with a black transom bar, glass transom and 0.08 m mullions, and two glass leaves pinned open outward against the glazing (fix round 2 fidelity-4) | walkable terraces (gameplay) |
| L308 ceiling | 2' x 4' tile at ~2.9 m | dropped tile ceiling at 3.5 m inside L308 only (visual, no collision) | displays at head height read as in #78; the camera still fits |
| F1 study-room fronts | glass to a ~2.9 m bulkhead under a ~3 m ceiling | glass to 2.9 m, white bulkhead to the 5.4 m game ceiling | photo proportions under the raised ceiling |
| Makerspace storefront and east wall | glass and clerestory up to a ~3 m tile ceiling; one door leaf | glass to 3.4 m (transom 2.4 m) and a clerestory at 2.4-3.4 m under white drywall up to 5.4 m; 2.4 m door gap; 4.8 m east opening | photo proportions under the raised ceiling; co-op, Act 5 |
| North entrance door leaves | four black leaves that close inside the storefront line | two leaves pinned open, square to the storefront, at the jambs of the wide (documented) door gap, with the name vinyl | keeps the co-op doorway open while showing the black leaves and vinyl (#1) |
| Invented objects | none of these exist | book chute, vent duct, chandelier, book carts, kiosks, Shushers, printer gantry, falling encyclopedias | mission devices (§7.3) |
| Book-cart bridges | none (#83-#93) | 0.45 m deep open steel grates (`int_rail_bars` deck) between the tops at the climbing ends of F3 / F4 rows (design fix round 1; were 0.8 m dark-wood boards) | a walkable route over the tops that does not hide Mario entering an aisle |
| Camera cutaways | n/a | the vent duct has no outer top face, and the wall over its mouth has only its lab-side face and lets the camera through (sorting-room side, not photographed) | the camera following Mario into the duct sees in (N64 cutaway) |
| Floor colours in the stair halls and on the core | not photographed | a full-height floor-colour stripe and a big floor number on the landing and half-landing walls of both stair halls; floor numbers by the core stair door and on the elevator block toward the atrium (F2-F5) | floor identity from the game camera (F3-F5 look alike) |
| F1 ring pendant tops | plain aluminium, never seen | the inner colour, lit, inside a 2.5 cm metal lip | the game camera looks down on the band |
| Roof | not photographed | grey seamed membrane, three low curbs / a duct between the coin ring and the AC steps | texel density and a stepping route |
| Wayfinding | EXIT signs over the stair doors | EXIT signs also over the SW tower door on F1-F5 and both F5 NE hall doors; a hanging 'STAIRS 4 5' sign over the top of the grand stair (F3), arrow west to the SW tower door 16 m away (the NE hall is ~35 m round the void) | the grand stair ends at F3; F4 / F5 are only reached by the towers and the core |
| F2 lantern top, roof steps, F5 | n/a | the lantern's frame top is walkable (a drop from the F3 balcony, 2.3 m down since fix round 2) with a hidden ring of 8 coins; a coin on each rooftop AC step and a 1-up on the SW tower top; F5 gains a coin line east of the void and a Goomba west of it | secrets, a climb on the bare roof, a less empty silent floor |

---

## 12. For the hub owner (not done here)

- **Door position:** the real main doors are at X −69.2..−65.2, in a wall recessed to Y −75.5 under a two-storey porch. Hub door 4 is at (−58.5, −69.0). Moving it 8.7 m west and recessing it is optional and would change flow.md §4.1.
- **Terraces:** the plans put the terraces on the **south-east**. The hub model instead steps the north wing back 1.2 m per floor and keeps a flat 16.8 m roof over the SE.
- **Recessed ground floors:** floors 2-3 are recessed about 6.5 m on the north wing, making a two-storey porch. The hub only has a one-storey colonnade on the west.
- **Zig-zag bays:** the zig-zag glass bays face the court, stacked over the court doors (photo S20).

---

## 13. Open questions

- **Floor-to-floor height:** the real height is unknown. 4.2 m is assumed, but 4.5 m is also common for 1980s libraries with compact shelving.
- **West grade:** is the basement at grade on the west? Evidence:
  - the floor-1 plan shows three west exits
  - OSM tags vending machines at level −1 near the French Fries
  - the Marston Courtyard's radial steps lead down toward the building
- **Terraces:** do the SE terraces carry planting or sloped glass, and can anyone walk on them?
- **Elevators:** the plans draw one elevator symbol per floor. Floor 1 is confirmed: its lobby has two stainless cars in a red brick wall (photo #69); two cars are assumed on the other floors.
- **Unplaced items:** the data consultation room on floor 3 and the real accent colours.
- **North Lab:** does the North Computer Lab really run under CSE? Only the floor-1 plan shows it.
- **Makerspace corridor carpet (#57):** the corridor beside the makerspace glass in #57 has a dark charcoal carpet with light flecks and no hexagon ottomans, where the model's lobby and west passage use the purple Commons carpet. Where #57 was taken is uncertain (it could be the light-well side), so the carpet is unchanged (r2_g2 review, low confidence).

### Open after review round 3 ( final integration)

Six reviewers scored the final build (out of 10): fidelity-1 7, fidelity-2 7.5, fidelity-3 6.5, fidelity-4 7, design 7.5, technical 8 (round 1: 5, 5, 6, 6, 7, 7). Their blocking items below were not fixed; the build in `mods/sgl64/levels/ccm` is the final source, rebuilt byte-identical. Photo | render pairs of 12 spaces: `art/levels/marston/compare/FINAL_sheet.jpg` (local only).

- **F1 lounge group (#38 4272, #41):** the S banquettes, the blue-faced ring and the maple bar tables stand apart (rings 8-9 m from the S, bar tables about 6 m south, the `commons_tables_09` pod in front). Suggested: ring (−47.25, −111.3) to about (−44.5, −106.0), the S about 2 m south, 3-4 bar tables east and south-east of it, the pod cleared, two white shell chairs.
- **F1 elevator lobby, west side (#69 4317):** the passage between the exterior wall (x −80.2) and the core (x −77.8) is open and ends in white and yellow walls; the photo shows a black-mullion glazed partition with a glass door and an EXIT sign at about y −91.0, brick behind.
- **North Lab benching (#64):** `MP.white_benching_120` exists but is never placed; the foreground of #64 is two or more white 120° pods. Suggested: replace the southmost double row at y −70.4 with two pods at about (−79.5, −71.9) and (−75.2, −71.9), keeping the aisle x −77.85..−76.15 clear.
- **Copper soffit lantern (#24-#26):** it is centred on the atrium (−58.17, −100.4) over the Collection Highlights shelves; the S group sits 1.4 m south of it. Move it about 4.2 m south (with its frame top, `lantern_top` anchor and coin ring) or swap the S and the shelves.
- **F3 open-study east windows (#75):** the band reads dark teal (window / wall about 0.42 matched, 0.65 from the game camera; photo 1.0-1.2): streaky `int_glass` in front of dark canopy masses. Clear daylight glass and sunlit, lower canopies, with sky in the upper third.
- **Terrace door bays (F4 east and south, F5 south):** the wall over each door gap keeps the grey pier tint, and `terrace_doors()` takes the layout's raw `head_m` 3.6 instead of `RIBBON_HEAD` 2.6, so the black mullions run 1 m above the glass (and up the brick outside).
- **F2 drinking fountain (`fountain_f2`, inferred):** a wall-mounted prop placed in the open floor at (−52.3, −101.9), with no wall behind it and no collision: it floats, its plate is culled from the east, and Mario walks through it. Mount it on a wall (the staff block's west face at x −46.4) with a no-camera box, or drop it.
- **Gameplay note:** the F5 Goomba west of the atrium (design fix) is in every act, so it shares the silent floor with act 2's librarians.

---

## 14. JSON quick reference

- **Top-level:** `floors[]` (F1-F5), `roof`, `vertical[]`, `missions`, `exterior`, `entrance`, `building`, `footprint`, `scale` (module grid, vertical factor), `plan_fit`, `materials_and_light`, `budgets`, `deviations`, `hub_followups`, `open_questions`, `sources`, `validation_warnings` (empty).
- **Each floor:**
  - `z_game_m`, `z_real_est_m`, `clear_height_game_m`, `noise`, `accent`
  - `outline_m` (the enclosed floor, CCW) and `outline_area_m2`
  - `default_zone`: what the unlisted open floor is
  - `zones[]` (`poly_m`, `type`, `walkable`, `enclosure`, `source`, `refs`)
  - `props[]` (`poly_m` or `pos_m`, `height_m`, `type`)
  - `openings[]` (door segments with `facing_deg`; stair-hall doors are under `vertical[].game.doors`)
  - `windows[]`, `columns_m[]`
- **Zone types:** `collab_open`, `open_floor`, `lobby`, `vestibule`, `service_desk`, `cafe`, `computer_lab`, `group_study`, `conference`, `makerspace`, `classroom`, `wellness`, `data_room`, `stacks`, `reading_quiet`, `reading_silent`, `atrium_floor`, `atrium_void`, `staff`, `restroom`, `sorting_room`, `porch`, `porch_void`, `terrace`, `roof_deck`.
  - Not walkable: `staff`, `restroom`, `atrium_void` and `porch_void`.
  - Outdoors: `porch`, `terrace` and `roof_deck`.
- **Prop types:** `range` (with `height_m`), `shelf_low`, `display_case`, `counter`, `table_cluster`, `computer_row`, `carrel_row`, `window_desk`, `aquarium`, `printer_3d`, `workbench`, `visualization_wall`, `vending_machine`, `book_return`, `book_return_slot`, `duct`, `pier`, `printer`, `wall_sign`, `drinking_fountain`, `skylight`.
- **Validation:** the JSON was checked when written:
  - zones lie inside their floor outline (outdoor zones excepted)
  - closed zones and cores don't overlap
  - props don't poke into rooms
  - ranges keep their aisles
  - columns miss props
  - mission points stand on walkable floor
  - stair slopes are under 38°
  - every coordinate fits in s16

---

## Sources

- **S1** UF Libraries, Marston Location & Floorplans:https://marston.uflib.ufl.edu/spaces/location-floorplans/
- **S2** Floorplan: 1st Floor (page + plan image, 2024-10): https://marston.uflib.ufl.edu/spaces/location-floorplans/floorplan-1st-floor
- **S3** Floorplan: 2nd Floor (page + plan image "2nd Floor MSL", 2024-10): https://marston.uflib.ufl.edu/spaces/location-floorplans/floorplan-2nd-floor/
- **S4** Floorplan: 3rd Floor (page + plan image, 2023-06): https://marston.uflib.ufl.edu/spaces/location-floorplans/floorplan-3rd-floor/
- **S5** Floorplan: 4th Floor: https://marston.uflib.ufl.edu/spaces/location-floorplans/floorplan-4th-floor/
- **S6** Floorplan: 5th Floor: https://marston.uflib.ufl.edu/spaces/location-floorplans/floorplan-5th-floor/
- **S7** Marston study guide, Spaces: https://marston.uflib.ufl.edu/find/study-guide/spaces
- **S8** Marston Study Spaces: https://marston.uflib.ufl.edu/spaces/study-spaces
- **S9** LibCal room booking (Marston): https://libcal.uflib.ufl.edu/reserve/studyMSL
- **S10** C&RL News (1987), Marston Science Library opening article: https://crln.acrl.org/index.php/crlnews/article/view/21346/26543
- **S11** Wikipedia, University of Florida Marston Science Library: https://en.wikipedia.org/wiki/University_of_Florida_Marston_Science_Library
- **S12** UF News (2014-01-16), Marston first floor to become student study space: https://archive.news.ufl.edu/articles/2014/01/marston-science-library-first-floor-to-become-student-study-space.html
- **S13** The Independent Florida Alligator (2022-09-19), renovation follow-up: https://alligator.org/article/2022/09/marstonrenovationfollowup
- **S14** The Independent Florida Alligator (2025-03-14), the Marston fish tank: https://alligator.org/r/329f187dce
- **S15** UF IT Learning Spaces, Marston: https://it.ufl.edu/learning-spaces/locations/marston-science-library/
- **S16** UF Libraries Makerspace: https://makerspace.uflib.ufl.edu/makerspace/
- **S17** UF Libraries Communications, tag "marston" (2025-09-17 makerspace reopening): https://communications.uflib.ufl.edu/tag/marston/
- **S18** UF Archives, campus architecture intro (VOA Associates, CSE connection, Alachua): https://www.uflib.ufl.edu/ufarch/intro2.htm
- **S19** OpenStreetMap via `data/uf/campus.json` (w150860048, w859919297, w150860044, n4072026972, n2351681364, n8015039971, n1637323042, w588044235): https://www.openstreetmap.org/way/150860048
- **S20** Wikimedia Commons, Category:Marston Science Library (photos 2005-2023, esp. "University of Florida Marston Science Library.jpg", 2022, A. Abair, CC BY 4.0): https://commons.wikimedia.org/wiki/Category:Marston_Science_Library
- **S21** Project data: `tools/campus/landmarks/marston_turlington.py`, `data/uf/stages.json`, `docs/flow.md` §2-§4.
