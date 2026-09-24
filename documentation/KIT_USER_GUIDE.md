# Gothic modular kit: user guide

For a Blender user building Gothic levels by hand. **You do not need Claude,
Python, or any add-on** -- the kit is a normal Blender Asset Library.

## 1. Add the library (once)

1. `Edit > Preferences > File Paths > Asset Libraries > +`
2. Pick the folder `blender_work_dir/kit/` (the one that contains
   `blender_assets.cats.txt` and the `KIT_*.blend` files). Name it
   `Gothic Kit`.

Open an **Asset Browser** editor and choose `Gothic Kit`. Pieces are sorted
in catalogs: `Kit/` (Gothic, `KIT_WALLS.blend`) and `Maya/` (flat-roof
family, `KIT_MAYA.blend`), each split into `WALLS`, `FLOORS`, `ROOFS`,
`STRUCTS` (Gothic also has `GROUND`); materials are in `MATS`. Search by
tag (`door`, `timber`, `4m bay`...).

## 2. Place pieces

- **Drag** a piece from the Asset Browser into the 3D viewport.
- Every kit asset carries **Append** as its own preferred import method, so
  dragging a piece in makes a local, editable copy whatever the library is
  set to (the `kit` library preference is Append too). For fewer duplicate
  materials set the Asset Browser header's Import Method to *Append (Reuse
  Data)*.
- Textures are **packed inside the kit files**, so nothing else has to be
  installed.

## 3. Snap pieces together (this is the whole trick)

Everything is built on a **1 m grid** (1 Blender unit = 1 m):

| Thing | Size |
|---|---|
| wall bay / road segment | 4 m |
| storey height | 3 m |
| wall thickness | 0.4 m |
| door opening | 1.2 x 2.2 m |
| window opening | 1.0 x 1.2 m, sill at 1.0 m |

Every piece's **origin sits on the floor on the INSIDE face of the wall**:
a wall bay's at the inside face's left end, a corner block's at its inner
corner. The wall's 0.4 m thickness hangs outside the grid line, so a room
is exactly 4n x 4 m and every piece of a house lands on whole metres. So:

1. Enable snapping (`Shift+Tab`), **Snap To: Increment**, and set grid
   scale 1 (or hold `Ctrl` while dragging).
2. Move pieces in whole metres. A wall bay placed at x = 0, 4, 8... butts
   flush with its neighbour; the texture continues across the joint.
3. Rotate in 90-degree steps (`R`, `Z`, `90`).
4. For an exact fit anywhere: **Snap To: Vertex** and drag by the origin.

Pieces are open on their snap faces on purpose (a wall bay is open at its
left and right ends). Don't try to "close" them.

**A corner and the wall that starts at it share one grid point.** Put the
corner at an inner room corner, e.g. `(0,0,0)`, and the first wall bay at
the same `(0,0,0)`: the corner block fills the 0.4 m outside the room, the
bay runs from there. Going round the room the corners turn 0, 90, 180,
270; the roof run sits on the same point as the bay under it, and the roof
end on the same point as the first run.

## 4. Variants and ruins

Variants (`_A`, `_B`, `_C`, `_RUIN`) share the same footprint and snap points.
Swap one for another in place -- nothing needs re-snapping. Mix them so a
town doesn't look copy-pasted.

## 5. Editing a piece

Select it, `Tab` to edit. The mesh is **all quads, one connected surface**,
flat shaded, one UV map called `Float2`. Keep it that way:

- Add detail with loop cuts, extrude, inset. Don't `Join` separate boxes.
- Don't triangulate. Each piece has a hidden export copy `<name>_ZEN`
  (`KIT_EXPORT_ZEN` collection, triangulated) for ZenGin. Use that copy when
  exporting.
- Materials are plain: Image Texture -> Principled BSDF. Swap a material
  by choosing another one from the level texture library
  (`materials_levels.blend`, in the sibling `Blend-Zen` repo at
  `asset_catalog/materials_levels.blend` -- shared infrastructure, not
  copied into this repo).

## 6. Adding your own piece to the kit

1. Model it following section 5 and put its origin on the floor at the snap
   corner. Name it `KIT_<FAMILY>_<PIECE>_<VAR>`, e.g. `KIT_WALL_WINDOW_B`.
2. Right-click the object in the Outliner > `Mark as Asset`.
3. In the Asset Browser's sidebar set its **Catalog**, a short
   description (size, snap planes, origin), and tags.
4. Save into the matching `KIT_<FAMILY>.blend`; regenerate the preview
   (Asset Browser > right-click > `Generate Preview`) **one at a time**.

## 7. Building a house, and welding it into one mesh

Pieces are designed so that **their open edges are identical vertex loops**.
Snap them on the **1 m grid**, select everything, `Join` (`Ctrl+J`), then in
Edit Mode `M > By Distance` (merge distance 0.001 m): the seams disappear and
you have one connected mesh. Any wall bay fits next to any other wall bay;
corner blocks and the roof end piece fit their neighbours the same way.

Example house with an 8 x 4 m room (8.8 x 4.8 m outside), one or two
storeys (ground floor top is z = 3 m, upper floor top z = 6 m; walls face -Y
at rotation 0). For a one-storey house put the roof pieces at z = 3 instead
of z = 6 (and use `WALL_CORNER_SOLO_A` corners). Every position is on the
1 m grid:

| What | Position (x, y, z) | Rotate Z |
|---|---|---|
| Ground wall bays, south | (0,0,0) (4,0,0) | 0 |
| ... north | (8,4,0) (4,4,0) | 180 |
| ... east / west | (8,0,0) / (0,4,0) | 90 / 270 |
| Ground corner blocks | (0,0,0) (8,0,0) (8,4,0) (0,4,0) | 0, 90, 180, 270 |
| Upper wall bays | same x, y, rotation as the ground bays, **z = 3** | as above |
| Upper corner blocks | same as ground corners, **z = 3** | as above |
| Roof runs | (0,0,z_roof) (4,0,z_roof) | 0 |
| Roof end + gable | (0,0,z_roof) west, (8,4,z_roof) east | 0, 180 |
| Ground floor | `FLOOR_GROUND_END_A` at (0,0,0) and (8,4,0) rotated 180 (planks at 0.46 = door threshold) | 0 and 180 |
| Upper floor | `FLOOR_END_A` at (0,0,3) and (8,4,3) rotated 180 | 0 and 180 |
| Chimney | (x, 2, z_roof), x anywhere on the ridge | 0 |

`z_roof` is the top of the highest wall storey (3 or 6). A room is 4n m long;
corners and bays share their grid points (the corner block is the 0.4 m
outside the room). Depth is fixed at one bay (4 m room, 4.8 m outer) so
the roof fits. Welding: ground bays + ground corners merge into one closed ring;
upper bays + upper corners the same; roof runs + the two end/gable pieces the same
(all checked with a 1 mm merge). Floor: the two END tiles close the floor watertight (an open floor end is not manifold, so use END tiles at both ends and `FLOOR_A` / `FLOOR_GROUND_A` in between for longer houses). The ground-floor tiles' stone base has its bottom vertices on the walls' inside-face bottom row, so the merge joins the floor to the walls too -- along that hidden edge three faces meet (wall inside face, wall bottom, base), a harmless non-manifold edge under the floor.

The ground-to-upper storey seam (z = 3) welds: every ground bay's top and
every upper bay's bottom is the same open vertex loop, so any ground bay
under any upper bay merges into one closed tube (0 non-manifold edges). On the hidden inside
face the two sides only share the common columns, so different bay types
meet there in straight T-junctions: Merge by Distance leaves those as open
edges along the inside of the seam. They are harmless: the edges are
collinear, so there is no gap and nothing shows. The same holds under the
gable's attic face;
outside, the ground eave and the upper sole plate meet in a chamfered
groove. The gable end welds to the wall bay and corner blocks under it the same way (their tops are open, the gable's bottom is built from them). A wall-to-roof joint (z = 6, or 3 for a one-storey house)
still just touches flush and does not fully weld -- not for lack of trying:
the wall's own top and the roof's soffit are now built to the same flat
strip too, but at every point where a bay boundary lines up with a roof-run
boundary (every 4 m along the eave, and at the corners) FOUR surfaces
converge there at once (bay 1's cap, bay 2's cap, roof run 1's cap, roof
run 2's cap) -- a proper mesh edge can only border 2 faces, so welding that
line to the roof would break the (required) bay-to-bay weld instead. After
merging you'll see the expected open/interior faces along that one line;
leave them, or `Select > Select All by Trait > Interior Faces` to tidy up.

## 8. The Maya family (`KIT_MAYA.blend`)

A second style: stone-and-plaster houses with flat roofs (the look of
HOUSE.001 in village_2.blend). Same grid (4 m bays, 3 m storeys), 0.3 m walls,
same origins: a wall bay at the INSIDE face / left end, a corner at the inner
corner. Place a house exactly like a Gothic one:

| Piece | Where |
|---|---|
| `KIT_MAYA_WALL_*_A` (ground) | z = 0, bays along the room sides, rotated 0/90/180/270 |
| `KIT_MAYA_WALL_UPPER_*_A` | same x/y, z = 3 (6 for a third storey) |
| `KIT_MAYA_WALL_CORNER_A` / `_CORNER_UPPER_A` | the four inner room corners, per storey |
| `KIT_MAYA_PARAPET_*_A` + `_PARAPET_CORNER_A` | on top of the TOP storey (z = 3 for a one-storey house) |
| `KIT_MAYA_ROOF_DECK_A` | with the TOP storey's matrix (it sits inside the parapet) |
| `KIT_MAYA_FLOOR_GROUND_A` | z = 0, one per 4 x 4 m room cell |
| `KIT_MAYA_FLOOR_UPPER_A` | with the storey BELOW it (z = 0 for the first floor) |
| `KIT_MAYA_STEP_A` | with the door bay's own matrix |

Bays: plain, window (keystone), twin window, arched door (ground only),
blind niche with a carved relief, and cracked variants. Parapets: plain,
rain spout, carved frieze -- all interchangeable. Every wall bay welds to every
other of its storey, storeys weld to each other and to the parapet, floor
tiles weld to their neighbours; after Merge by Distance (1 mm) a house has 0
non-manifold edges. The floor / ceiling / roof slabs touch the wall faces flush
(2 cm off the storey seam on purpose) without welding to them.

## What's in the kit now

All in `KIT_WALLS.blend` (roof/chimney in `KIT_ROOF`, ground/road in `KIT_STREETS`):

| Piece | What it is |
|---|---|
| `KIT_WALL_DOOR_A` | 4 m ground bay: centred door, stone footing, no window (228) |
| `KIT_WALL_WINDOW_A` | 4 m ground bay: one window, set high (between the mid rail and the eave, not down by the footing) (228) |
| `KIT_WALL_PLAIN_A` | 4 m ground bay: closed, studs and mid rail (106) |
| `KIT_WALL_PLAIN_LIGHT_A` | 4 m ground bay: closed, light frame -- corner posts + eave + sole only, no mid rail, for a plainer front (106) |
| `KIT_WALL_WINDOW_TWIN_A` | 4 m ground bay: two narrow windows with a timber pier between, a different facade rhythm (350) |
| `KIT_WALL_WINDOW_SHUTTER_A` | 4 m ground bay: one high window with a carved-ornament jamb -- more decorated than the plain window bay (228) |
| `KIT_WALL_RUIN_A` | ruined ground bay: broken top of varying height, a fallen-through hole, moss rubble over the stone footing -- open top/ends, stands alone or beside another ruin (99) |
| `KIT_WALL_CORNER_A` | 0.4 m mitred ground corner block, 3 m tall, open top and bottom (22) |
| `KIT_WALL_CORNER_SOLO_A` | ground corner for a SINGLE-STOREY building only (its top is nudged so a roof/gable sitting directly on it doesn't overlap -- see below) (22) |
| `KIT_WALL_UPPER_WINDOW_A` | 4 m upper-floor bay: one high window, timber sole plate (186) |
| `KIT_WALL_UPPER_PLAIN_A` | 4 m upper-floor bay: closed, no window -- for a side/rear that shouldn't repeat the front's window rhythm (86) |
| `KIT_WALL_CORNER_UPPER_A` | 0.4 m mitred corner block for the upper floor (18) |
| `KIT_TRIM_FASCIA_A` | timber fascia board, laps over an upper wall bay's top edge and the roof's underside -- surface-mounted, not welded (see below) (4) |
| `KIT_ROOF_RUN_A` | 4 m solid roof section for the 4.8 m depth (90) |
| `KIT_ROOF_END_GABLE_A` | closed roof end with the gable wall built in, welds to a run (206) |
| `KIT_ROOF_T_A` | T roof junction: 12 m of main roof (three bays) with a 4 m wing roof at 90 degrees off its middle bay, two real valleys. Snaps like a run on the middle bay's point; each of its three ends takes a gable end or another run (283) |
| `KIT_ROOF_L_A` | L roof corner: 4 m of roof turning 90 degrees in the corner bay into a 4 m wing (hip outside, valley inside); rotate it for any corner direction (172) |
| `KIT_ROOF_DORMER_A` | shed-roof window dormer, surface-mounted on a roof run at local (x=1.4, y=0.7) -- sits flush on the run's own slope, not cut into it (15) |
| `KIT_CHIMNEY_A` | stone chimney stack with a saddle base for the ridge (58) |
| `KIT_FLOOR_A` | 4 x 4 m timber floor tile, open on both x ends (middle tile of a long floor) (108) |
| `KIT_FLOOR_END_A` | same tile with its x=0 side closed by a rim: use at both ends of a floor (157) |
| `KIT_FLOOR_GROUND_A` | ground-floor version of `FLOOR_A`: same planks and joists lifted onto a low stone base -- origin on the ground, plank tops at 0.46 (the door threshold) (114) |
| `KIT_FLOOR_GROUND_END_A` | ground-floor version of `FLOOR_END_A`, same stone base (166) |
| `KIT_STAIR_A` | timber stair, ground floor (0.46) to upper floor (3.0): 10 risers, 1 m wide against the back wall (y 3..4), climbing +x. Origin = inner room corner on the ground, same point as the room's ground floor tile (70) |
| `KIT_FLOOR_STAIRWELL_A` / `_END_A` | `FLOOR_A` / `FLOOR_END_A` with the stairwell for `KIT_STAIR_A` (x 0.58..3.42, y 2.99..4, framed by a header beam); same snap loops, use it in their place at z = 3 (248 / 298) |
| `KIT_MAYA_STAIR_A` | Maya: solid plastered stair with ashlar treads, 0.05 to 2.98, 11 risers, same layout and origin as `KIT_STAIR_A` (59) |
| `KIT_MAYA_FLOOR_UPPER_STAIRWELL_A` | Maya: `FLOOR_UPPER_A` with the stairwell for `KIT_MAYA_STAIR_A` (x 0.5..3.5, y 3..4); place both at the same room corner (67) |
| `KIT_TERRAIN_FLAT_A` | 4 x 4 m flat grass ground tile, open on all four sides (16) |
| `KIT_TERRAIN_YARD_A` | 4 x 4 m flat bare/trodden dooryard tile, same weld contract (16) |
| `KIT_ROAD_STRAIGHT_A` | 4 x 4 m gravel road segment, 2 m wide, runs north-south with grass shoulders; rotate 90 for east-west (16) |
| `KIT_ROAD_JUNCTION_A` | 4 x 4 m road crossroads, mitred at a true diagonal seam so the directional road texture turns the corner cleanly (20) |
| `KIT_SIGN_POST_A` | freestanding timber post + bracket arm + hanging board, for a tavern's door (17) |
| `KIT_CHURCH_TOWER_A` | freestanding square stone bell tower, belfry band, hip-style tiled spire (17) |
| `KIT_RUIN_RUBBLE_A` | freestanding height-field rubble mound with a few embedded cut-stone blocks (20) |
| `KIT_RUIN_BEAM_A` | freestanding fallen roof/floor timber, lying on the ground (18) |
| `KIT_WALL_CIVIC_*` / `KIT_WALL_SACRED_*` | same geometry as `WALL_DOOR_A`/`WALL_WINDOW_A`/`WALL_PLAIN_A`/`WALL_CORNER_A` and their upper-floor counterparts, re-textured: civic = cut-ashlar facade (townhall), sacred = carved stone with a botanical relief (church) |
| `KIT_WALL_RH1_*` / `KIT_WALL_RH2_*` / `KIT_ROOF_RH1/RH2_*` | same geometry as their residential counterparts (`DOOR_A`/`WINDOW_A`/`PLAIN_A`/`CORNER_A` + upper + `ROOF_RUN_A`/`ROOF_END_GABLE_A`), re-textured with a different wall pattern + roof colour, for row-house street variety |
| `KIT_WALL_BURGHER_*` | same geometry as the residential family (door/window/plain/corner + upper counterparts), re-textured stucco render + dark timber, for a richer/taller townhouse street frontage |
| `KIT_WALL_FARM_*` / `KIT_ROOF_THATCH_*` | same geometry as `WALL_DOOR_A`/`WALL_WINDOW_A`/`WALL_PLAIN_A`/`WALL_CORNER_A` (single-storey only) and `ROOF_RUN_A`/`ROOF_END_GABLE_A`, re-textured rough farmhouse timber + straw thatch |
| `KIT_ROUND_TOWER_A` | freestanding octagonal watchtower: a tapering shaft, an open belfry band partway up, a frustum-capped spire (no pole at the apex) (50) |
| `KIT_WELL_A` | freestanding octagonal stone well: a short ring wall + a dark "water" cap. Ring only -- no roof/posts, see below (42) |

Visible surfaces are all quads (no fans or poles), with two documented,
deliberate exceptions: the road junction's centre (a flat 8-triangle mitre
fan, so its directional texture can turn 90 degrees) and the roof dormer's
two cheek walls (a shed roof's own silhouette). Otherwise the few triangles
that remain sit on hidden flat strips (wall tops/bottoms, inside roof ends).
Bigger flat quads come from designing openings on shared rows, not from
decimation. The kit is being extended (next: stairs, hip roof, more street
furniture -- see `documentation/ROADMAP.md`); see
`.claude/skills/gothic-kit-piece/SKILL.md` for the design rules.

### Newer variants -- placement notes

- **Ornamented window / ruin**: drop-in replacements for a normal ground bay
  wherever you'd use `WALL_WINDOW_A` / any ground bay; same 4 m footprint
  and end loops. (`WALL_WINDOW_SHUTTER_A` originally also carried a pair of
  open shutter panels; dropped -- their reused door-plank texture put a
  door hinge/lock decal on a panel too small to read as anything but a
  mismatched sticker, see `SKILL.md` lesson 23.) The ruin's top and ends
  are genuinely open (it's not meant to carry a roof or weld to a pristine
  wall bay).
- **Dormer**: place directly on top of an already-placed `ROOF_RUN_A` at
  the same x, y, z origin as that run (it reads the run's own slope, so it
  lines up automatically). It's surface-mounted, not welded into the roof's
  own mesh -- Merge by Distance won't stitch it to the roof's shingle
  courses, which is expected.
- **Fascia**: place at the SAME x, y, z, rotation as the upper wall bay
  it's finishing (its own local z=3 already matches that wall's top row).
  It's surface-mounted like the dormer above, not welded -- it covers the
  wall-to-roof seam visually but doesn't reduce the model's open-edge
  count (the wall's real top boundary there is a branching zigzag, not a
  straight edge to weld against; see `SKILL.md` lesson 16). It does weld
  sideways to a second fascia board at the next bay over.

### Civic buildings, small houses, and freestanding props

- **Civic/sacred re-textures**: `WALL_CIVIC_*` and `WALL_SACRED_*` are the
  EXACT SAME geometry as their residential counterparts (`WALL_DOOR_A` etc)
  with different material slots -- they place identically (same offsets,
  same weld contract, `WALL_CIVIC_CORNER_A`/`WALL_SACRED_CORNER_A` instead
  of `WALL_CORNER_A`) and weld to EACH OTHER exactly like the residential
  family does, but do NOT mix a civic/sacred wall with a residential corner
  or vice versa at the same corner (different object, but check face
  counts match before assuming a cross-family weld works -- it hasn't been
  tested).
- **Single-storey cottage**: `WALL_CORNER_SOLO_A`, not `WALL_CORNER_A`, for
  any ground-only building (no upper storey) -- the plain `WALL_CORNER_A`
  assumes an upper corner stacks on top of it, so its own top lip isn't
  nudged clear of the roof/gable the way `WALL_CORNER_SOLO_A`'s is. Mixing
  them up doesn't fail loudly: both pieces check out individually clean,
  it only shows up as a genuine 3-face overlap once merged (see `SKILL.md`
  lesson 18).
- **Sign post**: place directly in front of a door bay, a few cm proud of
  the wall face (see `build_showcase_level.py`'s tavern placement for the
  offset used there). Freestanding, not welded to anything.
- **Bell tower**: place beside a nave's gable end, its own footprint clear
  of the nave's -- freestanding, not derived from or welded to the church
  wall bays.
- **Ruin debris**: `RUIN_RUBBLE_A`/`RUIN_BEAM_A` are freestanding scatter,
  same as the ruin walls themselves -- place by eye, any rotation, no weld
  contract to honour.
- **Burgher / farm+thatch palettes**: straight retexture-copies, same
  weld contract as the family they're copied from -- `WALL_BURGHER_*`
  places exactly like the residential family (7 pieces, ground + upper),
  `WALL_FARM_*` like the single-storey cottage family (4 pieces, no
  upper-storey counterpart -- pair with `ROOF_THATCH_RUN_A`/
  `ROOF_THATCH_END_GABLE_A` instead of the standard roof pieces, same
  placement as any other roof run/gable).
- **Round tower / well**: both freestanding, origin at ground level,
  no weld contract to anything else -- place by eye, any rotation, like
  the sign post or bell tower. The well is ring-only (no roof or corner
  posts -- dropped to avoid a choice between a disconnected mesh and a
  real 6-quad pole where 3 bands would meet at its rim; see ROADMAP.md's
  "Known, accepted limitation" note and `village_pieces.py`'s `build_well`
  docstring for the tradeoff). Both were designed by studying
  `NW_VILLAGE_01` directly (its own tower/well silhouettes via the
  Blender MCP), not guessed at.

### T-shaped house (cross wing)

`KIT_ROOF_T_A` roofs a 3-bay main house with a 1-bay (4 m room) wing off its
middle bay. With the main house's inner corner at (-4,0) (room x -4..8,
y 0..4) and the wing room at x 0..4, y 4..8:

| What | Position (x, y, z) | Rotate Z |
|---|---|---|
| T roof | (0,0,3) -- the middle bay's point | 0 |
| West gable end | (-4,0,3) | 0 |
| East gable end | (8,4,3) | 180 |
| Wing gable end | (0,8,3) | 270 |
| ...or continue: west run (-8,0,3), east run (8,0,3), wing run (4,8,3) | | 0, 0, 90 |

For a two-storey house use z = 6. Every end is an ordinary run end, so the
merge closes the whole roof (checked: T + three gables, and T + three runs +
three gables, both 0 open and 0 non-manifold edges). The shingle courses of
both roofs meet exactly on the valleys. Walls: the main house's north side
has no bay where the wing opens; the two inside corners of the T (at (0,4)
and (4,4)) have no inside-corner piece yet, so the main north bay and the
wing side wall overlap by 0.4 x 0.4 m there.

### L-shaped house (corner)

`KIT_ROOF_L_A` turns the roof round an L footprint. With the corner bay's
inner corner at (0,0) (main room x -4..4, y 0..4; wing room x 0..4,
y 4..8):

| What | Position (x, y, z) | Rotate Z |
|---|---|---|
| L roof | (0,0,3) -- the corner bay's point | 0 |
| West gable end | (-4,0,3) | 0 |
| Wing gable end | (0,8,3) | 270 |
| ...or continue: west run (-8,0,3), wing run (4,8,3) | | 0, 90 |

Rotate the whole group (walls, roof, gables) for the other three corner
directions. It also chains with the T (checked: L + T + gables closes with 0
open and 0 non-manifold edges). Same wall caveat as the T: the inside corner
has no inside-corner wall piece yet.

### Row houses and L-shaped buildings

`build_showcase_level.py`'s `section_placements` is the general form every
house composition is now built from: a rectangular gable-roofed section
(any wall spec, any `n_bays`, with or without an upper storey) built at a
local origin, then wrapped in ONE outer `M(x0, y0, 0, rot)` -- so `rot`
alone decides which world direction the gable faces. `house_placements`/
`small_house_placements` are the `rot=0` special case; nothing else about
them needed to change. These scripts still write their positions in the
kit's OLD origin frame (outer wall face / outer corner); every placement
goes through `kit_lib.legacy_placement()`, which converts it for the
current inside-face origins, so the numbers in them are not grid positions
to copy by hand -- use the table in section 7 for that.

- **Row house / terrace unit**: `section_placements(x0, y_back, 270,
  n_bays=1, upper=True, ...)`. `rot=270` was found empirically (place one
  test unit, read back its door object's world position), not derived by
  hand -- it puts the section's own gable-end "E" wall (and whatever door/
  window is on it) facing world -Y. The door/gable edge lands at
  `y_back - 4.8`, not at `y_back` itself (the section's local footprint
  extends in -Y after this rotation) -- set `y_back` to
  `(street Y) + 4.8` to land the front on a specific street line. `S`/`N`
  (a unit's own local eave walls) become the PARTY WALLS after rotation --
  always a plain wall (`*_PLAIN_A`), since two units are placed edge to
  edge (4.8 m apart, one `n_bays=1` footprint's own width) with no gap.
  Each unit keeps its own complete roof + gable end, INCLUDING at the
  shared party-wall edge -- this is a deliberate doubled-wall overlap, not
  a bug (see `SKILL.md` lesson 20 and ROADMAP.md's "known, accepted
  limitation" note). `KIT_WALL_RH1_*`/`RH2_*` + matching
  `KIT_ROOF_RH1/RH2_*` give a row real palette variety beyond the
  default residential materials.
- **L-shaped building**: two `section_placements` calls (e.g. `rot=0` and
  `rot=90`), positioned so their footprints share a FULL wall-length edge
  (not just a corner point) -- work out the second section's origin from
  where you want its rotated footprint to land (`NW_LSHAPE`'s own build
  code in `build_showcase_level.py` derives this from the rotation
  matrices directly, with the working shown). Each section keeps its own
  separate roof; there is no valley yet, so the shared edge gets a real,
  doubled wall + corner + gable-end roof from BOTH sections. Verify a new
  L-shape by screenshot at the join, not by chasing its merge-test overlap
  count to 0 -- that bar doesn't apply to this kind of composition (see
  ROADMAP.md's "Future work" for the true-valley item this is queued
  ahead of).

### Terrain

`build_showcase_level.py`'s `NW_TERRAIN` is a hand-authored height-field
grid (gothic-terrain-piece's own technique: a rectangular vertex grid with
a height field, never concentric rings) surrounding the flat tile
footprint -- flat (z=0) under the tiles plus a short collar, rising into
low hills further out. It is a SEPARATE mesh from `NW_GROUND`, positioned
so its own flat collar sits at the same z=0 plane and X/Y extent as the
tile grid's outer edge -- continuous-LOOKING, not a vertex weld (the tile
grid and a hand-authored height field don't share a partition to weld
against, the same touches-not-welds relationship the chimney/dormer
already use). If you extend the village footprint, extend
`CORE_X0/X1/Y0/Y1` in the terrain-building code to match, or the collar's
flat margin will end up either overlapping tiles or leaving a visible gap.

### Organic (non-grid) terrain and composition

`build_organic_village.py` is a second, separate level script -- it does
NOT extend `build_showcase_level.py`'s street-grid terrain, it replaces
the terrain technique entirely for a non-grid scene:

- **Radial height field**: `_terrain_height(x, y)` keys off
  `d = math.hypot(x, y)` (distance from the origin) instead of the
  rectangular core+collar bounding box `build_showcase_level.py` uses --
  flat within `CLEAR_R` of the origin, rising into hills beyond a
  `COLLAR` transition band. Use this version instead of the rectangular
  one whenever a scene's buildings sit at arbitrary angles around a
  central point rather than along streets; the rectangular version reads
  wrong (a visible straight collar edge) once buildings aren't axis-
  aligned.
- **Houses at arbitrary rotation**: buildings are placed with
  `section_placements`/`small_house_placements` at whatever `rot` reads
  right for an organic cluster (this scene uses 18/-30/105/210/340
  degrees, not the usual 0/90/180/270 street grid) -- the wall/roof
  geometry itself doesn't care, only the terrain and path network need to
  follow suit.
- **Path network without tiles**: `_dist_to_path(x, y)` computes the
  minimum distance from a terrain face's centre to any of several
  well-to-doorstep line segments (`DOORSTEPS`), and faces near-enough and
  low-enough get a dirt-path material instead of grass/stone -- a
  material-zoning technique, not a placeable `Kit/Streets` tile, so it
  only exists inline in this script for now (see ROADMAP.md's "New
  pieces" list for promoting it into a reusable piece).

Reuse the radial-terrain + arbitrary-rotation pattern for any future
non-grid scene; reuse the rectangular core+collar terrain from
`build_showcase_level.py` for anything that keeps the street grid.

### Ground and road tiles

The `Kit/Streets` tiles share one weld contract, separate from the house's:
every tile is a flat 4 x 4 m quad grid with the SAME z = 0 boundary loop on
all four sides, so any mix of `TERRAIN_FLAT_A`, `TERRAIN_YARD_A`,
`ROAD_STRAIGHT_A` and `ROAD_JUNCTION_A`, in any rotation, welds to its
neighbours with a 1 mm merge -- lay them out on the same grid the wall bays
use (world x/y multiples of 4 m) and they tile like the walls do. A straight
road tile's own footprint is corner-anchored, so rotate it in place (about
its own centre, e.g. with the 3D cursor set to its middle) rather than
moving it after rotating, or its 2 m road band will land off the tile you
meant to cover.

## Sample levels

Not kept as files in the repo (workspace stays lean) — run a script to
regenerate one on demand, via the Blender MCP or
`blender --background --python <script>`. Each builds a fresh scene and
saves its own output; none of them modify `KIT_WALLS.blend`.

- `build_sample_level.py` -- one two-storey house on procedural terrain
  (hill, rock outcrop, a meandering road to a cobbled doorstep).
- `build_two_house_level.py` -- two differently-massed houses (window
  rhythm, framing, upper-storey treatment, chimney position all differ)
  connected by the modular ground/road tiles.
- `build_showcase_level.py` -- a full village: houses A/B/C, two cottages,
  a tavern, a townhall (civic palette), a church (sacred palette + bell
  tower), a 5-unit row/terrace, a first L-shaped building, a ruin site,
  roads with a civic-square branch, and a rolling terrain apron. Its own
  module docstring has the full building-by-building placement.
- `build_organic_village.py` -- a second, non-grid composition built after
  studying `NW_VILLAGE_01` directly: five buildings at arbitrary rotations
  around a central well/watchtower, on a radial (not rectangular) terrain
  with dirt paths running from each doorstep to the well. Carries its own
  self-contained copies of the shared placement helpers rather than
  importing `build_showcase_level.py` -- see "Organic (non-grid) terrain
  and composition" above.

Each script's output keeps hidden triangulated `_ZEN` copies of every
object in its own export collection.
