# Reference helper functions for building Gothic (ZenGin) style terrain pieces
# in Blender via the blender MCP `execute_blender_code` tool.
#
# This is NOT a Blender add-on. It is a snippet library: read the function you
# need, paste/adapt it into an execute_blender_code call (or exec() this file
# directly from disk, as the workflow below does). Keeping it as plain text
# avoids depending on an installed add-on that may not be enabled.
#
# --- MESH-BUILD PHILOSOPHY (read this before generating anything) ---------
# 1. Build with QUADS. The whole piece -- terrain, water, buildings, roads --
#    is ONE bmesh, ONE connected vertex grid. Triangulate only as the very
#    last step (`finalize_for_zengin`), right before export/inspection. Tris
#    mid-development are only acceptable on genuinely flat surfaces that have
#    no other clean quad topology (e.g. a gable roof's triangular end wall).
# 2. No poles. Don't fan geometry out from a single center vertex (that's
#    where "primarily quads" breaks down for no reason) -- build islands as
#    a rectangular vertex grid with a height field, not concentric rings
#    around a point.
# 3. Everything is welded. A building sitting on the terrain is not a
#    separate object joined on top -- its wall-base ring reuses the actual
#    terrain vertices at its footprint, so the mesh has zero seams there.
#    Same for water: it is the same grid, continued past the shoreline and
#    blended down to water level, not a floating plane. Materials can (and
#    should) differ face-to-face across a shared edge -- that's normal
#    per-loop UV/material data, it does not require duplicating vertices.
# 4. Triplanar UV by default, EXCEPT for directional textures (paths, stair
#    treads, plank runs, anything with visible grain/flow) which need an
#    explicit tangent direction -- see `set_directional_uv`. Never rely on
#    bpy.ops.uv.cube_project for those: it is an implicit rotate-per-face
#    operator, so texture heading is not decided by the resulting UV
#    field, and any face whose dominant normal axis flips relative to its
#    neighbor twists that face's texture 90 degrees.

import bpy
import bmesh
import math
import os

# EDIT THIS for your machine -- same convention as
# asset_catalog/generate_material_catalog.py's TEXTURE_ROOT in this repo.
TEXLIB_ROOT = r"C:\Users\jkjw\Documents\gothic mod\GothicBlenderAssets-master\TEXTURES\LEVELS"
NEWWORLD_DIR = os.path.join(TEXLIB_ROOT, "NewWorld")
OLDWORLD_DIR = os.path.join(TEXLIB_ROOT, "OldWorld")


# --- materials -------------------------------------------------------------

def get_or_create_gothic_material(mat_name, texture_path, roughness=0.5):
    """Reproduce the reference asset's material recipe exactly:
    Principled BSDF (defaults) <- Image Texture (sRGB) -> Base Color only.
    No normal/roughness maps, no extra nodes. Reuses an existing material
    if one with this name is already in the file (the source mesh never
    duplicates a material name).
    """
    mat = bpy.data.materials.get(mat_name)
    if mat:
        return mat

    mat = bpy.data.materials.new(mat_name)
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = 0.0

    tex = nt.nodes.new("ShaderNodeTexImage")
    img = bpy.data.images.get(os.path.basename(texture_path))
    if img is None:
        img = bpy.data.images.load(texture_path)
    img.colorspace_settings.name = "sRGB"
    tex.image = img

    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    out.location = (300, 0)
    bsdf.location = (0, 0)
    tex.location = (-300, 0)

    return mat


# --- quad-grid terrain (no poles, fully welded) -----------------------------

def build_terrain_grid(bm, half_size, segments, height_fn):
    """Build a fully-connected NxN quad grid, no poles. `height_fn(x, y)`
    returns the z for each vertex -- this is the ONLY place geometry is
    procedural; everything downstream (faces, UVs, materials) just reads
    positions back out. Returns (V, dx): V is a [segments+1][segments+1]
    array of BMVert, dx is the cell size in world units.
    """
    n = segments
    dx = (2 * half_size) / n
    V = [[None] * (n + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        x = -half_size + i * dx
        for j in range(n + 1):
            y = -half_size + j * dx
            V[i][j] = bm.verts.new((x, y, height_fn(x, y)))
    return V, dx


def grid_quads(bm, V, skip_cells=None):
    """Quad-fill the whole grid except cells in `skip_cells` (a set of
    (i, j) lower-left cell indices -- e.g. a building footprint about to be
    carved out). Returns a list of (face, i, j) so callers can classify /
    tag each face by its grid cell as it's created (much more reliable than
    re-deriving a zone from geometry after the fact).
    """
    n = len(V) - 1
    skip_cells = skip_cells or set()
    out = []
    for i in range(n):
        for j in range(n):
            if (i, j) in skip_cells:
                continue
            f = bm.faces.new((V[i][j], V[i + 1][j], V[i + 1][j + 1], V[i][j + 1]))
            out.append((f, i, j))
    return out


def footprint_cells(i0, i1, j0, j1):
    """All (i, j) grid cells covered by a footprint rectangle -- pass this
    straight into `grid_quads(..., skip_cells=...)` before carving a
    building with `carve_building`.
    """
    return {(i, j) for i in range(i0, i1) for j in range(j0, j1)}


def carve_building(bm, V, i0, i1, j0, j1, wall_height, roof_ridge_height):
    """Weld a small gable-roofed building onto a footprint already removed
    from the terrain grid (via `footprint_cells` + `grid_quads`).

    The wall base is NOT new geometry -- it's the existing boundary loop of
    terrain vertices at (i0..i1, j0..j1), so the building is topologically
    part of the same mesh as the ground around it. Only the wall-top ring
    and the roof ridge are new vertices. Ridge runs along the i (x) axis;
    pick i1-i0 > j1-j0 so the roof reads as a proper gable, not a hip.

    Faces created:
      - walls: quads, one per boundary edge segment
      - roof: quads for the two sloped planes
      - gable ends: 2 triangles (flat vertical surfaces -- the one place
        this workflow allows a non-quad by design, not by accident)

    Returns {"wall": [...], "roof": [...], "gable": [...]} face lists.
    """
    base_z = V[i0][j0].co.z
    wall_top_z = base_z + wall_height
    ridge_z = wall_top_z + roof_ridge_height

    top = {}
    for i in range(i0, i1 + 1):
        for j in (j0, j1):
            v = V[i][j]
            top[(i, j)] = bm.verts.new((v.co.x, v.co.y, wall_top_z))
    for j in range(j0 + 1, j1):
        for i in (i0, i1):
            v = V[i][j]
            top[(i, j)] = bm.verts.new((v.co.x, v.co.y, wall_top_z))

    def perimeter_keys():
        keys = []
        for i in range(i0, i1):
            keys.append((i, j0))
        for j in range(j0, j1):
            keys.append((i1, j))
        for i in range(i1, i0, -1):
            keys.append((i, j1))
        for j in range(j1, j0, -1):
            keys.append((i0, j))
        return keys

    faces = {"wall": [], "roof": [], "gable": []}

    keys = perimeter_keys()
    n = len(keys)
    for k in range(n):
        a, b = keys[k], keys[(k + 1) % n]
        base_a, base_b = V[a[0]][a[1]], V[b[0]][b[1]]
        faces["wall"].append(bm.faces.new((base_a, base_b, top[b], top[a])))

    ridge = {i: bm.verts.new((V[i][j0].co.x, (V[i0][j0].co.y + V[i0][j1].co.y) / 2, ridge_z))
             for i in range(i0, i1 + 1)}

    for i in range(i0, i1):
        faces["roof"].append(bm.faces.new((top[(i, j0)], top[(i + 1, j0)], ridge[i + 1], ridge[i])))
        faces["roof"].append(bm.faces.new((ridge[i], ridge[i + 1], top[(i + 1, j1)], top[(i, j1)])))

    faces["gable"].append(bm.faces.new((top[(i0, j0)], top[(i0, j1)], ridge[i0])))
    faces["gable"].append(bm.faces.new((top[(i1, j1)], top[(i1, j0)], ridge[i1])))

    # Interior grid vertices strictly inside the footprint (not on its
    # boundary loop) are no longer referenced by any face once their cells
    # were skipped in grid_quads -- purge them or they end up as
    # disconnected loose verts, breaking the "one connected mesh" contract.
    remove_loose_verts(bm, [V[i][j] for i in range(i0 + 1, i1) for j in range(j0 + 1, j1)])

    return faces


def remove_loose_verts(bm, verts):
    """Delete verts from `verts` that ended up with zero linked faces (e.g.
    grid vertices orphaned by carve_building). Safe to call with verts that
    still have faces -- those are left untouched.
    """
    dead = [v for v in verts if v.is_valid and len(v.link_faces) == 0]
    bmesh.ops.delete(bm, geom=dead, context='VERTS')


# --- UV projection -----------------------------------------------------------
# Two modes. Pick per zone, not per material -- the same material can be
# used with either mapping depending on what surface it's on.

def set_triplanar_uv(face, uv_layer, tile):
    """Default for isotropic textures (rock, grass, sand, roof, generic
    wall): project along whichever world axis the face's normal points
    down most, using the other two coordinates as U/V. For a mostly-flat
    zone (ground, water) this naturally settles on the same axis for every
    face in the zone, so it reads as one continuous, unrotated texture --
    no per-face seams. `tile` is world units per texture repeat.
    """
    n = face.normal
    ax, ay, az = abs(n.x), abs(n.y), abs(n.z)
    for loop in face.loops:
        co = loop.vert.co
        if az >= ax and az >= ay:
            uv = (co.x / tile, co.y / tile)
        elif ay >= ax:
            uv = (co.x / tile, co.z / tile)
        else:
            uv = (co.y / tile, co.z / tile)
        loop[uv_layer].uv = uv


def set_directional_uv(face, uv_layer, origin, dir_u, dir_v, tile_u, tile_v):
    """Use for anything with a visible direction -- paths, stairs, plank
    runs, rivers. `dir_u` is the texture's "forward" (along the direction
    of travel / grain), `dir_v` its "across" -- both unit Vectors, computed
    once from the actual path tangent and shared by every face in the zone,
    so heading and scale stay consistent regardless of each face's own
    normal. `origin` anchors u=v=0. tile_u/tile_v are world units per
    texture repeat along each axis (they usually differ: a path tiles at a
    different rate along its length than across its width).

    This replaces bpy.ops.uv.cube_project for directional zones: that
    operator picks a projection axis per face from the face's own normal,
    so on a winding or sloped strip neighboring faces can each choose a
    different axis and the texture heading jumps between them. Projecting
    every loop against one shared (dir_u, dir_v) frame instead guarantees a
    single, consistent heading down the whole strip.

    For a strip that curves, don't call this with one global (dir_u,
    dir_v) -- instead compute a local tangent per face (e.g. from a spline)
    and call this once per face with that face's own dir_u/dir_v.
    """
    for loop in face.loops:
        rel = loop.vert.co - origin
        loop[uv_layer].uv = (rel.dot(dir_u) / tile_u, rel.dot(dir_v) / tile_v)


# --- finalize ----------------------------------------------------------------

def finalize_for_zengin(obj):
    """Bring a mesh in line with the mesh-hygiene conventions observed on
    the reference asset (G2ISLAND_WEB): fully triangulated, flat shaded,
    no modifiers left in the stack, no custom split normals. Call this LAST,
    after all quad-based sculpting/UV/material work is done -- triangulating
    earlier throws away the quad structure this workflow depends on for
    clean topology and defeats the point of building in quads at all.
    """
    bpy.context.view_layer.objects.active = obj
    for m in list(obj.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)

    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method='BEAUTY', ngon_method='BEAUTY')
    bmesh.update_edit_mesh(obj.data)
    bpy.ops.object.mode_set(mode='OBJECT')

    for p in obj.data.polygons:
        p.use_smooth = False

    if hasattr(obj.data, "use_auto_smooth"):
        obj.data.use_auto_smooth = False  # pre-4.1 API
    if obj.data.has_custom_normals:
        obj.data.free_custom_split_normal_data()


# --- material zone lookup -----------------------------------------------
# Category prefixes found under NewWorld/ (Gothic II "New World" set) and
# OldWorld/ (Gothic I "Old World" set). Use these to pick sensible textures
# per terrain zone based on the user's theme.
NEWWORLD_ZONES = {
    "cliff_rock": ["NW_Nature_Stein", "NW_Seq_CanyonWall", "NW_Nature_BarkRings"],
    "ground_grass": ["NW_Nature_Waldboden", "NW_Seq_Ground", "NW_Nature_Acker"],
    "ground_stone": ["NW_City_StoneGround", "NW_Misc_Maya_Ground"],
    "path": ["NW_Nature_Path", "NW_Seq_GravelPath", "NW_Nature_Kies"],           # directional
    "sand_shore": ["NW_Seq_Nature_WhiteSand"],
    "water": ["NW_Nature_Water_01"],
    "wall_ruin": ["NW_Monastery_Wall", "NW_Dungeon_Wall", "NW_Misc_Maya_Wall"],
    "wall_wood": ["NW_Monastery_WoodWall"],
    "roof": ["NW_Misc_Roof", "NW_Monastery_Roof"],
    "stairs": ["NW_Harbour_Stairs", "NW_Nature_Stairs", "NW_Monastery_Steps"],   # directional
    "floor_interior": ["NW_City_BodenDielen", "NW_City_InsideFloor"],
    "temple_orc": ["NW_DragonIsland_Temple", "NW_DragonIsland_OrcWall", "NW_DragonIsland_Rock"],
}

OLDWORLD_ZONES = {
    "volcano": ["OW_Volcano"],
    "swamp": ["OW_Forest", "OW_Nature"],
    "old_camp": ["OW_OldCamp"],
    "orc": ["OW_Orcs"],
}

# Zones that need set_directional_uv instead of set_triplanar_uv -- anything
# with visible grain/flow along a direction of travel.
DIRECTIONAL_ZONES = {"path", "stairs"}
