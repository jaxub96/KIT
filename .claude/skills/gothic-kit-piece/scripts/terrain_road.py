# Modular ground/road tiles: 4m x 4m (matches BAY), flat quad grid, so they
# snap to each other AND to the house footprint on the same module grid the
# wall kit uses. Needs kit_lib.py exec'd first.
#
#   exec(open(KIT_LIB).read()); exec(open(TERRAIN_ROAD).read())
#   build_ground_tile(ob, "flat", mats, zen_coll=zenc, seed=51)
#   build_ground_tile(ob, "yard", mats, zen_coll=zenc, seed=52)
#   build_road_tile(ob, "straight", mats, zen_coll=zenc, seed=53)
#   build_road_tile(ob, "junction", mats, zen_coll=zenc, seed=54)
#
# Weld contract: every tile is built on the SAME 4x4, 1m-cell grid, z=0 at
# every edge vertex (x=0, x=4, y=0, y=4) with NO jitter there -- any two
# tiles (ground-to-ground, ground-to-road, road-to-road, any rotation of
# either) share that row exactly, so placing them on the grid and running
# Merge by Distance welds the ground into one mesh, the same as the wall
# kit's end loops. Interior verts get a small jitter so the surface doesn't
# read as a mechanical grid.
import bpy, bmesh, math
from mathutils import Vector

TILE = 4.0
N = 4                                    # 1m cells
ROAD_W = 2.0                             # road band width, centred


def _grid(bm, kind_at):
    """kind_at(cx, cy) -> material kind string for cell (cx,cy) in 0..N-1.
    Returns (faces, V) with V[(i,j)] the BMVert at grid line (i,j), i,j in 0..N."""
    V = {}

    def v(i, j):
        if (i, j) not in V:
            V[(i, j)] = bm.verts.new((i * TILE / N, j * TILE / N, 0.0))
        return V[(i, j)]
    faces = []
    for i in range(N):
        for j in range(N):
            f = bm.faces.new((v(i, j), v(i + 1, j), v(i + 1, j + 1), v(i, j + 1)))
            faces.append((f, kind_at(i, j)))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return faces, V


def _finish(ob, bm, faces, V, mats, kinds_order, seed, zen_coll, uv_fn):
    bm.verts.ensure_lookup_table()
    interior = [v for v in V.values() if 1e-4 < v.co.x < TILE - 1e-4 and 1e-4 < v.co.y < TILE - 1e-4]
    jitter(bm, interior, (0.0, 0.0, 0.035), seed=seed)
    bm.normal_update()
    ob.data.materials.clear()
    slot = {}
    for k in kinds_order:
        ob.data.materials.append(mats[k])
        slot[k] = len(ob.data.materials) - 1
    uvl = bm.loops.layers.uv.get("Float2") or bm.loops.layers.uv.new("Float2")
    for f, k in faces:
        f.material_index = slot[k]
        uv_fn(f, k, uvl)
    write_piece(ob, bm)
    bm.free()
    res = check_piece(ob, snap_planes=[(2, 0.0)], flat_tri_ok=True)
    if zen_coll is not None:
        make_export_copy(ob, zen_coll)
    return res


def build_ground_tile(ob, kind, mats, zen_coll=None, seed=51):
    """kind: "flat" (grass) or "yard" (bare trodden dirt, for a house's own
    footprint / dooryard). Single material, flat quad grid, edges pinned."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    if zen_coll is not None:
        for o in [o for o in bpy.data.objects if o.name == ob.name + "_ZEN"]:
            bpy.data.meshes.remove(o.data)
    bm = bmesh.new()
    faces, V = _grid(bm, lambda i, j: kind)
    tile = 5.0 if kind == "flat" else 3.0

    def uv(f, k, uvl):
        set_grid_uv(f, uvl, tile)
    return _finish(ob, bm, faces, V, mats, (kind,), seed, zen_coll, uv)


def _road_kind(i, j, mode):
    lo, hi = (N - ROAD_W / (TILE / N)) / 2, (N + ROAD_W / (TILE / N)) / 2
    cx, cy = i + 0.5, j + 0.5
    on_ns = lo <= cx <= hi
    on_ew = lo <= cy <= hi
    if mode == "straight":
        return "road" if on_ns else "flat"
    return "road" if (on_ns or on_ew) else "flat"          # junction / crossroads


def build_road_tile(ob, mode, mats, zen_coll=None, seed=53):
    """mode: "straight" (runs north-south, grass shoulders either side) or
    "junction" (crossroads, so several straight segments can meet and reach
    more than one house). Rotate 90 in Z for an east-west straight run.

    The road texture is unidirectional (grain/wear runs one way), so a
    junction can't just keep the straight tile's rectangular N-S/E-W split
    -- that seam is a straight line where the two directions meet edge-on,
    which is wrong for grain that has to turn a corner. Mitre it instead,
    the way a picture frame turns a directional moulding: the crossing's
    own 2x2 m square is cut by both diagonals into 4 wedges (N/E/S/W, one
    per arm), each carrying that arm's own UV formula in toward the centre.
    Where two wedges meet, the two formulas actually agree exactly (their
    only difference is x<->y, and every point on a corner-to-corner
    diagonal has x == y or x+y == TILE, which is exactly where the two
    formulas coincide) -- a true seamless mitre, not an approximation."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    if zen_coll is not None:
        for o in [o for o in bpy.data.objects if o.name == ob.name + "_ZEN"]:
            bpy.data.meshes.remove(o.data)
    bm = bmesh.new()
    faces, V = _grid(bm, lambda i, j: _road_kind(i, j, mode))
    half = ROAD_W / 2.0
    mid = TILE / 2.0
    wedge = {}                                      # centre triangle -> "ns" / "ew"
    if mode == "junction":
        lo, hi = mid - half, mid + half
        centre = [f for f, k in faces if k == "road"
                  and lo < f.calc_center_median().x < hi and lo < f.calc_center_median().y < hi]
        # FACES_ONLY, not FACES: the centre's own corner/midpoint verts
        # (including V[(2,2)]) would otherwise be dropped as "orphaned" by
        # deleting their only faces, but the mitre triangles below reuse
        # every one of them.
        bmesh.ops.delete(bm, geom=centre, context='FACES_ONLY')
        cs = set(centre)
        faces = [(f, k) for f, k in faces if f not in cs]
        c = V[(2, 2)]                                # the crossing's own centre point
        # each wedge kept split at the SAME edge midpoints the grid already
        # has (so its outer edge still matches the arm quad next to it, and
        # the tile's own x=2/y=2 boundary rows are untouched) -- one wedge
        # is 2 triangles, not 1, but the mitre direction is unchanged.
        tris = [(V[(1, 3)], V[(2, 3)], c, "ns"), (V[(2, 3)], V[(3, 3)], c, "ns"),   # north
                (V[(3, 3)], V[(3, 2)], c, "ew"), (V[(3, 2)], V[(3, 1)], c, "ew"),   # east
                (V[(3, 1)], V[(2, 1)], c, "ns"), (V[(2, 1)], V[(1, 1)], c, "ns"),   # south
                (V[(1, 1)], V[(1, 2)], c, "ew"), (V[(1, 2)], V[(1, 3)], c, "ew")]   # west
        for a, b, cc, w in tris:
            f = bm.faces.new((a, b, cc))
            faces.append((f, "road"))
            wedge[f] = w
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])

    def uv(f, k, uvl):
        if k == "flat":
            set_grid_uv(f, uvl, 5.0)
            return
        # Pick the formula from the FACE (once, from its wedge tag or its
        # centre) -- picking it per VERTEX let a boundary cell see two
        # different formulas across its own corners, shearing that one
        # quad's UV (world/uv edge ratio ~0.9 on one edge vs ~2.0 on the
        # other, instead of ~2.0 on both).
        w = wedge.get(f)
        if w is None:
            cx = f.calc_center_median().x
            w = "ns" if (mode == "straight" or abs(cx - mid) <= half + 1e-4) else "ew"
        for loop in f.loops:
            p = loop.vert.co
            if w == "ns":
                u, v = (p.x - mid) / (2 * half) + 0.5, p.y / (2 * half)
            else:                                            # the E-W arm of a junction
                u, v = (p.y - mid) / (2 * half) + 0.5, p.x / (2 * half)
            loop[uvl].uv = (u, v)
    return _finish(ob, bm, faces, V, mats, ("flat", "road"), seed, zen_coll, uv)
