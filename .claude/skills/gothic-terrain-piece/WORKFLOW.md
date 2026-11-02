# Manual modeling workflow: quad-first Gothic level pieces

This is the human-in-Blender counterpart to `scripts/gothic_material_lib.py`.
Same rules, same reasons -- written out as a step order and a checklist so
you get a clean, fully-connected quad mesh in one pass instead of fixing
topology after the fact. Read `SKILL.md` first for the material/texture
conventions; this file is about *build order and topology discipline*.

## Why iteration usually happens (and how this avoids it)

Almost every case of "I have to go back and fix the mesh" traces to one of
four decisions made too early:

1. **A pole.** Fanning geometry from a single center vertex (circle-from-a-
   point, cylinder caps) looks fine until you need to cut a building
   footprint or a road through that area, and there's no clean quad grid to
   cut into. **Fix: never start from a point.** Start from a grid.
2. **A boolean.** Cutting a doorway, footprint, or path with a Boolean
   modifier produces whatever n-gon soup the algorithm feels like that day.
   It's fast once and expensive forever after. **Fix: cut footprints with
   loop cuts on a grid you already planned for, so the cut lands exactly on
   existing edges.**
3. **Building the house/prop separately, then `Join`.** A join is not a
   weld — you get two overlapping vertex shells sitting at the same point in
   space, not one. It looks right and is topologically wrong (loose
   geometry, doubled verts, hidden seams). **Fix: either build the prop's
   base ring directly from the terrain's own boundary loop (see step 4), or
   `Join` + `Bridge Edge Loops` + `Merge by Distance` — never `Join` alone.**
4. **Triangulating early.** Once a quad becomes two triangles you've lost
   the edge that a future loop cut, inset, or bevel would have used. Every
   downstream edit gets harder. **Fix: triangulate is the literal last
   operation, done once, right before export.**

## Build order

### 1. Plan the zones before opening Blender

Sketch the footprint top-down: where's the building, which direction does
the road run, where's the shoreline. You need this before picking a grid
resolution, because the resolution has to make your smallest feature (a
door width, a path width) land on a whole number of cells — re-gridding
after the fact is exactly the rework this guide exists to avoid.

### 2. Start from one grid, sized for everything including water

`Add > Mesh > Grid`, sized to cover the landform *and* a water margin
around it — water is not a separate plane, it's the outer rim of this same
grid, so it has to be in the domain from the start (see step 6). Pick X/Y
subdivisions so cell size divides evenly into your building footprint(s)
(e.g. 1m cells if the house is 3m x 4m). This is the one and only place a
resolution decision gets made — no re-gridding later.

### 3. Sculpt height with Proportional Edit, not sculpt-mode brushes

Vertex select the whole grid, then use Proportional Editing (`O`, Smooth
falloff) to push/pull regions into a plateau, slopes, and a cliff band.
Proportional edit moves existing quads without changing topology — sculpt
mode brushes are fine for organic props but will happily add poles/n-gons
you then have to clean up. Work in top-ortho (Numpad 7) so you can see the
zone plan from step 1 under the mesh (reference image or grid overlay).

Height guidance from the reference asset (`G2ISLAND_WEB`) and this skill's
generator: a flat plateau cap, a smoothstep-falloff slope down to the
shoreline, and a bit of high-frequency noise on the *non-corridor* portion
of that slope reads as "rocky cliff" — keep the corridor toward your
road/beach smoother and lower-amplitude than the rest of the shoreline, or
the road will look like it's cutting through solid rock.

### 4. Cut and extrude the building — don't join a separate object

1. `Ctrl+R` loop cuts to isolate the exact footprint rectangle on the grid
   (this is why step 2's resolution matters).
2. Select the footprint's interior faces and delete them — the boundary
   loop stays, still shared with the surrounding terrain. That loop *is*
   the wall base; nothing new has been created there yet, so there is
   nothing to weld.
3. Select that boundary loop, `E` then `Z` to extrude straight up to wall
   height. This ring of new wall-top vertices is the only genuinely new
   geometry so far — everything else so far reused existing terrain verts.
4. At the top loop, `Ctrl+R` a single loop cut down the ridge line
   (perpendicular to the long axis), then select just that new ridge edge
   and `G Z` it up to the peak height. This automatically produces the two
   sloped roof faces as quads.
5. The two gable ends are the one place this workflow expects a triangle —
   select just those two end faces and `Ctrl+T` *only them*, not the whole
   mesh. A flat vertical triangle is the correct primitive there; forcing a
   quad would mean adding a meaningless extra vertex.

If you modeled the house as a separate object for convenience (e.g. reusing
a prop from elsewhere), position it exactly so its base ring vertex count
and spacing matches the terrain cut, then use `Bridge Edge Loops` between
the two boundary loops, followed by `Mesh > Merge > By Distance` to weld
coincident vertices. Check the loose-geometry step in the checklist below
afterward — this is the #1 source of the "6 orphaned vertices" class of bug
(interior verts of a deleted footprint that never got cleaned up).

### 5. Roads: a material zone, not new geometry (usually)

For a road that follows the existing slope (not raised/sunken), don't model
it — select the strip of *existing* faces along the route (`Select Loop`,
or Lasso in top-ortho) and give that strip its own material slot. Only add
real geometry (a sunken cart-track profile, raised causeway, stairs) if the
brief specifically calls for elevation change; the reference asset uses
flat material-only paths for the common case.

### 6. Water: extend the same grid, don't add a plane

The rim of the grid from step 2, beyond the shoreline, is water — assign
it the water material directly. If you need it flat and at a specific
level regardless of what the seabed does further out, box-select just that
outer ring in top view and set its Z uniformly (`Alt+S` won't do this —
just type an absolute Z with `G Z` then typing the value, or use the N
panel's Z field on a multi-vertex selection... note Blender averages, so
for an exact shared Z use Mesh > Transform > this is one case where
scripting a flat Z is easier than doing it by hand — see
`gothic_material_lib.py`'s `height_at` water branch for the reference
formula (smoothstep down to a constant `water_level`)).

### 7. UV unwrap per zone, matched to how the texture reads

**Isotropic textures** (rock, grass, sand, generic wall/roof — no visible
direction): select the zone's faces (`Select Similar > Material` after
step 8, or select as you go), orient the view to match the zone's dominant
surface normal (top-ortho for mostly-flat zones, front/side-ortho for
mostly-vertical ones — i.e. pick the axis a triplanar projection would have
picked), and `UV > Project from View (Bounds)`. This is the manual
equivalent of `set_triplanar_uv` in the script: same axis for every face in
the zone keeps it seamless.

**Directional textures** (paths, stair treads, plank runs — anything with
visible grain or a heading): do *not* use Cube Projection — it picks a
projection axis per face from that face's own normal, so a strip that
winds even slightly gets a rotation jump at every face where the dominant
axis flips. Instead: orbit the view to look straight down the path's
direction of travel in orthographic (rotate the view so the path reads
"up" in-frame), select the strip, `UV > Project from View (Bounds)`. This
is the manual equivalent of `set_directional_uv` — projecting from one
locked view direction is the same guarantee the script gets from one
shared `(dir_u, dir_v)` frame. For a *curving* path, do this in short
straight segments (project each mostly-straight run from its own matching
view angle) rather than one projection for the whole curve.

After projecting, temporarily assign a UV test grid image
(`Image > UV Test Grid` in the material's image slot, or a checker node) to
each zone and rotate the viewport around it in Material Preview — a
correctly-aligned directional texture shows unbroken parallel lines along
the whole strip; any 90-degree jump is a face that needs re-projecting.

### 8. Assign materials, matching the reference recipe

One `Image Texture (sRGB) -> Base Color -> Principled BSDF (defaults) ->
Output` per material, nothing more (no normal/roughness maps — see
`SKILL.md`). Assign by selecting the zone's faces and hitting `Assign` in
the material slot list.

### 9. Topology checklist — run this BEFORE triangulating

Fixing any of these after triangulating means redoing UV work too, so
catch them here:

- `Select > All by Trait > Non Manifold` — should select nothing (except a
  deliberately open boundary edge where this piece will join an adjacent
  level tile).
- `Select > All by Trait > Faces by Sides`, "Not Equal To", 4 — should
  select only the intentional triangles (gable ends) and nothing else. Any
  other tri or n-gon here is a mistake to fix now, while it's still quads
  and easy to see why.
- `Select > All by Trait > Loose Geometry` — should select nothing. This is
  exactly the bug class from step 4 (orphaned interior verts of a deleted
  footprint) — catch it here, not after export.
- Single connected mesh: `Select Linked` (`Ctrl+L`) from any one vertex
  should select the entire mesh, including the water rim and the house.
  If it doesn't, something got left as a separate island — go find the
  seam and `Bridge Edge Loops` + `Merge by Distance` it.

### 10. Triangulate — last step, no exceptions

`Select All`, `Mesh > Triangulate Faces` (`Ctrl+T`), Beauty method. Do this
on a duplicate or after saving a `.blend` with the quad version intact —
you will want to come back and edit the quad mesh, not the triangulated
export copy, if anything changes later.

## Quick reference: what NOT to do

| Instead of... | Do this |
|---|---|
| Circle/cylinder primitive with a pole | Grid primitive, no pole, ever |
| Boolean cut for a footprint/doorway | Loop cut on a pre-planned grid |
| Build house separately, `Join` | Cut footprint from terrain, extrude in place (or Bridge + Merge by Distance if you must join) |
| Separate floating water plane | Same grid, outer rim, water material |
| `Cube Project` on a path/stairs | `Project from View` locked to the path's own direction |
| Triangulate while still modeling | Triangulate once, last, before export |
