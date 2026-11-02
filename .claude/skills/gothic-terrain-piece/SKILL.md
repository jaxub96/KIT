---
name: gothic-terrain-piece
description: Build a Gothic (ZenGin/Gothic 1-2 modding) style low-poly terrain or level chunk in Blender via the blender MCP tools, matching the visual/technical conventions of this project's reference asset G2ISLAND_WEB. Use when the user asks to create an island, cliff, ruin, cave, terrain patch, house, road, or similar level-art piece "in the Gothic style" or "like the existing mesh" -- whether scripted via MCP or modeled by hand.
---

# Gothic terrain piece

Builds level-art terrain (islands, cliffs, ruins, caves, roads, small
buildings) that matches the look of this project's reference asset,
analyzed directly from the Blender scene: `G2ISLAND_WEB` (a rocky island
with cliff faces, cave arches, a grass-covered top, a small ruined tower,
and harbor-style stairs) -- and the mesh-topology discipline worked out
while building a follow-up piece (a hill + house + road + beach + water)
by hand-authoring it with MCP.

Two companion files, same rules, different audience:

- **`WORKFLOW.md`** -- the step-by-step guide for building one of these by
  hand in Blender's UI. Read this if you (or the user) are modeling
  directly rather than scripting.
- **`scripts/gothic_material_lib.py`** -- runnable helpers for building the
  same thing via `execute_blender_code`: grid terrain generation, building
  carving, material creation, and the two UV-projection strategies. Read
  this before writing any generation code; paste/adapt its functions
  rather than reinventing the node graph or UV math.

## Mesh-build philosophy (non-negotiable, applies to both workflows)

1. **Quads first, triangulate last.** Build and edit in quads the entire
   time; `Ctrl+T` / `finalize_for_zengin()` is the final step before
   export or inspection, never a mid-build convenience. A triangle
   mid-build is a dead end -- you've lost the edge a later loop cut/inset
   would have used.
2. **No poles.** Don't fan geometry from a single center vertex (circle-
   from-a-point, cylinder caps). Build a landform as a rectangular vertex
   grid with a height field, not concentric rings. A pole is exactly where
   "primarily quads" breaks down for no real reason, and it's the first
   thing that gets in the way when you later need to cut a footprint or
   road through that area.
3. **One connected mesh, always.** A building on the terrain is not a
   separate object `Join`ed on top -- its wall-base ring reuses the actual
   terrain vertices at its footprint, so there's zero seam. Water is the
   same grid, continued past the shoreline and blended down to water
   level, not a floating plane. Verify with `Select Linked` (`Ctrl+L`)
   from any vertex: it must select the whole mesh. Materials/UVs are still
   free to differ face-to-face across a shared edge -- that's normal
   per-loop data, it doesn't require duplicating vertices.
4. **Tris are allowed only on genuinely flat surfaces with no clean quad
   alternative** -- the textbook case is a gable roof's triangular end
   wall. Never triangulate as a shortcut past a topology problem; fix the
   topology instead (see `WORKFLOW.md`'s checklist).
5. **UV strategy depends on whether the texture is directional.** Rock,
   grass, sand, generic walls/roofs have no visible heading -- project
   along whichever world axis each face's normal points down most
   (triplanar). Paths, stairs, and anything with visible grain or flow
   *do* have a heading -- project every face in that zone against one
   shared direction vector (the path's actual tangent), never per-face
   auto-projection (`bpy.ops.uv.cube_project` or eyeballed `Project from
   View` per face), which rotates the texture wherever a face's dominant
   normal axis happens to flip. See `set_directional_uv` /
   `set_triplanar_uv` in the script, or the manual "project from a locked
   view direction" technique in `WORKFLOW.md` step 7.

## What the reference asset tells us (verified via blender MCP inspection)

- **Fully triangulated at export** (18,837 all-3-sided polygons on
  `G2ISLAND_WEB`) -- but that mesh is the *shipped* state, not evidence of
  how it was authored. Treat rule 1 above as the authoring discipline
  regardless.
- **Flat shaded**: every polygon has `use_smooth = False`, no custom split
  normals. Deliberate low-poly hard-surface look, not a smoothed organic
  sculpt.
- **One UV map**, conventionally named `Float2`.
- **Materials are dead simple and reused by name** across the whole level
  set: `Image Texture (sRGB TGA, 512x512)` -> `Base Color` of a stock
  **Principled BSDF** (Metallic 0, Roughness 0.5, everything else
  default). No normal maps, no roughness maps, no mixing nodes. Always
  check `bpy.data.materials.get(name)` before creating a new one --
  `get_or_create_gothic_material()` does this for you.
- **Texture source**: `GothicBlenderAssets-master/TEXTURES/LEVELS/NewWorld/`
  (Gothic II "New World" set, 644 files) and `.../OldWorld/` (Gothic I
  set, 177 files) live alongside this project. Every material name matches
  its source filename (minus extension), e.g. `NW_Nature_Stein_01.tga` ->
  material `NW_NATURE_STEIN_01`.
- **Scale convention**: 1 Blender unit ~= 1 Gothic engine unit. Don't
  rescale imported textures/geometry.

## Texture zones (pick by theme)

| Zone | NewWorld prefixes | UV mode |
|---|---|---|
| cliff / rock face | `NW_Nature_Stein*`, `NW_Seq_CanyonWall*` | triplanar |
| grass / soil top | `NW_Nature_Waldboden*`, `NW_Seq_Ground*`, `NW_Nature_Acker*` | triplanar |
| worked stone ground | `NW_City_StoneGround*`, `NW_Misc_Maya_Ground*` | triplanar |
| paths | `NW_Nature_Path*`, `NW_Seq_GravelPath*`, `NW_Nature_Kies*` | **directional** |
| sand/shore | `NW_Seq_Nature_WhiteSand*` | triplanar |
| water | `NW_Nature_Water_01` (also see `NW_Water_Lake01_*` animated frames under `Animated/`) | triplanar |
| ruined walls | `NW_Monastery_Wall*`, `NW_Dungeon_Wall*`, `NW_Misc_Maya_Wall*` | triplanar |
| small-house / timber walls | `NW_Monastery_WoodWall*` | triplanar |
| roofs | `NW_Misc_Roof*`, `NW_Monastery_Roof*` | triplanar |
| stairs | `NW_Harbour_Stairs*`, `NW_Nature_Stairs*`, `NW_Monastery_Steps*` | **directional** |
| interior floors | `NW_City_BodenDielen*`, `NW_City_InsideFloor*` | triplanar |
| orc/temple ruins | `NW_DragonIsland_Temple*`, `NW_DragonIsland_OrcWall*`, `NW_DragonIsland_Rock*` | triplanar |

For a Gothic-1-flavored theme (volcanic, swamp, old camp, orc), use
`OldWorld/` textures instead (`OW_Volcano*`, `OW_Forest*`, `OW_OldCamp*`,
`OW_Orcs*`).

If unsure what's available, search the folder, e.g. via Bash/Glob on
`GothicBlenderAssets-master/TEXTURES/LEVELS/NewWorld/*<keyword>*`.

## Workflow (scripted, via MCP)

1. **Parse the user's prompt** into a landform, footprint size, and 2-4
   thematic zones, each mapped to a texture prefix above and a UV mode.
2. **Build one height-field grid** with `build_terrain_grid()` covering
   the landform *and* a water margin -- water is the outer rim of this
   same grid (blend the height field down to a constant water level past
   the shoreline radius/boundary), not a second object.
3. **Reserve footprint cells** for any building with `footprint_cells()` +
   `grid_quads(..., skip_cells=...)`, then weld it in with
   `carve_building()`. Call `remove_loose_verts()` on that footprint's
   interior verts afterward -- they lose every face that referenced them
   and become disconnected if you don't.
4. **Classify each face's zone** at creation time (from its grid cell's
   center position), not by reverse-engineering normals/height after the
   fact -- record `{face: zone}` as you go, it's far more reliable.
5. **UV + material per zone**: `set_triplanar_uv()` for isotropic zones,
   `set_directional_uv()` for path/stair zones (compute `dir_u`/`dir_v`
   once from the zone's actual direction of travel, reuse for every face
   in it). Assign materials via `get_or_create_gothic_material()`.
6. **Finalize** with `finalize_for_zengin()` -- applies/removes modifiers,
   triangulates (last step, `BEAUTY` method), forces flat shading, strips
   custom normals.
7. **Verify**: `get_object_info` (face-side distribution should be ~all 4s
   plus your intentional tris, pre-triangulation; single connected
   component via a flood-fill over `link_edges`), and
   `get_viewport_screenshot` in Material Preview shading from a top-down
   angle (fastest way to see zone layout/misalignment) and a 3/4
   perspective (fastest way to see silhouette/proportions).
8. **Name the object** in the reference's ALL-CAPS underscore convention
   (`G2ISLAND_WEB`), prefixed `NW_`/`OW_` to match whichever texture set
   was used, e.g. `NW_HILLHOUSE_01`.
9. **Save.** The Blender scene in this project is not backed by a `.blend`
   file by default (the reference mesh was loaded from a `.ZEN` and lived
   only in memory -- it was lost once already when the addon reloaded).
   `bpy.ops.wm.save_as_mainfile(filepath=...)` after finishing a piece.

## Workflow (manual, in Blender's UI)

See `WORKFLOW.md` for the full step-by-step guide, including the
topology checklist to run before triangulating and a table of "instead of
X, do Y" fixes for the most common sources of rework.

## What this skill does NOT know

No ZenGin/.ZEN exporter or collision/LOD requirements were inspected as
part of this analysis -- only the Blender-side mesh and material state.
Don't invent exporter-specific claims (portal geometry, LOD chains, vertex
colors, lightmap UVs) beyond what's written above; ask the user if the
task requires exporting rather than assuming engine-side conventions.
