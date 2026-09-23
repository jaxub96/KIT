---
name: gothic-kit-piece
description: Design and build a new, original modular kit piece (wall, corner, door/window wall, roof run, stairs, road/path segment, fence, pillar, arch, market stall, harbour dock, ruin chunk...) for a reusable Gothic (ZenGin, Gothic 1/2) level-building library in Blender via the blender MCP tools. Use when the user asks for a kit piece, modular asset, building block, "asset for building towns/buildings/roads", or to extend the kit library -- NOT for a one-off terrain/level chunk (use gothic-terrain-piece for that) and NOT for extracting pieces out of an existing level mesh.
---

# Gothic kit piece

We are building an **original modular asset library**: high-quality, detailed,
creative pieces a level designer snaps together to make towns, buildings and
roads. Pieces are authored from scratch. The village file and island files
are **reference for scale, palette and style only** -- never cut pieces out
of them. This kit lives in its own repo, split out of the original `Blend-Zen`
project on 2026-09-23; those reference files were left behind there and are
NOT part of this repo -- they live at the sibling path
`../Blend-Zen/blender_work_dir/NW_VILLAGE_01.blend` (and `G2ISLAND_WEB.blend`)
on disk. Same for the shared level-texture library (see below).

Companions: `scripts/kit_lib.py` (tested helpers -- exec it, don't reinvent),
and the `gothic-terrain-piece` skill (same material/UV/flat-shading
conventions; its `WORKFLOW.md` topology rules apply here unchanged).

## Non-negotiable mesh rules (same as the terrain skill)

1. **One connected mesh per piece.** Detail is *grown out of the surface*
   (extrude / inset / loop cuts on a planned grid). Never `Join` a separate
   beam/sill/step box onto a wall and never Boolean. `check_piece()` fails
   `components_bad` on any second island.
2. **Quads only.** Zero tris, zero n-gons in the master -- including gable
   ends (see "Recipes"). Triangulate **only** on the hidden `_ZEN` export copy.
3. **No poles.** No fans from a center vertex, no cylinder cap fans. Valence
   5 at the reflex corner of a rectangular opening is normal; 6+ is a bug.
4. **Flat shaded, one UV map named `Float2`, one stock material per surface**
   (Image Texture sRGB -> Principled Base Color; nothing else). Materials are
   never created by hand: `ensure_material(name)` appends them from
   `asset_catalog/materials_levels.blend` (857 level textures, names ==
   texture filenames). No normal/roughness maps, no vertex-colour tricks.
5. **Real geometry carries the detail, textures carry only colour/grain.**
   With flat textures and no normal maps, depth comes from actual relief:
   recessed panels, raised timbers, chamfered corners, reveals, overhangs.
   That is what separates a "high quality" piece from a textured box.

## Module grid (the contract that makes pieces snap)

Verified from the village file: **1 Blender unit = 1 metre** (cart 1.8x3.0x1.5,
statue 5.9 tall; median edge length in the village is 1.0). Constants live at
the top of `kit_lib.py` -- change them there, once, if the user overrides:

| Constant | Value | Notes |
|---|---|---|
| `U` | 1.0 | base cell; piece bounding boxes are whole multiples |
| `BAY` | 4.0 | wall bay / road segment width |
| `STOREY` | 3.0 | floor-to-floor; ground floor wall = 3.0 |
| `WALL_T` | 0.4 | wall thickness (reveals read as real depth) |
| door | 1.2 x 2.2 | opening, on the grid lines you build |
| window | 1.0 x 1.2, sill 1.0 | |

Only the **bounding box and the snap planes** must sit on whole units.
Interior detail lines (opening edges, timber edges) may be at 0.1 m steps --
put them into the `xs`/`zs` grid-line lists so faces land exactly on them.
Every piece is authored so:

- **Origin = floor level, at the piece's own snap corner** (wall: bottom-left
  front corner; road: centre of the bottom face; stairs: bottom-front centre).
  Record the choice in the piece's custom property `kit_origin`.
- **Snap faces are flat, on grid planes, and left open** (a wall bay's left
  and right edge are open boundary loops -- that is the *only* allowed open
  boundary). Neighbouring pieces must present **identical vertex spacing on
  their shared plane** so the level author can weld or just butt them.
  Store them: `kit_snap = "x0,x4,z0"` (planes that are open by design).
- **Materials/UVs continue across pieces**: `set_grid_uv` works from
  piece-local coordinates and the tile size divides `BAY`, so a texture runs
  seamlessly from one wall bay into the next.
- **Variants share a footprint** (`_A`, `_B`, `_C`, `_RUIN`): same bounding
  box, same snap loops, different detail -- swappable in a level with no
  re-snapping. Every family needs at least 2 variants + a damaged/ruined one
  so towns don't look copy-pasted.

## Detail budget and texel density (measured from the village)

Reference: 16k quads for 18 full buildings with interiors + terrain; a whole
house shell is 250-2300 faces. Per-piece targets (quads, master):

| Piece class | Target |
|---|---|
| plain wall bay / road segment | 60-150 |
| detailed wall (timber frame, door or window) | 120-350 |
| corner, plinth, cornice, fence bay | 40-160 |
| roof run (4 m) with courses / eave | 100-260 |
| stairs (per flight of 8 steps) | 60-140 |
| hero piece (porch, market stall, gatehouse, arch bridge) | 300-900 |

Above ~1000 quads a "piece" is really a building: split it. Count only
what earns its place: dissolve/avoid grid lines that carry no shape.

Texture scale, median world units per texture repeat in the village
(use these as `tile` so the kit matches existing levels):
walls 2.5-3.4, roofs 2.1-3.0, interior floors/planks 2.3, timber
ornament strips 1.0, stone/cobble paths 3.0, ground 4-5.6 (grass fields up
to 7). Pick a tile that divides `BAY` cleanly where possible (2.0 or 4.0),
staying within about +-25 % of those figures.

## Material palettes (all verified present in the village file)

Pick **one style set per family** and keep to 3-5 materials per piece.

- **City timber house**: plaster `NW_City_Wall_02/03/05`, `NW_City_StuckWall_01`
  (**baked frame panels: crop, see below**); timber `NW_City_WoodBeam_01/02/03`,
  `NW_City_Wood_02` (greenish planks), `NW_City_Wood_Ornament_02` (128x512 strip: directional);
  stone `NW_Misc_Wall_01`, `NW_City_StoneWall_01/02`, `NW_Harbour_Wall_04`;
  roofs `NW_City_Roof_01/02/04/05`; interior `NW_City_InsideWall_11/12/13`,
  `NW_City_BodenDielen_01/02`, `NW_City_Roof_Inside_01`, `NW_City_Rich_InsideWall_01`.
- **Farm / rural**: `NW_Misc_Bauernhaus_01/04`, `NW_Seq_Misc_WoodWall_01`,
  `NW_Misc_Roof_01`, `NW_Seq_Misc_Roof_01`, `NW_Seq_Misc_StrawRoof_01`.
- **Harbour**: `NW_Harbour_Wall_04`, `NW_City_Hafen_Holzwand_01`,
  `NW_City_Hafen_Giebel_01`, `NW_City_Hafenkai_Boden_01`.
- **Stone / monastery / ruin**: `NW_Monastery_Wall_48`, `NW_Monastery_Ground_04`,
  `NW_City_Pflasterstein_01`.
- **Ground / road**: `NW_Seq_Ground_02_XL`, `NW_Seq_Ground_03`,
  `NW_Nature_Waldboden_03`, `NW_Nature_Path_02` (directional),
  `NW_Seq_GrassPath_01_XL` (directional), `NW_City_DirtyGround_01`.

Need something else (Old World, temple, swamp)? Search the library by name:
`with bpy.data.libraries.load(MATERIAL_LIB) as (src, _): [n for n in src.materials if 'keyword' in n.lower()]`.
Directional textures (beams, planks, treads, roads, roof courses, ornament
strips) use `set_directional_uv` with the piece's real grain axis; everything
else uses `set_grid_uv`. Never `uv.cube_project`.

## Making the textures belong together (learned the hard way)

The first wall looked wonky because the textures were picked by name.
**Look at every candidate texture before using it** (convert with
`sips -s format png X.tga --out X.png` and view it), then:

- **Many `NW_City_*Wall*` tiles are baked panels, not plain walls.**
  `NW_City_Wall_02/03/04/05`, `StuckWall_01/02`, `InsideWall_13`,
  `Rich_Wall_01` are a plaster field with a timber frame (and braces)
  painted into the border, meant to be mapped *once per wall panel*.
  Tiled across a wall they print a frame every 3 m and fight real timber
  geometry. Use `set_window_uv` to crop to the clean plaster interior
  (Wall_02: `window=(0.12,0.88,0.43,0.90)`, size `(2.4, 1.5)`), with a grid
  line on every mirror boundary.
- **Directional / strapped textures**: `NW_City_WoodBeam_01` is a 256x512
  beam with an iron strap at v~0.75 -- crop to `(0.06,0.94,0.05,0.70)` so
  the strap doesn't repeat, and use `swap=True` on horizontal beams so the
  grain runs along them.
- **One palette per piece**: plaster + timber + stone that share hue and
  value (here warm grey plaster, dark brown beams, brown-grey slate stone:
  `NW_City_Wall_02` / `NW_City_WoodBeam_01` / `NW_Misc_Wall_01`). Two
  greens or a black timber next to a brown one reads as a mistake.
- **Same texel density across materials, and sharp**: aim for ~250-300 px
  per metre on 512 px textures (the village's ~165 px/m reads blurry up
  close). Pick `set_window_uv` sizes to hit that, and put a grid line at
  every mirror line. Narrow members (beams, jambs, posts) pass
  `origin=` = the member's own edge on the across axis so they never
  straddle a mirror line.
- **Whatever the user swapped in is theirs**: read the object's current
  material slots before a rebuild and reuse those material objects (see
  the top of `build_walls` usage in `wall_bay.py` (mats param)); never re-assign by name.
- **Tiles with a cornice/border band** (e.g. `NW_Misc_Strong_StoneWall_Top_01`)
  need the crop too, or the band repeats.

## Making it look built, not generated

- **All raised regions come from ONE `extrude_faces` call.** Two adjacent
  regions extruded separately leave two coincident side sheets (a crevice
  and a pole). Extrude everything at a common depth, then give each region
  its own relief by moving cap vertices in depth (a vertex shared by two
  regions takes the deeper one), so stone, timber, sill and eave flow into
  each other welded. Header beams, jambs, sills and the eave are then one
  connected timber skeleton, not planks stuck on.
- **Stepped chamfer**: `inset(caps, 0.028, depth=0.03)` on the whole raised
  region gives every timber/stone edge a visible bevel step for the cost
  of one ring.
- **Irregularity from vertices, not polygons**: `jitter()` on raised verts
  (stone more, timber less), bowed posts, a sagging eave, slightly wobbly
  opening edges (`share_y=True` so reveals stay planar). Use `period_x=BAY`
  and `keep_planes` so snap faces still mate. Keep opening wobble under
  ~0.01 m or it reads as broken, not aged.
- **Break the light where materials change.** A stone-to-timber (or
  timber-to-sill) joint on one continuous surface looks pasted on. Leave a
  ~4 cm groove row between the two raised regions (a grid row that is NOT
  raised, so it stays at the wall plane): both sides get real side walls
  and a shadow line. Regions that need to read as one piece (jamb-to-lintel,
  post-to-eave) stay welded with no groove.
- **Materials must agree with the shape.** A board-shaped, projecting sill
  or step is a *plank*: give it timber on every face (front, top, ends) and
  carry it through the wall thickness (the reveal floor under a window is
  the same wood; under a door it is the stone step). A stone-textured plank
  reads as a rendering error. Join same-material members (jambs, lintel,
  sill) into one welded frame with no groove; grooves are for material
  changes only.
- **Lean mesh.** Uniform grids are wasteful: the back of a wall is flat and
  needs almost no lines. Use `slab_lean(...)` (own coarse back grid; reveals,
  top and bottom are bridged with quads where the vertex chains line up and
  triangles where they don't -- tris ONLY on those flat bridge planes, never
  on relief). Put only geometry-carrying lines in the front grid; get UV
  mirroring for free with `set_window_uv(bounds=...)` on lines that already
  exist, `set_wrap_uv` for tileable stone, `set_beam_uv` for beams (the iron
  strap then repeats as bands, which reads as ironwork). Never add a grid
  line just to satisfy a UV mirror. 902 -> 406 faces on the wall bay.
- **Layered relief**: plaster recessed, timber proud, eave proudest, stone
  footing and projecting sill: at least four depth layers on one bay.
- **Reference recipe**: `scripts/wall_bay.py` builds
  every wall bay this way (406 faces, one component, 0 poles). Copy
  its structure -- `tag()` region classifier, single extrusion, depth by
  region, inset chamfer, jitter, then material + UV by face tag.

## The weld contract (pieces are merged into one mesh by the user)

The user places pieces on a 0.2 m grid, joins them and runs Merge by Distance.
So every seam must be **the same vertices in the same positions on both
sides**, and **no piece may overlap another** (overlapping timber "adds up"):

1. **Identical end loops.** Every wall bay of a storey carries the same rows
   on its two snap planes (`ZS_END` in `wall_bay.py`, forced into
   `planar_partition`), the same half-width end posts (0.15), regions never
   merge across the end-post columns (`split_x`), and verts on the snap
   planes use piece-independent jitter seeds. Any bay of the storey welds to
   any other. Verify: the (y, z) point sets at x=0 and x=4 must be equal
   across all variants; a stray extra vertex means a rectangle corner leaked
   onto the snap plane.
2. **Derive, don't redraw.** Pieces that meet another piece's loop are
   generated FROM that loop (`weld_pieces.py`): the corner block is a mitre
   sweep of a wall end loop (0.4 m = one wall thickness, walls start 0.4 m
   from the corner, nothing overlaps); the roof end cap is the roof run's
   end loop swept 0.7 m and closed (cap bridged with `_stitch`, no
   contextual_create/triangulate: it breaks on concave outlines).
3. **Symmetry where a piece is reused rotated.** The roof run's noise is
   mirror-symmetric about y = W/2 so the same end cap fits both ends after a
   180 deg turn. Anything reused under rotation/mirroring needs this.
4. **Solid, not sheets.** Roof slab 0.22 m thick with stepped courses,
   closed at building ends. Open boundary loops are allowed ONLY at
   declared snap planes.
5. **Gable and roof are ONE welded system**: the roof run's attic cavity outline
   carries vertices at the gable's grid columns (course stations) and at the
   rafter row, and `build_roof_end_gable` builds the closed end piece FROM the
   run's end loop: outer verge, open overhang, recessed gable face with frame,
   a solid plug and an interior back face. Never build a gable as a separate
   plug whose top/side coincide with the tunnel surfaces; they would not share
   vertices (a 1 mm merge cannot weld them).
6. **Butt joints that cannot weld** (wall top vs roof skirt or upper wall: their
   outlines differ) must still be flush and non-overlapping; document that
   interior faces remain.
7. **Test it, don't assume**: place linked copies per the guide's table
   (call `bpy.context.view_layer.update()` first or matrix_world is stale),
   join into one bmesh, `remove_doubles(dist=0.001)`, and count open /
   non-manifold edges. The house must give 0 open (>2-face) edges; distinguish
   from harmless single-face OPEN edges at the true envelope limit (ground
   contact, wall-to-roof) -- `len(e.link_faces) > 2` is the real bug signal,
   `== 1` at those two places is expected.
8. **A grid line kept alive lower down is still alive higher up.**
   `protect_x` in `tensor_partition` protects an x LINE across every z row,
   even a row where nothing needs it (the end-post columns 0.15/3.85 have no
   reason to exist in the uniform eave band, but stay there anyway). If two
   different pieces both carry that leftover line exactly on a shared snap
   plane (a storey seam), Merge by Distance welds their two copies into one
   vertex with 3-4 linked faces. Fix at the source, not with a bigger merge
   distance: nudge the leftover interior vertex off the plane (opposite
   directions on the two sides, e.g. `±0.006`), or -- better, see next point
   -- remove the reason the seam doesn't already match.
9. **A storey seam only welds fully if both sides are the SAME shape
   there.** A cornice (eave) and a sole plate are different 3D reliefs, so
   only their flat back corner used to coincide when stacked; most of the
   seam stayed open. Stop each relief `LIP` short of the true z = 0/top row
   (e.g. 0.02 m) so the row itself is flat, unrelieved and identical on both
   sides -- then the WHOLE seam welds, not just two corners. Keep the
   feature's own tag() check consulting the shortened range, not a blanket
   `z > band_start` that ignores the lip.
10. **A corner/end piece derived from another piece's loop must stay an open
    tube like the piece it came from.** Sweeping (e.g. mitring) EVERY edge of
    a closed boundary loop also sweeps its top- and bottom-closing edge into
    an unwanted lid; skip any loop edge whose two ends share the same
    z = 0/top plane. A capped corner duplicates whatever piece closes that
    volume from the other side (a roof end's attic-plug floor, a floor
    tile's own rim) and both copies show up non-manifold once welded.
11. **A beam/grain UV keyed off a single world axis collapses on a diagonal
    or tiny face.** `set_beam_uv` used to read its "across" coordinate from
    one world axis chosen by the face normal; a mitred corner strip (or any
    small end-cap face) can have almost no extent on that axis while still
    being wide in 3D, so the UV shrank to a sliver (world-area/uv-area
    ratios over 1000x measured). Derive along/across from the FACE'S OWN
    edges instead (whichever is closer to the grain axis is along) so a
    square-on face reduces to the old formula exactly and a diagonal one
    still gets its true width.
12. **A UV formula must branch on the FACE, not on each vertex.** Picking a
    different mapping per-vertex from that vertex's own position (instead of
    once, from the face centre) lets one quad straddling the boundary get
    two different formulas across its own corners -- a real shear, not a
    scale issue, so a simple world-area/uv-area check won't catch it
    (`find_stretched_uv_faces`'s anisotropy check does: same-face edges that
    scale differently between world and UV space). Evaluate the branch once
    per face and apply it to all of that face's loops.
13. **Four surfaces CAN genuinely need one edge.** Tried making an upper
    wall's own top weld to the roof run above it (gave both a matching flat
    soffit strip, same width, same z). It worked -- except at every bay-to-bay
    and corner column, where the wall's sideways neighbour-bay weld and the
    roof's own run-to-run weld ALSO land on that exact edge: four caps
    (wall bay 1, wall bay 2, roof run 1, roof run 2) converging on one line,
    but a manifold edge holds only 2 faces. Welding wall-to-roof there broke
    the bay-to-bay weld instead (open edges traded for real overlaps, worse).
    No per-vertex nudge fixes this: it's not misalignment, it's a genuine
    4-valent line in the topology as designed. Left as a flush, non-welded
    touch (documented, expected, harmless) rather than force a weld that
    costs a weld somewhere else. If this needs solving, it wants a structural
    change (e.g. a real fascia board piece bridging wall-to-roof that owns
    that edge on both sides), not a coordinate nudge.
14. **A geometric helper's "0" is often really "wherever this piece's own
    reference plane happens to be."** `build_corner_from_bay`'s mitre math
    hardcoded the bay's front plane at local y=0 and its far mitre plane at
    y=T (`T=WALL_T`) -- true for every bay so far, but a jettied bay is the
    SAME wall shifted outward as a whole, so its front is at y=-JETTY, not
    0. Fix generalized to `y0 + T` (`y0` = the bay's own front-plane
    offset), reducing to the original formula exactly when y0=0. Getting
    `y0` right mattered: `min(loop.y)` looked right but isn't -- a bay's x=0
    boundary loop includes its RELIEF points too (the eave/timber caps
    project further out than the flat front plane), so the true minimum is
    contaminated by whatever detail happens to stick out furthest. The
    BACK plane (`max(loop.y) - T`) is reliable instead: relief only ever
    projects forward, never backward, so nothing ever sticks out past it.
15. **A UV branch selects a face's own formula from a KNOWN vertex
    duplication, not from position matching.** A dormer's front-wall grid
    and its 4 outer corners (reused for the cheeks/roof) must be the SAME
    BMVert objects, not separately-created vertices at coincident
    positions -- bmesh never merges those on its own, so two "the same
    point" verts stay two different, disconnected points until an explicit
    `remove_doubles` (which a single piece's own build never runs). Build
    the shared grid first and index into it (`FV[(0,0)]` etc.) for anything
    that needs "the same corner," rather than calling the vertex
    constructor twice with the same numbers.
16. **Matching endpoint POSITIONS is not matching an EDGE.** Tried building
    a fascia board whose bottom edge runs from the wall's (0,0,3) vertex to
    its (4,0,3) vertex, on the theory that the LIP fix (lesson 09) put a
    flat, weldable row exactly there. It doesn't: the LIP row is a set of
    points where several *different* branching zigzag edges (the eave cap's
    relief, one row below) happen to touch z=3, not one continuous edge
    spanning the bay. Checked directly: the wall's own (0,0,3) vertex has 3
    `link_edges`, none toward (4,0,3) -- two short open stubs to relief
    points below it, one already-closed internal edge. `remove_doubles`
    happily merges the two endpoint vertices (they really are at the same
    position) but that doesn't create or consume the long edge between
    them, so the open-edge count doesn't drop even though nothing overlaps
    either. A weld needs a piece to contribute the SAME edge, not just the
    same two endpoints; if the target boundary branches, either replicate
    the branching exactly (piece-specific, not a shared trim board) or,
    honestly, build a surface-mounted piece instead (see `build_chimney`/
    `build_dormer`) and don't claim it reduces the open-edge count. See
    `scripts/fascia.py`'s module docstring and `TRIM_FASCIA_A` in the kit.
17. **A derived corner's own weld-edge distance is NOT always the T you
    passed in -- read it back before trusting a placement offset.**
    `build_corner_from_bay` computes `T_new = y0 + T` where `y0` is the
    bay's own back-plane y (lesson 14) -- for a normal wall (back plane at
    WALL_T) this reduces to the input T=0.4 exactly, which is why
    `house_placements` could get away with a single hardcoded 0.4 m
    wall-to-corner offset for years. A JETTIED wall's entire profile,
    front AND back, is shifted outward by JETTY, so its own back plane
    sits at WALL_T-JETTY (0.25, not 0.4) -- and so does its corner's
    T_new. Placing `UPPER_JETTY_A` + `CORNER_JETTY_A` with the same 0.4 m
    offset used everywhere else leaves a real, un-welded 0.15 m gap at
    every jettied corner: standalone `check_piece()` on the corner passed
    clean (it only checks the corner's OWN manifold-ness, not that it
    actually meets its wall at the offset a placement script assumes), so
    this shipped undetected until a direct two-piece merge test (build the
    wall + corner at their real relative placement, `remove_doubles`,
    check whether the open-edge count actually DROPS below the sum of
    their standalone counts) caught it. Fixed by parametrizing
    `house_placements`' corner offset (`upper_off`) instead of assuming
    0.4 always applies, and deriving the SPAN (corner-to-corner distance)
    from that same offset so both ends of a wall run stay consistent.
    General lesson: whenever a piece is placed at an offset that came from
    a DIFFERENT piece's own derivation (not a fixed module constant),
    verify with an actual merge test, not just each piece's own
    `check_piece()` -- the two checks catch different bugs.
18. **A corner's `nudge_top`/`nudge_bottom` choice depends on what's ABOVE
    it, not just what family it's in.** `CORNER_A` (ground) is built with
    both nudges off, because in every house so far its top welds to an
    UPPER corner stacked on it (a real weld, shouldn't be nudged) and its
    bottom sits on bare terrain (also fine unnudged). A single-storey
    cottage (no upper storey) breaks that assumption: the ROOF/GABLE sits
    directly on the ground corner instead, which is exactly the situation
    `nudge_top=True` exists for (lesson 13's "four caps, one edge" -- the
    corner's own un-nudged top lip, the roof, and the gable all land on
    the same z=3 line, one too many for a 2-face manifold edge). Found via
    a house-level merge test (3 overlapping edges per corner, 4 corners),
    not either piece's own `check_piece()` -- same general lesson as #17,
    a corner's correctness depends on ITS PLACEMENT CONTEXT, not just its
    own geometry. Fixed with a dedicated `WALL_CORNER_SOLO_A`
    (`nudge_top=True, nudge_bottom=False`), derived from the same ground
    wall bay boundary loop as `CORNER_A` -- use it for any building whose
    roof sits directly on the ground floor, `CORNER_A` only when there's a
    real upper storey above.
19. **A house composition can be made rotation-generic for free, by
    building it at a local origin and wrapping the WHOLE placement list in
    one outer transform, instead of hardcoding which world direction each
    wall faces.** `house_placements`/`small_house_placements` each
    computed world-space matrices directly (`M(x0+off, y0, z, 0)` etc) --
    correct, but only for ONE fixed orientation (gable sideways). Nothing
    about a wall bay, a corner mitre, or a roof run actually cares which
    world direction it faces; the ONLY thing that mattered was that the
    section's own internal S/N/E/W/corner math stayed self-consistent.
    `section_placements` builds every piece at LOCAL coordinates (origin
    0,0, exactly the old math with x0/y0 zeroed out) and returns
    `[(name, outer @ local_mat) for ...]` where `outer = M(x0, y0, 0,
    rot)` -- one matrix multiply per piece, applied after the fact.
    Verified equivalent to the original by a direct merge-test comparison
    (same wall spec through both functions: identical face count, 0
    overlap, identical open-edge count) -- then verified the NEW
    capability (rot=90) merge-tests the same too, since a rigid rotation
    can't change a mesh's own topology. This is what let a row-house unit
    (gable facing the street) and a plain house (gable facing sideways)
    become the SAME function call at a different `rot`, instead of a
    second hand-written composition. Which world direction `rot` actually
    points a given local wall was determined empirically (place one test
    instance, read back a recognisable object's world position, e.g. the
    door), not derived by hand from the rotation matrices -- faster and
    less error-prone than tracking local/world axis correspondence through
    two composed rotations by hand.
20. **"Separate roofs, no valley" is a real, honestly-scoped way to build
    non-rectangular footprints before a true roof valley exists.** An
    L-shaped building is two `section_placements` sections (one at
    `rot=0`, one at `rot=90`) positioned so their footprints share a full
    wall-length edge, each keeping its own complete, independent roof.
    Where the two sections' own walls land back-to-back at that shared
    edge, BOTH sections contribute a full wall (+ corner blocks, + a
    gable-end roof) there -- a real, deliberate doubled-geometry overlap,
    not a bug to chase to 0. Same trade-off row houses make at every
    party wall between units (each unit is its own complete
    `section_placements` call, gable end included, placed edge-to-edge --
    checked visually, not just by the overlap count, since two coincident
    opaque faces CAN look fine in practice, which they did here). Treat
    an L-shape/row-house merge's overlap count as EXPECTED and roughly
    proportional to the number of internal shared edges, not as a
    regression to fix -- the real check for these is a screenshot at the
    join, not `check_piece`'s or `build_house`'s usual "0 overlap" bar,
    which still applies to everything else. A true single-roof valley
    over an L footprint (no doubled wall, one continuous roof surface)
    remains unimplemented -- it needs the roof's own cross-section sweep
    to miter at the inside corner, materially harder than anything above.
21. **`bmesh.ops.grid_fill` does not reliably cap a regular N-gon --
    verify it, don't assume it.** Tried it first for an octagon tower's
    spire tip and foot ring (an 8-edge closed boundary loop, passed as
    `edges=`): it silently returned ZERO faces on a plain regular octagon,
    no error, easy to miss (`check_piece` still flagged `ngons_bad`/open
    edges afterward, which is what surfaced it). Grid Fill is built for a
    loop with 4 dominant corners it can read as a rectangle's own
    boundary, not an N-sided shape with no dominant corners at all -- a
    regular octagon has none. The reliable, general technique instead:
    pair up adjacent ring verts (0,1)(2,3)(4,5)(6,7), inset each pair's
    own midpoint toward the centre to build a 4-point inner square,
    triangle each aligned pair into its own inner point (4 triangles,
    unavoidable -- same "no clean quad alternative" tier as the dormer's
    cheeks or the road junction's mitre fan), quad each gap between one
    pair and the next across to the two neighbouring inner points (4
    quads), then cap the resulting plain square with one final quad. This
    closes ANY even-sided regular N-gon with quads-plus-N/2-triangles and
    no pole, reusable wherever a "round" (in practice: octagonal) cross-
    section needs a flat cap -- see `scripts/village_pieces.py`'s `_cap`.
22. **`_stitch(bm, F, B, key)` degenerates into a FAN (a real pole) the
    instant one chain has a wide gap in `key` with no intermediate points
    while the other chain has many points across that same span --
    `check_piece`'s own `poles_bad` metric does not reliably catch it, so
    verify with a direct per-vertex `len(v.link_faces)` count, not just
    the summary field.** This took THREE attempts to get right on
    `build_roof_end_gable`'s outer end-cap (`weld_pieces.py`), each one
    only caught by looking harder, so the failure history is worth
    keeping:
    - **The original bug**: the end-cap closes the roof-end's silhouette
      by walking `boundary_loop`'s ring from the min-y point to the max-y
      point in each direction ("up"/"dn") and stitching the two arcs
      together -- correct ONLY when the ring is a plain loop.
      `build_roof_run`'s own boundary at x=0 is a "keyhole" (the outer
      roofline PLUS a slit into the inner attic/notch profile, spliced
      into one ring), and one of the two arcs detours through that slit,
      its z climbing almost as high as the true outer roofline -- stitching
      it straight against the true outer arc self-intersects into a
      "crown of thorns" of crossing triangles at both eave corners.
    - **Attempt 1 (still broken)**: filtered "dn" down to its own low
      points (z <= KNEE), dropping the notch detour entirely and leaving
      a clean, single 15-edge OPEN loop there instead of closing it. This
      alone checked out clean on every `check_piece` field and looked
      right in a side-silhouette screenshot -- but a per-vertex check
      (only added after attempt 2's failure showed the summary field
      couldn't be trusted) found a vertex with 20 linked faces: with the
      wide gap unfilled, `_stitch`'s zipper (it only advances whichever
      chain's NEXT point has the smaller `key` value) fans every one of
      "up"'s ~15 points in that span off the single "dn" anchor before
      the gap. A silhouette-only screenshot doesn't reveal a fan viewed
      nearly edge-on; a front/corner 3-4 view (or the per-vertex count)
      does.
    - **Attempt 2 (worse)**: tried to close that gap with a second
      `_stitch` call against a 2-point chord (just the gap's two
      endpoints) -- exactly the same fan mechanism, now with only 2
      points on one side instead of a handful, producing a dramatic
      13-face fan from one vertex. This is the one that actually shipped
      broken and had to be reverted from the live kit file.
    - **The real fix**: keep the gap-detection idea from attempt 1, but
      wherever a gap in "dn" is wider than one course step
      (`COURSE_DY`), insert flat (z=0) placeholder points at each of
      "up"'s own y-values inside that gap -- giving both chains
      comparable point density across the WHOLE range, so the zipper
      pairs them step by step instead of fanning. Verified this time with
      a per-vertex `len(v.link_faces)` sweep (max 6, matching the
      pre-existing baseline) on the isolated piece, on all 3 retextured
      copies, AND on every merged house in the showcase (checking
      specifically in the roof-height zone, since a merged multi-piece
      house has other legitimately-high-valence points elsewhere, like
      floor-tile corners and row-house party walls, that aren't the bug
      being hunted) -- not just `check_piece`'s summary.
    - Caught the ORIGINAL bug from a user report ("elements stick out of
      the house silhouette"), not from `check_piece` -- a self-intersecting
      fan still closes every edge exactly twice, so every `*_bad` field
      reads 0 regardless. Caught attempt 1's fan (before it shipped) and
      confirmed attempt 2's shipped fan (from a second user report, after
      it visibly broke the piece further) the same way: a per-vertex link-
      face count, not the check_piece summary. **Lesson: for any fix that
      touches `_stitch`, `check_piece`'s `poles_bad` field is not
      sufficient evidence of no pole -- always also run a direct
      `max(len(v.link_faces) for v in bm.verts)` sweep before trusting the
      result, on the isolated piece AND on anything it gets merged into.**
    - Separately: when copying a fixed base piece's mesh onto a
      retextured variant's OWN object (`ob.data = base.data.copy()`),
      replace materials by INDEX (`new_mesh.materials[i] = mat`), never
      `materials.clear()` + `.append()` -- clearing a mesh's material list
      to zero slots immediately clamps every face's `material_index` to
      0, even before you re-append anything, silently collapsing the
      whole piece onto one material.
    - **UPDATE, same day: the whole attempt was reverted.** Once
      topologically correct (attempt 3 above), the user looked at it and
      said the redesigned cap simply didn't look good -- a judgment call
      on the shape itself, not a remaining correctness bug. `weld_pieces.py`'s
      `build_roof_end_gable` was reverted verbatim to its pre-session form
      (confirmed byte-identical via git diff against the last commit that
      touched it, `017b8b1`), and cross-checked against the actual
      geometry still sitting in `NW_SAMPLE_LEVEL_2HOUSES.blend` (a file
      never rebuilt this session, so it preserved the untouched original)
      -- same corner, screenshotted, pixel-for-pixel the same detail. So
      the ORIGINAL self-intersecting outer-cap fan is back, unchanged from
      how this kit always shipped it, `poles_bad` reading "2" both before
      today's whole excursion and after the revert (that field was never
      sensitive to this either way). The technical finding above (the
      `_stitch` fan-degeneracy mechanism, and that `poles_bad` can't be
      trusted alone) remains true and worth knowing for any FUTURE
      `_stitch` work -- it's just that fixing THIS piece's cap is no
      longer wanted; don't re-attempt it without the user explicitly
      asking again, and if asked, show a mockup/isolated-piece screenshot
      before touching the live kit, since "technically correct" and
      "looks good" turned out to be two different bars here.
23. **A retextured/reused material can be wrong for a *specific* small
    part even when it looks fine everywhere else in the kit.**
    `WALL_WINDOW_SHUTTER_A`'s open-shutter panels reused `NW_City_Door_01`
    (chosen for its generic wood-plank look) at a UV scale that, on a
    panel only `SHUTTER_W=0.32` m wide, cropped in on the texture's own
    door hinge-and-lock hardware decal -- putting a door fitting on a
    window shutter, in that texture's off-palette hinge colour against
    the rest of the piece's aged dark timber. Not a stretched-UV bug
    (`check_piece`'s anisotropy/area checks don't catch "the right pixels,
    wrong feature" -- they only catch distorted scale) and not fixable by
    retexturing (no other stock texture is a better fit for two small
    panels this size) -- fixed by dropping the shutter members entirely
    (`window_dress.py`'s `shuttered_window_members`/its `extra_members`
    wiring) and keeping just the carved-ornament jamb, which reads fine on
    its own. When a texture crop is the actual problem, check what
    non-repeating FEATURES (hardware, grain knots, damage marks) the
    crop's UV window lands on at the piece's real on-screen size, not just
    whether the numeric UV stretch factor is in range.
24. **Regenerating an asset's preview thumbnail one object at a time
    (`bpy.ops.ed.lib_id_generate_preview_from_object()` inside
    `temp_override(id=ob)`) is NOT enough to target that specific object
    -- it also needs `ob` to actually be the ACTIVE and SELECTED object,
    not just the override's `id`.** Regenerated all 75 kit pieces'
    previews this way, one per call, verified each one's pixel buffer was
    non-blank -- but never checked that the CONTENT was actually of the
    right object. It wasn't: `context.id` decides where the result gets
    stored, but the render itself reads from `context.active_object`/
    `context.selected_objects`, which stayed on whatever was last active
    in the viewport from earlier debugging -- so most of the 75 previews
    ended up as copies of a couple of unrelated pieces' renders. A
    "non-blank pixels" check can't catch "blank but plausible-looking
    WRONG content" -- confirmed by building a montage of every piece's
    actual preview pixels tiled into one image and looking at it, which
    is the reliable way to spot this class of bug (not spot-checking a
    couple of pieces, which can easily land on ones that happened to be
    active/correct by chance). Also: **Blender has a proper BATCH
    preview-regeneration operator, `bpy.ops.wm.previews_batch_generate()`
    -- use it instead of a manual per-object Python loop.** It takes
    `directory` + `files` (scope it to just the one `.blend` you want,
    not the whole folder) and `use_objects`/`use_collections`/
    `use_scenes`/`use_intern_data` toggles; it processes the file as a
    background job and re-saves it with correct, properly-isolated
    previews for everything in one call -- no per-object active/selected
    juggling, no risk of the "renders whatever was last active" bug
    above, and it's what Blender's own File Browser uses for "Batch
    Generate Previews", not a workaround. The resulting renders are
    dimmer/flatter than a hand-framed Material Preview viewport
    screenshot (different render pathway, a plain default light rig) --
    that's a cosmetic difference, not a bug; don't chase it. After
    running it, reload the file fresh (`bpy.ops.wm.open_mainfile`) before
    trusting anything about it, including the Asset Browser panel's own
    display, which can show a stale "No items" state from before the
    file was last saved+reloaded even when the underlying data is fine.

## Building pieces that compose into a house

`scripts/wall_bay.py` (`build_wall_bay`) is the parametric wall bay (ground
or `storey="upper"`): give it window/door x-ranges and studs; z-ranges are fixed
to the shared rows (see the quads-only section) and every bay has a mid rail. It
meshes flat areas with `tensor_partition`. An opening dict's `trim` key swaps
its jamb from plain "timber" to any other registered kind; `spec["extra_members"]`
(more `(x0,x1,z0,z1,orient,kind)` tuples), `spec["extra_kinds"]` (their material
slot names) and `spec["extra_uv"]` (`{kind: fn(face, uv_layer, member)}`) add
NEW kinds of relief (shutters, an ornament trim...) without editing
`build_wall_bay` per piece -- see `scripts/window_dress.py`. Both are
additive/backward-compatible: omit them and a call behaves exactly as before
(verified against all 9 pre-existing wall pieces after adding them).
`scripts/roof_gable.py` has `build_roof_run`, `build_chimney` and the shared
`roof_slope_uv`; `build_gable` and `build_corner_post` are superseded (integrated
end piece, mitre corner block). `scripts/floor_tile.py` has `build_floor_tile` (`closed_x0=True` = END tile). A floor with an open end is not manifold after merging, so floors are two END tiles (one turned 180 deg) plus open tiles between; ground floor top z = 0.46 (footing top = door threshold). Anything reused turned 180 deg about z must be mirror-symmetric (see the roof run).
`scripts/jetty.py` builds a jettied upper wall by calling `build_wall_bay`
NORMALLY, then translating the whole finished piece -- relief, jitter and
all -- outward as one step; no changes to `build_wall_bay` itself needed.
Its corner uses `build_corner_from_bay` the usual way (see lesson 14 above
for why that function had to generalize first).
`scripts/ruin_wall.py` builds a broken wall bay by treating each zone's
missing-material region as an "opening" that runs off the top of the
domain, reusing `slab_planar`'s own front/back/reveal/side machinery rather
than a bespoke jagged-silhouette extrude (which turned out NOT to cap
correctly on its own -- see the script's own history if reviving that
approach).
`scripts/dormer.py` builds a roof dormer as a self-contained piece that
sits ON an existing `ROOF_RUN_A`'s slope (reading the same `zu()`/KNEE/TAN
the run itself uses, the same "saddle follows the roof" trick
`build_chimney` already uses), rather than requiring the run to have a
literal hole cut into it.
`scripts/fascia.py` builds a surface-mounted timber fascia board
(`TRIM_FASCIA_A`) for the upper wall-to-roof seam -- the same touches-
but-doesn't-vertex-weld relationship as `build_chimney`/`build_dormer`,
NOT a real weld (see lesson 16 above for why a true weld there isn't
achievable without piece-specific work). Place it at the same transform
as the wall bay it's finishing.
`scripts/ruin_debris.py` has `build_rubble_pile` (a height-field grid, top
cap only -- no sides/bottom, it sits IN the ground the way any rubble
scatter mesh does) and `build_fallen_beam` (a station-based ring sweep,
same technique as the dormer/beam pieces below -- rough silhouette jitter
reads as "broken," not a modelled fracture). Neither is on a weld
contract; both are freestanding scatter next to `WALL_RUIN_A`.
`scripts/civic_pieces.py` has `build_sign_post` and `build_bell_tower`,
both freestanding (chimney/dormer pattern, not welded). The sign post is
ONE continuous ring-sweep (post -> arm -> board), not three separate
boxes -- see lesson 15 (shared verts, not coincident ones) and lesson 16
(matching positions isn't matching an edge) for the two specific bugs
that approach hit along the way: reusing 2 of the post's own top-ring
verts as the arm's own base ring needed the post's own matching face
OMITTED (not just skipped-and-re-added) or the shared ring edge gets a
3rd face; and two rings meant to meet at the same seam z, built as two
SEPARATE ring calls, are coincident but not shared -- a face spanning
both collapses to zero area. The bell tower's spire is a FRUSTUM (a
small flat ring at the top, capped), not a single-point pyramid, so
there's no pole at the apex.
`build_corner_from_bay` also derives `WALL_CORNER_SOLO_A` (a
`nudge_top=True` ground corner for single-storey buildings -- see lesson
18) from the same wall bay boundary loop `CORNER_A` uses; and the civic/
sacred wall variants are plain material-slot re-assignments on COPIES of
the existing wall_bay/corner objects, no new geometry or `check_piece`
re-verification needed (same mesh, same UVs, only the slot -> material
mapping changes). The row-house RH1/RH2 and farm/burgher/thatch variants
(`village_pieces.py`'s companions, still plain retexture-copies of the
residential wall_bay/roof geometry) follow the exact same pattern.
`scripts/village_pieces.py` has `build_round_tower` (an octagonal
freestanding watchtower/dovecote -- "round" from a shaft that's actually
an 8-sided quads-only prism, belfry band, frustum-capped spire, same
no-pole trick as the bell tower) and `build_well` (a simple octagonal
stone ring + water cap; an earlier version's 4 free-standing roof posts
either stayed disconnected components or, once welded to the rim, pushed
several rim verts to a genuine 6-quad pole -- dropped rather than force
either compromise, see lesson 21's own `_cap` for the octagon-closing
technique both pieces need for their own flat caps). Both pieces, and all
the retextured wall-bay variants above, were designed by studying
NW_VILLAGE_01 (the project's own reference asset) directly via the
Blender MCP -- its own layout (buildings scattered at varied angles
around a central well, not a grid), material list, and building shapes,
not guessed at.
`scripts/weld_pieces.py` has `boundary_loop`, `build_corner_from_bay`,
`build_roof_end_gable`. Assembly contract (user table in
`documentation/KIT_USER_GUIDE.md` section 7): 3 m ground floor, 0.6 m knee,
38 deg pitch, 4.8 m outer depth, 0.4 m corner blocks, 0.2 m grid.
`scripts/terrain_road.py` has `build_ground_tile` (flat grass / bare yard)
and `build_road_tile` (straight / junction): flat 4 x 4 m quad grids on their
own weld contract (every tile shares the same z = 0 boundary loop on all
four sides), separate from the house -- see "Ground and road tiles" in the
user guide. A rotated tile's footprint must stay pinned to its own grid
cell: rotate about the TILE'S CENTRE, not its corner (`GM()` in
`build_two_house_level.py`), or a 90 deg turn shifts its footprint a whole
tile-width off the one the layout meant, overlapping the neighbour.

Lessons:
- **Non-rectangular outlines (gables) use a mapped grid**: put vertical
  lines where you need them and give each line its own row heights so every
  column has the same row count and every cell is a quad; back face = two
  coarse trapezoid quads bridged with `_stitch`.
- **Sweep profiles for roofs**: an ordered point ring with a "kind" per edge
  swept along x (2 segments), x fixed at the open ends. Shingle courses are
  a sawtooth in the profile with UVs from the profile.
- **Compose before polishing**: after 3+ new pieces assemble linked copies
  and look from front and back; snap and proportion bugs only show there.
  A picture-perfect house that does not weld is a failed kit.

## Reducing quads on flat surfaces: quads only, never fans

The first attempt (`planar_partition`: merge cells into rectangles and bridge the
extra boundary vertices with triangles) produced fans of thin triangles and high
valence poles at every transition. **Do not do that on any visible surface.**
Rules that work (`tensor_partition` / `slab_planar` in `kit_lib.py`):
- A flat area is a grid whose REDUNDANT lines were dissolved: a line is
  redundant only if every cell pair it separates has the same region id (or is
  void on both sides). Removing it merges whole columns/rows into bigger quads,
  so there are never T-junctions, triangles or poles. Nothing is removed
  "locally".
- Quad meshes cannot be graded smoothly from many rows to few (parity), so make
  the layout itself need few lines: **design every opening on rows that already
  exist** (sole rail, mid rail, eave, footing). Ground window = between the sole
  rail and the mid rail, upper window = between the sole plate and the mid rail,
  door = footing top to eave beam. A mid rail on every bay is real geometry that
  also gives every bay the same end rows. No row exists just for one opening.
- The back face uses its own coarse grid (only opening edges, end columns,
  all rows); reveals stay 1:1 quads with the front.
- Triangles are allowed ONLY on hidden flat strips (wall top/bottom, the plug
  floor inside a roof end, the closed roof cap). Visible planes are all quads.
- Result: wall bays 200-380 faces, all quads except 8-12 hidden triangles.

## Roof UVs must be even

Use one mapping for the whole roof: `roof_slope_uv(y, z)` = distance along the
slope, one course = 0.25 of the 512 px tile, u = x * 0.5. Do not assign v per
profile edge or per piece (steps get zero area, end caps stretch). The end cap
continues the run's u across the weld: u = (x - length) * 0.5. Closed end faces
(normal along x) use a planar (y, z) wrap, never a beam mapping with x as the
long axis (that streaks).

## Piece families (build order)

1. **Walls** -- plain, door, window, double window, half-timber (Fachwerk),
   stone-base + timber-upper, corner post (outer + inner), wall end/gable
   wall, plinth/foundation strip.
2. **Roofs** -- straight run, ridge cap, hip corner, gable end, eave/dormer,
   chimney (square stack, no cylinder poles), lean-to.
3. **Openings & trim** -- door frame + step, shutter set, window box, porch
   with posts, balcony, external stair.
4. **Floors & interiors** -- floor tile bay, ceiling beams, interior wall bay,
   staircase (straight/L), fireplace.
5. **Streets** -- straight, corner, T, cross, ramp, stepped ramp, gutter/edge,
   cobble patch, path end-cap blending into grass (matching edge vertices).
6. **Street furniture** -- fence bay + gate + post, well, market stall,
   signpost, lamp post, cart, barrel/crate stack, hitching post.
7. **Big structures** -- arched gate/bridge, tower base + top, stone wall
   with battlements, harbour pier bay + mooring post, ruin chunks
   (broken walls, fallen beams).

## Workflow (via MCP)

1. **Brief (write it down before touching Blender).** Family, style set,
   bounding box in cells, snap planes, origin, 3-5 materials, and the *design
   idea* in one sentence (see "Quality bar"). If the user gave a loose
   request, pick something specific and say what you picked.
2. **Plan the grid lines.** Collect every x and z where an opening edge,
   timber edge, sill, plinth step or panel inset must fall; merge with
   `lines_from(...)`. This is the only re-gridding decision -- do it before
   building. Openings are `(x0, x1, z0, z1)` rectangles on those lines.
3. **Base slab.** `slab_from_mask(bm, xs, zs, solid, thickness)` -> front,
   back, side and reveal quads. The slab comes out closed; **delete the
   `side` faces lying on each snap plane** (x0/x1 for a wall bay) so the
   snap loops open, and list those planes in `kit_snap` and in
   `check_piece(snap_planes=...)`.
4. **Relief.** `extrude_faces` for timbers, plinths, sills, cornices,
   corbels; `inset` (with a small `depth`) for recessed panels and door
   leaves. Work from large forms to small: mass, then relief, then trim.
   Add asymmetry and wear on purpose (sagging beam, chipped plinth corner,
   one crooked shutter, a patched panel) -- moved verts, not extra geometry.
5. **Materials per face at creation time** (record `{face: material}` as you
   create/extrude, do not infer from normals afterwards) and UVs
   (`set_grid_uv` / `set_directional_uv`).
6. **Verify** with `check_piece(ob, snap_planes=[...])` -- every `*_bad`
   must be 0, `components_bad` 0, and `dead_material_slots` empty. Then look
   at it: `get_screenshot_of_area_as_image('VIEW_3D')` in Material Preview,
   front + 3/4, plus the piece snapped next to a copy of itself and next to
   its family neighbours (seams, texture continuity, snap spacing).
   *The MCP screenshot tools often fail with an `Unterminated string`
   transport error. Reliable fallback: in `execute_blender_code`, set the
   view (`region_3d.view_location/view_distance/view_rotation`, shading
   `MATERIAL`), call `area.tag_redraw()`, and **in a separate call** run
   `bpy.ops.screen.screenshot_area(filepath=...)` under a `temp_override`
   for the VIEW_3D area, then `Read` the PNG (taking it in the same call as
   the view change captures the stale frame).* Do not trust `check_piece()`
   alone: it cannot see bad textures or a boxy silhouette.
7. **Export copy + asset.** `make_export_copy(ob, hidden_collection)` ->
   hidden triangulated `<name>_ZEN`. Then `mark_asset(ob, catalog_id)`.
   Generate the preview **one piece per timer tick / by hand**, never in a
   tight loop (see `documentation/ASSET_LIBRARY_HANDOFF.md`: batching
   previews crashes Blender).
8. **Save the `.blend` immediately** (`bpy.ops.wm.save_as_mainfile`) after
   each finished piece; the MCP connection has dropped the whole session
   before. Confirm afterwards with `bpy.data.filepath` and file size --
   a tiny file means you saved the wrong scene state.

## The kit is for humans, not for Claude

The finished kit is used **by a Blender user by hand, with no Claude, no
Python and no add-on**. `kit_lib.py` and these scripts are authoring tools
only; nothing in a delivered `.blend` may depend on them or on this repo's
absolute paths. Every piece must therefore ship as:

- **Self-contained**: texture images **packed** into the kit `.blend`
  (`image.pack()`), never referenced by a path on this machine. Materials
  are the plain library recipe, so a user can swap them.
- **A real Blender asset**: `mark_single`, a catalog under `Kit/<Family>`
  (catalogs live in `blender_work_dir/kit/blender_assets.cats.txt`, written
  *before* assigning `catalog_id`), a human `description` (size in metres,
  snap planes, origin), tags, author, and a **rendered preview**.
- **Placeable by eye**: origin at floor level on the snap corner, bounding
  box on whole metres, unrotated and unscaled (apply transforms), Y-forward
  wall faces, so drag-and-drop with Increment snap just works.
- **Editable by hand**: clean quad topology and sensible names so a human
  can add a loop cut or swap a material without breaking the piece. No
  modifiers left on the master, no custom properties the user must
  understand to use it.
- **Documented for the user** in `documentation/KIT_USER_GUIDE.md`: keep the
  "What's in the kit" table current and update the guide whenever a
  convention (grid, origin, snap, catalog list) changes. Write user-facing
  text for someone who has never seen this repo.

After saving a kit file, check it from a user's point of view:
from a *different* open file (Blender refuses to load from the current one),
`bpy.data.libraries.load(path, assets_only=True)` lists the pieces; in the
kit file itself, all images report `packed_file`.

## Naming, collections, metadata

- Object + mesh: `NW_KIT_<FAMILY>_<PIECE>_<VAR>` all caps, e.g.
  `NW_KIT_WALL_DOOR_A`, `NW_KIT_ROOF_HIP_B`, `NW_KIT_ROAD_CORNER_A`,
  `NW_KIT_FENCE_GATE_RUIN`. Use `OW_KIT_...` for Old World palettes.
- Collections: `KIT_<FAMILY>` for masters (visible), `KIT_EXPORT_ZEN` for the
  hidden triangulated copies.
- Custom props on the master: `kit_origin`, `kit_snap`, `kit_bbox_cells`,
  `kit_variant_of` (the `_A` it shares a footprint with), `kit_style`.
- Asset catalog branch: `Kit/<Family>` (own branch; do not mix with the
  `Mobs/*` prop catalogs in `blender_assets.cats.txt`).
- Lay the kit out on a labelled shelf grid (10 m spacing, families in rows)
  in the library `.blend` -- one library file per family group under
  `blender_work_dir/kit/`.

## Recipes for common quad-only problems

- **Gable end without a triangle.** The end wall is a pentagon; put one
  vertical loop from the floor line to the apex. That yields two trapezoid
  quads per storey (both with a sloped top edge). Zero tris.
- **Hip / pyramid roof without a pole.** Don't converge four planes on one
  vertex: end the ridge as a short flat ridge line (two vertices), so each
  hip face is a quad.
- **Round things (pillar, barrel, well shaft, tower).** Use an octagonal or
  12-sided ring, and cap it with a 3x3 quad grid pushed to the ring
  (a "squircle" cap), not a fan. Prefer octagons -- they read as Gothic
  low-poly and snap to the grid.
- **Arches.** Build the door/arch opening in the slab grid, then move the
  top vertices of the opening onto a circle/segment arc; the reveal quads
  follow. Add the voussoir pattern as raised quads, not a texture.
- **Roof courses / tiles.** Loop-cut the roof plane into course rows and
  offset alternate rows in Z by 1-2 cm (real relief), texture runs along
  the slope with `set_directional_uv`.
- **Density change** (detailed centre, plain ends). Don't T-junction: run
  the line through the whole piece or stop it with a proper quad ring
  around the detail. Grid lines cost quads; budget for it.
- **Ruins.** Start from the intact piece, then delete whole quads / drag
  boundary verts to make broken edges, keeping the mesh closed by turning
  the new broken edge into real quads. Ruin variants keep the snap loops.

## Quality bar (what "good" means here)

A piece passes review only if it has: a readable silhouette from 20 m
(overhang, gable/eave, chimney, posts), at least three depth layers on
faces that fill the screen (e.g. plinth / wall / timber, or step / riser /
nosing), deliberate asymmetry or wear, a consistent style set, edges that
don't look razor-sharp (chamfer the visible corners with a real strip), and
a clean snap to its family neighbours. If it looks like a textured cube,
add relief before adding polygons elsewhere.

`check_piece()`'s `stretched_uv_bad` catches a texture that prints
stretched: a face whose two edges scale differently between world and UV
space (a SHEARED quad -- usually a UV function that branched per-vertex
instead of per-face, so some corners of one quad got two different
formulas), or whose world-area/uv-area is a big outlier against the rest of
its own material in the piece. Zero, always -- if it's nonzero, read
`stretched_uv_info` (face index, material, "anisotropic"/"area_outlier",
ratio) before assuming a bigger merge distance or "it's probably fine" will
cover it; a real one looks visibly stretched at normal viewing distance.

## Calling the helpers

```python
import bpy, bmesh
exec(open("/Users/jakubjaworski/Creativity/Blender Projects/Blender User Scripts/KIT/.claude/skills/gothic-kit-piece/scripts/kit_lib.py").read())
ob = new_piece("NW_KIT_WALL_DOOR_A", bpy.data.collections["KIT_WALL"])
xs = lines_from([0, 4], [0.4, 3.6], [1.4, 2.6])
zs = lines_from([0, 3], [0, 2.2], [2.6])
solid = mask_with_openings(xs, zs, [(1.4, 2.6, 0, 2.2)])
bm = bmesh.new(); r = slab_from_mask(bm, xs, zs, solid)
timber = [f for f in r["front"] if f.calc_center_median().x < 0.4 or f.calc_center_median().x > 3.6]
caps, sides = extrude_faces(bm, timber, 0.08, with_sides=True)   # + = outward
uvl = bm.loops.layers.uv.new("Float2")   # name the UV map Float2, not "UVMap"
# ...assign material_index / UVs (set_window_uv / set_grid_uv) while the
# bmesh is open, then:
write_piece(ob, bm)
print(check_piece(ob, snap_planes=[(0, 0.0), (0, 4.0)]))
```

Each `execute_blender_code` call starts with a fresh namespace: re-`import
bpy, bmesh` and re-`exec` the lib in every call. Faces returned by one
`slab_from_mask` / `extrude_faces` become invalid after you delete or
re-extrude them; re-select by position instead of keeping stale references.

## What this skill does not know

Not verified: ZenGin/`.ZEN` exporter requirements for kit pieces (collision
proxies, portals, LOD, lightmap UVs, vob-vs-level-mesh placement). The
`_ZEN` copy is only "triangulated and flat shaded like the reference".
Ask the user before claiming anything engine-side. Snap plane sizes, `BAY`
and `STOREY` are proposals derived from the village's measured scale; the
user may change them -- confirm before generating a large batch of pieces.
