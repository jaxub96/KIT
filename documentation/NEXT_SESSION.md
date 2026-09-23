# Next session: start here

Read this first, then `ROADMAP.md` for the prioritized backlog and
`.claude/skills/gothic-kit-piece/SKILL.md` for the mesh-topology lessons.
Last updated 2026-09-23.

## Where things stand

- This is its own repo now, split out of `Blend-Zen` on 2026-09-23 (was
  branch `feature/gothic-kit-house` there). Lives at the sibling path
  `Blender User Scripts/KIT/`, `main` branch, pushed to its own GitHub repo.
  Two things stayed behind in `Blend-Zen` on purpose and are referenced by
  absolute/relative sibling path, not copied here: the shared level-texture
  library (`../Blend-Zen/asset_catalog/materials_levels.blend`, used by
  `kit_lib.py`'s `ensure_material()`) and the reference village/island files
  (`../Blend-Zen/blender_work_dir/NW_VILLAGE_01.blend`, `G2ISLAND_WEB.blend`)
  used only for scale/palette study, never as a live dependency of the
  shipped kit (its 75 pieces have their materials packed inside
  `KIT_WALLS.blend` already).
- The kit library is `blender_work_dir/kit/KIT_WALLS.blend` (renamed from
  `KIT_WALLS.blend`) — 75 pieces, laid out in a non-overlapping grid by
  family, previews regenerated and correct. `build_showcase_level.py` /
  `build_sample_level.py` / `build_two_house_level.py` /
  `build_organic_village.py` are still here as source but their OUTPUT
  `.blend` files were deleted (workspace cleanup) — rerun a script if you
  need one of those scenes back.
- **Grid-snap origins (2026-09-23)**: every wall-line piece's origin is on
  the INSIDE wall face (bay: inside face, left end; corner: inner corner;
  roof run/dormer/fascia: same point as the bay below; roof end: where it
  meets the first run; chimney: wall-top height). A room is 4n x 4 m and a
  whole house snaps on the 1 m grid -- see `KIT_USER_GUIDE.md` section 7.
  Builders still work in the old frame; `kit_lib.rebase_origin()` is their
  last step and `kit_lib.legacy_placement()` converts the level scripts.
  Ground floors are `FLOOR_GROUND_A`/`FLOOR_GROUND_END_A` (origin on the
  ground, planks at 0.46). The jetty pieces were removed.
- **Basic ground set refined (2026-09-23)**, the user's current focus
  (`KIT_WALL_*_A` + `CORNER_A`/`CORNER_SOLO_A`; other families are to be
  re-made later as retextured copies of it, so they're deliberately stale
  and no longer weld to it): the sole rail now sits right on the stone
  footing (0.46-0.61, no groove row; stone and timber meet in a bevelled
  crease), the chamfer no longer runs along the open bay ends, so the
  corner continues the footing flush, and the corner's stone is jittered.
  Rebuild with `scripts/basic_set.py`, which now also holds the upper
  bays + `CORNER_UPPER_A` (rebuilt too: the storey seam is an open, identical loop in every bay
  thanks to `wall_bay.SEAM_COLS` -- welds with 0 non-manifold; see SKILL.md).
  Lean since the same day: plain bay 102 faces, door 176 (SEAM_COLS only on
  the FRONT seam chain; the interior back chain keeps the bay's own columns
  and meets other bays in in-line T-junctions -- the user's method, adopted
  into the generator 2026-09-23 along with their centre-column layout for
  the gable's attic back face). Floor-base skirt still gives 3-face edges when merged
  (by design, see guide). `KIT_WALLS.blend` has three stale test copies of the
  user's (`KIT_WALL_DOOR_A.001`, `UPPER_PLAIN_A.001`, `UPPER_WINDOW_A.001`
  at y=-90) -- theirs, left alone.
- **`KIT_ROOF_T_A` (2026-09-23)**: T roof junction (`scripts/roof_t.py`),
  12 m main roof + 4 m wing off its middle bay, mitred valleys; every end is
  a normal run end. (The trial T-house scene was removed in the 2026-09-24 cleanup; only the asset libs are kept.)
  Still missing for T/L houses: an inside-corner WALL piece (the two
  inside corners overlap 0.4 x 0.4 m). `KIT_ROOF_L_A` (same script, one
  mitre: hip + valley) covers L corners in any direction by rotation.
- **`ROOF_END_GABLE_A` rebuilt (2026-09-23, user-approved from renders)**
  with `scripts/gable_end.py`: slab-only overhang, timber frame + wrapped
  corner posts, clean cap. The old "don't re-fix the cap" note is void.
  The run gained a soffit station (T, L rebuilt from it); RH1/RH2/THATCH
  runs and gables are NOT rebuilt and no longer weld to the basic ones.
  Every marked asset has preferred import method Append. The gable now
  welds to the walls under it (open wall tops + `wall_top_loop`), 0
  non-manifold for 1- and 2-storey houses with roof.
- ZenGin export path: one baked level mesh, or individually placed VOBs?

- **Maya family (2026-09-24, user-approved style)**: `KIT_MAYA.blend` +
  `scripts/maya_bay.py` (built by a scratch script; rebuild = exec kit_lib,
  weld_pieces, maya_bay and call the builders over `MAYA_BAYS` /
  `MAYA_PARAPETS` / `MAYA_CORNERS`, floors, deck, step, then `rebase_origin`).
  22 pieces, flat-roof stone/plaster style of HOUSE.001: plinth, ashlar string
  course split across the storey seam, keystone windows, 7-voussoir arched
  door, blind relief niche, cracks as in-cell notches, parapet (plain / spout /
  frieze), beamed floors and roof slab. Weld tests 0 non-manifold. Known,
  accepted: a few valence-6 verts on the 2 cm chamfer strips (door-jamb /
  plinth crease, seam strip). Next: inner corner (L/U plans), 2 m filler bay,
  plaster/plinth retextured variants, then 3-5 example houses.

## Known traps (read before touching shared code)

- `section_placements` (`build_showcase_level.py`) is the base every
  house/row-house/L-shape composition calls into. Its `rot` parameter's
  real-world effect was determined EMPIRICALLY (place a test instance,
  read back its world position) — don't re-derive by hand.
  `build_organic_village.py` has its OWN copy of this function.
- A corner's `nudge_top`/`nudge_bottom` depends on what's above it
  (lesson 18) — use `WALL_CORNER_SOLO_A` for single-storey buildings.
- A jettied storey's wall-to-corner offset is 0.25 m, not 0.4 m (lesson 17).
- `NW_ROW_HOUSES`/`NW_LSHAPE` have real, DELIBERATE overlapping geometry
  at party walls/inside corners (lesson 20) — don't chase that to 0.
- `bmesh.ops.grid_fill` silently returns 0 faces on a regular N-gon with
  no dominant corners — use `village_pieces.py`'s `_cap()` instead
  (lesson 21).
- `_stitch(bm, F, B, key)` degenerates into a real pole (a triangle fan)
  if one chain has a wide gap with no intermediate points while the other
  doesn't — and `check_piece`'s `poles_bad` field does NOT reliably catch
  it. For anything touching `_stitch`, verify with a direct
  `max(len(v.link_faces) for v in bm.verts)` sweep, not just `check_piece`
  (lesson 22).
- Retexturing a copy (`ob.data = base.data.copy()`): reassign materials by
  INDEX, never `materials.clear()` + `.append()` — clearing to zero slots
  clamps every face's `material_index` to 0 first (lesson 22 postscript).
- Regenerating asset previews: use `bpy.ops.wm.previews_batch_generate()`
  (scoped to the one file), not a manual per-object Python loop — the
  manual version needs the target to be ACTIVE and SELECTED, not just
  `temp_override(id=ob)`, or it silently renders whatever was last active
  (lesson 24).
- See `SKILL.md`'s numbered lessons (24 of them) before adding a new
  weld-adjacent piece.
