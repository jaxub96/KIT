# Gothic modular building kit

A reusable Gothic (ZenGin, Gothic 1/2 style) modular level-art kit for
Blender: 75 asset-marked wall/roof/floor/street/prop pieces that snap
together on a 1 m grid to build houses, row houses, civic/sacred
buildings, and streets.

Split out of the `Blend-Zen` project on 2026-09-23 into its own repo so it
can stand alone as a Blender Asset Library.

## Start here

- **`documentation/NEXT_SESSION.md`** -- current status, known traps, open
  questions. Read this first.
- **`documentation/ROADMAP.md`** -- full piece list and future work.
- **`documentation/KIT_USER_GUIDE.md`** -- how to use the kit by hand in
  Blender's UI (no scripting needed): adding the asset library, snapping
  pieces together, building a house.
- **`.claude/skills/gothic-kit-piece/SKILL.md`** -- how to build/extend
  kit pieces, including the mesh-topology lessons learned building this
  kit (poles, stitching, weld contracts, preview generation).

## Layout

- `blender_work_dir/kit/KIT_WALLS.blend` -- the kit library (open this as
  a Blender Asset Library, see `KIT_USER_GUIDE.md` section 1).
- `blender_work_dir/build_*.py` -- sample-scene generator scripts (village,
  two-house demo, organic composition). None of them modify the kit
  library; each builds and saves its own separate output file.
- `.claude/skills/gothic-kit-piece/` -- the piece-building skill: design
  rules, helper library (`scripts/kit_lib.py`, `scripts/weld_pieces.py`,
  etc.), and per-family piece scripts.

## External dependencies (intentionally left in the sibling `Blend-Zen` repo)

- **Shared level-texture library**: `../Blend-Zen/asset_catalog/materials_levels.blend`
  -- `kit_lib.py`'s `ensure_material()` pulls from it when a piece needs a
  material not already packed into `KIT_WALLS.blend`. The kit's existing 75
  pieces don't need this at runtime (their materials are packed in), only
  new-piece development does.
- **Reference assets**: `../Blend-Zen/blender_work_dir/NW_VILLAGE_01.blend`
  and `G2ISLAND_WEB.blend` -- used only to study scale/palette/style when
  designing new pieces. Never a runtime dependency of the shipped kit.

Both assume this repo stays checked out as a sibling of `Blend-Zen` on disk
(`.../Blender User Scripts/KIT` next to `.../Blender User Scripts/Blend-Zen`).
