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
  `NW_KIT_WALLS.blend`) — 75 pieces, laid out in a non-overlapping grid by
  family, previews regenerated and correct. `build_showcase_level.py` /
  `build_sample_level.py` / `build_two_house_level.py` /
  `build_organic_village.py` are still here as source but their OUTPUT
  `.blend` files were deleted (workspace cleanup) — rerun a script if you
  need one of those scenes back.
- `ROOF_END_GABLE_A`'s outer roof cap self-intersects (a real, known,
  unfixed bug) — the user asked for this REVERTED after seeing a
  topologically-correct redesign, so it's intentionally back to the
  original broken shape. **Don't re-fix it without being asked.**
  `WALL_WINDOW_SHUTTER_A`'s shutter panels were removed for good (kept).

## Open question for the user (don't guess — ask)

- ZenGin export path: one baked level mesh, or individually placed VOBs?

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
