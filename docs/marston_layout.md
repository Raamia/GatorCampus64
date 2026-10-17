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
- **West side:** the makerspace (the Act 5 Printer Jam bay, its east wall open onto the Commons) and the South Computer Lab. [plan] Light-well windows on their west wall look into a sunken planted court. [inferred/gameplay]
- **North Computer Lab:** a long room under the court with a walk-in vent duct along its west wall at z −3.4..−1.4. [plan; duct gameplay]
- **Book sorting room:** in reality a staff room. In the game the book chute from the 2nd-floor vestibule lands here. [gameplay]
- **Restrooms and vending:** the gender-inclusive restroom is in the NE corner and the men's room is south of the NE tower; supply vending stands beside them. [plan]
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
- **Starbucks:** on the west, with its court door (locked) and an extra interior door from the west aisle. [plan; interior door gameplay]
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

### Floor 3, journals, classroom, aquarium (z +6)

![Floor 3](../art/levels/marston/layout_floor3.png)

- **Atrium balcony:** a ring with railings round the void; the top of the grand stair lands on its west side. The real 30-ft atrium cell is marked in blue on the sketch.
- **Stacks:** five periodical ranges north of the atrium and five south of it (the agriculture documents are the west end). Two theses ranges run east-west east of the atrium. [plan; ranges gameplay-spaced]
- **Around the elevators:** classroom L308 sits in front of the elevators, with the wellness room L307 beside it. The **fish tank** is across from the elevator doors (red coin R6). A data consultation room stands next to the core. [plan / inferred]
- **Other:** a computer row and display cases west of the atrium, reading tables along the east windows, and staff space plus the zig-zag bay offices along the west (closed).
- **Windows:** north windows look over the porch roof void; the zig-zag bays face the court roof; ribbon windows run along the east and south.

### Floor 4, quiet floor, books A-Z (z +12)

![Floor 4](../art/levels/marston/layout_floor4.png)

- **Stacks:** three A-QC ranges north of the atrium, with every second one 3.6 m tall (red coin R1 on top). West of the atrium are two QC-Z ranges plus the oversize range. [plan]
- **Moved stacks:** the QC-Z ranges the game atrium displaces move to a new band of five ranges on the south. [gameplay]
- **Quiet study:** carrel rows along the east band, using the 2022 furniture with power. [plan / inferred]
- **Computers:** along the west wing's north wall. [plan]
- **Terraces:** doors open onto the east terrace (X −42.6..−33.54) and the south terrace (Y −115.9..−125), both at z 12. They are walkable outdoor decks with 1.1 m parapets. [gameplay; the setbacks are plan]
- **Atrium chandelier:** a ring light hangs in the atrium with its top at z 15; reach it by long jump from this balcony. [gameplay]

### Floor 5, silent floor, reading rooms with a view (z +18)

![Floor 5](../art/levels/marston/layout_floor5.png)

- **Reading rooms:** an L-shaped silent floor round the atrium's top storey: the north reading room and the west reading room with carrel rows. The atrium's east and south sides here are the building's own exterior glass, which looks down the terraces.
- **North view windows:** these face Century Tower (bearing 31°, 114 m), the Auditorium and Turlington. The Act 1 star sits over the reading tables there, and the window counter runs along the glass. [plan / inferred]
- **West window desk:** the Act 2 goal; Shusher loops run between the carrel rows. [gameplay]
- **Upper terraces:** at z 18, reached from the NE stair hall (east) and through a south door. Red coin R8 is on the east terrace. [gameplay]

### Roof (z +24, gameplay)

The roof is a flat deck with a 1.0 m parapet and the atrium skylight (hipped glass, ridge z 27) in its SE corner. The NE and SW towers rise 5.7 m above it. The NE stair hall reaches the roof.

---

## 6. Vertical circulation

| Id | Where (map m) | Floors | Real | Game |
|---|---|---|---|---|
| `stair_ne` | NE tower X −52.6..−39.6, Y −67.4..−79.0 | F1-F5 (+roof) | stairwell + exit + restrooms on every floor (S2-S7) | switchback, flights run N-S. Two 5.85 m lanes (X −52.25..−46.4 and −45.8..−39.95). Floor landing on the south, turn landing on the north, 30°. Doors on the south face at X −52.3..−49.7 (F1-F4); on F5 the door is in the west face, plus a terrace door; roof door. Restrooms dropped. |
| `stair_sw` | SW tower X −90.82..−79.46, Y −107.8..−118.95 | F1-F5 | stairwell + exit on every floor (S2-S6) | switchback, flights run E-W. Two 4.95 m lanes, floor landing on the east, 30°. Doors: east face (F1-F3), north face (F4-F5). |
| `core` | X −77.8..−69.7, Y −83.2..−90.6 | F1-F5 | stair + exit + elevators at the court corner (S2-S6) | steep secondary stair, 35°, with 2.2 m lanes and its door to the east. Elevators 1 and 2 are 2.7 × 2.4 m with doors on the south. Elevator 1 is OUT OF ORDER in Act 1: doors stuck open, no car, a wall-kick shaft F2→F5. |
| `freight_elevator` | X −76.8..−73.8, Y −115.9..−112.9 | F1-F4 | a receiving room led to a freight elevator (S10); loading dock at the south notch (S19) | closed shaft; position inferred |
| `atrium` | game X −65.0..−51.83, Y −107.8..−93.0; real cell X −60.97..−51.83, Y −106.71..−97.57 | floor F2, open through F3-F5 | two storeys, 30 ft (S10) | 13.2 × 14.8 m, 24 m tall, skylight. Two free-standing module columns inside. |
| `grand_stair` | X −65.0..−61.5, Y −94.5 → −104.9, landing to −107.8 | F2→F3 | the central stair drawn by the architect and cut in 1987 (S10) | straight 3.5 m stair, 30° |
| `book_chute` | from the vestibule (−69.6, −77.2, z 0.8) to the sorting room (−80.0, −77.2, z −6.0) | F2→F1 | none | slide, 1.6 m wide, 33°; red coin R5 (as built: a 1.2 × 1.6 m hatch in the F2 floor at (−71.0..−69.8, −78.0..−76.4) over a 24° slide from z −2.0 at x −69.85 to z −6.0 at x −78.8, so it clears the F2 slab's underside by 1.9 m; see `tools/campus/interiors/marston.py` `CHUTE`) |

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
| A4 R1-R8 | F4, F1, F1, F4, F1, F3, F2, F5 | see JSON | | | range top, 3D printer, vent duct, chandelier, book chute, fish tank lid, Starbucks counter, upper terrace |
| A5 arena | F1 | X −80.2..−56.0, Y −115.4..−96.8 | −6 | | makerspace + west Commons; gantry rail at z −1.4 |
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

---

## 10. Materials and light

- **Shell:**
  - brick_red / brick_dark on the exterior, towers and interior feature walls
  - bronze fascias and piers (photos)
  - window_glass, white_trim, concrete
  - *New textures needed:* carpet (tinted per floor), wood shelving, ceiling tile (`make_textures.py`, not done here).
- **Floor accents:** each floor had its own accent colour in 1987 (S10), but the real colours are not published. The game picks: F1 lime, F2 UF orange, F3 coral, F4 sky blue, F5 violet. These come from the official plan legends. [gameplay]
- **Vertex-colour lighting:**
  - cool daylight within 3 m of windows
  - warm interior
  - darker stack aisles with lighter range tops
  - a bright atrium fading down from the skylight
  - a cooler basement with warmly lit glass study rooms
  - full daylight on the terraces

  The JSON gives RGB factors for each (`materials_and_light`).

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
| Starbucks | court door only | extra interior door | the court is backdrop |
| Staff spaces | NE offices, SW receiving corridor, F1 NW staff room | NE hall, SW corridor, book sorting room | connect the stairs; chute gag |
| Exhibit cases, highlights shelf | 2×2 cases in the lobby; shelf 3.3 m further west | cases along the atrium's south edge; shelf moved east | clear the lobby and the grand stair |
| Basement windows | unknown | light-well windows on the west | daylight on F1 |
| Window bands | narrow ribbons under dark fascias | sill 1.0, head 3.6 m (views 0.8-4.4 m) | readable views |
| Invented objects | none of these exist | book chute, vent duct, chandelier, book carts, kiosks, Shushers, printer gantry, falling encyclopedias | mission devices (§7.3) |

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
- **Elevators:** the plans draw one elevator symbol per floor; two cars are assumed.
- **Unplaced items:** the data consultation room on floor 3 and the real accent colours.
- **North Lab:** does the North Computer Lab really run under CSE? Only the floor-1 plan shows it.

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
