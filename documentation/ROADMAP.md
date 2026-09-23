# Gothic modular kit: status and roadmap

Snapshot of where the kit stands and what's worth doing next. Companion to
`KIT_USER_GUIDE.md` (how to use it) and `.claude/skills/gothic-kit-piece/SKILL.md`
(how to build for it, including the mesh-topology lessons learned along the way).

## Current state

**Repo**: split out of `Blend-Zen` (was branch `feature/gothic-kit-house`
there) into its own repo on 2026-09-23, `main` branch. The shared
level-texture library and the reference village/island files stayed behind
in the sibling `Blend-Zen` repo on purpose -- see `NEXT_SESSION.md`.

**Kit library**: `blender_work_dir/kit/KIT_WALLS.blend`, 75 asset-marked pieces
(packed textures, catalog, description, tags, rendered preview each), plus a
hidden triangulated `_ZEN` copy of every one. Objects are laid out in a
non-overlapping grid, one row per family, so browsing the file directly in
the 3D viewport doesn't show pieces stacked on top of each other.

| Family | Pieces |
|---|---|
| Kit/Walls | `WALL_DOOR_A`, `WALL_WINDOW_A`, `WALL_WINDOW_TWIN_A`, `WALL_WINDOW_SHUTTER_A`, `WALL_PLAIN_A`, `WALL_PLAIN_LIGHT_A`, `WALL_RUIN_A`, `WALL_CORNER_A`, `WALL_CORNER_SOLO_A`, `WALL_UPPER_WINDOW_A`, `WALL_UPPER_PLAIN_A`, `WALL_UPPER_JETTY_A`, `WALL_CORNER_UPPER_A`, `WALL_CORNER_JETTY_A`, `TRIM_FASCIA_A` |
| Kit/Walls (civic) | `WALL_CIVIC_DOOR_A`, `WALL_CIVIC_WINDOW_A`, `WALL_CIVIC_PLAIN_A`, `WALL_CIVIC_CORNER_A`, `WALL_CIVIC_UPPER_WINDOW_A`, `WALL_CIVIC_UPPER_PLAIN_A`, `WALL_CIVIC_CORNER_UPPER_A` |
| Kit/Walls (sacred) | `WALL_SACRED_DOOR_A`, `WALL_SACRED_WINDOW_A`, `WALL_SACRED_PLAIN_A`, `WALL_SACRED_CORNER_A`, `WALL_SACRED_UPPER_WINDOW_A`, `WALL_SACRED_CORNER_UPPER_A` |
| Kit/Walls (row house RH1/RH2) | `WALL_RH1_DOOR_A`, `WALL_RH1_WINDOW_A`, `WALL_RH1_PLAIN_A`, `WALL_RH1_CORNER_A`, `WALL_RH1_UPPER_WINDOW_A`, `WALL_RH1_UPPER_PLAIN_A`, `WALL_RH1_CORNER_UPPER_A`, `WALL_RH2_*` (same 7) |
| Kit/Walls (burgher) | `WALL_BURGHER_DOOR_A`, `WALL_BURGHER_WINDOW_A`, `WALL_BURGHER_PLAIN_A`, `WALL_BURGHER_CORNER_A`, `WALL_BURGHER_UPPER_WINDOW_A`, `WALL_BURGHER_UPPER_PLAIN_A`, `WALL_BURGHER_CORNER_UPPER_A` |
| Kit/Walls (farm) | `WALL_FARM_DOOR_A`, `WALL_FARM_WINDOW_A`, `WALL_FARM_PLAIN_A`, `WALL_FARM_CORNER_A` (single-storey only, pairs with `ROOF_THATCH_*`) |
| Kit/Roofs | `ROOF_RUN_A`, `ROOF_END_GABLE_A`, `ROOF_DORMER_A`, `CHIMNEY_A`, `CHURCH_TOWER_A`, `ROOF_RH1_RUN_A`, `ROOF_RH1_END_GABLE_A`, `ROOF_RH2_RUN_A`, `ROOF_RH2_END_GABLE_A`, `ROOF_THATCH_RUN_A`, `ROOF_THATCH_END_GABLE_A` |
| Kit/Interior | `FLOOR_A`, `FLOOR_END_A` |
| Kit/Streets | `TERRAIN_FLAT_A`, `TERRAIN_YARD_A`, `ROAD_STRAIGHT_A`, `ROAD_JUNCTION_A` |
| Kit/Props | `SIGN_POST_A`, `RUIN_RUBBLE_A`, `RUIN_BEAM_A`, `ROUND_TOWER_A`, `WELL_A` |

**Sample scenes**: not kept as files in the repo (workspace cleanup —
regenerate on demand). `build_showcase_level.py` builds a full village
(houses, tavern, townhall, church, row houses, an L-shape, terrain, roads).
`build_organic_village.py` builds a second, non-grid composition (radial
terrain, buildings at arbitrary rotations around a central well/tower).
`build_sample_level.py` / `build_two_house_level.py` build simpler one/two
house demos. Run any of them via the Blender MCP or `blender --background
--python <script>`; each opens a blank file, builds, and saves its own
output — none of them touch `KIT_WALLS.blend`.

**Mesh quality**, verified by `check_piece()` on every piece and merge
tests on assembled houses: all quads on visible surfaces (documented
triangle exceptions only: floor rim/wall straps, the road junction's flat
mitre fan, the dormer's cheek walls); 0 non-manifold edges after a 1 mm
merge; a permanent stretched-UV check runs on every piece. `ROOF_END_GABLE_A`
has 2 pre-existing poles from its own construction (accepted, see below).

**Known, accepted limitations** (investigated, not oversights):
- **Wall-to-roof joint doesn't fully weld** (z=6 or z=3). Four real caps
  (2 wall bays + 2 roof runs) converge on that one edge; a manifold edge
  only holds two faces, so forcing the weld breaks the bay-to-bay weld
  instead. `TRIM_FASCIA_A` dresses the seam visually but doesn't close
  it — see `SKILL.md` lesson 13.
- **`ROOF_END_GABLE_A`'s outer end-cap self-intersects** into a jagged
  mess at both eave corners — a real bug, topologically fixed once this
  session (three attempts, see `SKILL.md` lesson 22), then **reverted at
  the user's own request** after seeing the redesigned shape didn't look
  good. Currently back to the original, unfixed geometry on purpose.
  Don't re-attempt without being asked; if asked, show an isolated-piece
  screenshot before touching the live kit.
- **`NW_ROW_HOUSES`/`NW_LSHAPE` have deliberate doubled geometry** at
  party walls / the L's inside corner (two independently-roofed sections
  placed edge to edge, no shared-wall piece or roof valley yet — lessons
  19-20). Verify a new one of these by screenshot at the join, not by
  chasing the merge-test overlap count to 0.
- **`WELL_A` is ring-only**, no roof or corner posts — adding them forced
  a choice between a disconnected mesh or a real 6-quad pole where 3
  bands meet at the rim. Shipped the simpler, clean ring; a roofed
  well-house is future work with its own support ring.

## Future work

Roughly ordered by how much it'd unblock or how quick a win it is; nothing
here is committed to.

### Structural / mesh-correctness

1. Close the wall-to-roof joint for real, or the z=3 storey seam's
   remaining ~16 open edges — both need the wall's branching top boundary
   simplified first (see "Known, accepted limitations").
2. `ROOF_END_GABLE_A`'s outer end-cap self-intersection (see above) —
   only if the user asks again; a working fix exists in git history
   (reverted commit) as a starting point.
3. A true roof valley for L-shaped footprints — needs the roof run's own
   cross-section to mitre at an inside corner, and the shared wall built
   once instead of twice. Likely the hardest open structural item.
4. A shared party-wall piece for row houses, to remove the doubled wall
   at each unit boundary (lower priority — the doubling is invisible in
   practice).

### New pieces

Studying `NW_VILLAGE_01` (the project's reference asset) directly turned
up ~18 building types this kit doesn't have yet, worth confirming
priority on before building toward closer parity:
- A tannery/smithy/sawmill/storehouse family (working-building
  silhouettes: bigger doors, external racks/wheels, no jetty).
- A windmill (rotating blades, a tapering tower — genuinely new geometry).
- A harbour quarter (dock edge, pilings, moored detail).
- Market stalls / open-air trading props.
- A curved/organic path tile, or promoting `build_organic_village.py`'s
  inline distance-to-segment path painting into a reusable `Kit/Streets`
  piece.

Also open: a hip roof (needs reworking `build_roof_run`'s cross-section
sweep, not just a new piece); a door leaf (closed/ajar, openings are
still bare holes); interior/exterior stairs; a road T-junction, fences,
a lamp post; more window/wall rhythm variants; a curved/diagonal road
tile; a second townhall/church wall-bay pattern (a real arched window
opening, not just a different material).

### Tooling / workflow

1. A small Blender add-on panel: "Place House" (the placement table,
   one click), "Weld Selection" (join + merge-by-distance, one button).
2. ZenGin export path — still open, see "Two open questions" in
   `NEXT_SESSION.md`.

### Polish

1. Revisit the stretched-UV check's thresholds once used on more pieces.
2. `NW_VILLAGE_01.blend` (29 MB reference file) stays untracked in git by
   design — revisit only if this branch becomes the long-term home for it.
