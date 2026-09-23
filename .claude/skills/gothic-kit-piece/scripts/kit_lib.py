# Helper library for building Gothic modular-kit pieces in Blender via the
# blender MCP `execute_blender_code` tool. Snippet library, not an add-on:
# exec() it from disk at the top of a build call, e.g.
#
#   exec(open(KIT_LIB_PATH).read())
#
# (KIT_LIB_PATH = .claude/skills/gothic-kit-piece/scripts/kit_lib.py)
#
# Read SKILL.md first. The rules in short: ONE connected quad mesh per piece,
# no poles, no Join/Boolean, detail grown out of the surface (extrude/inset
# on a pre-planned grid), flat one-texture-per-face materials, triangulate
# only on the hidden export copy.

import bpy
import bmesh
import math
import os
from mathutils import Vector

# --- grid constants (see SKILL.md "Module grid") ------------------------------
# 1 Blender unit = 1 metre in the reference village file. Verified from vob
# sizes there (cart 1.8x3.0x1.5, statue 5.9 tall). Change these in ONE place.
U = 1.0            # base cell
BAY = 4.0          # wall bay width (4 U)
STOREY = 3.0       # floor-to-floor height
WALL_T = 0.4       # wall thickness
DOOR_W, DOOR_H = 1.2, 2.2
WIN_W, WIN_H, WIN_SILL = 1.0, 1.2, 1.0

# Where the shared NewWorld/OldWorld material library lives (one material per
# level texture, names == texture filenames without extension).
_HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else ""
MATERIAL_LIB = os.environ.get(
    "KIT_MATERIAL_LIB",
    "/Users/jakubjaworski/Creativity/Blender Projects/Blender User Scripts/"
    "Blend-Zen/asset_catalog/materials_levels.blend",
)


# --- materials ---------------------------------------------------------------

def ensure_material(name):
    """Return the material `name`, appending it from MATERIAL_LIB if this
    file doesn't have it yet. Never creates a new node graph -- the library
    materials already are the reference recipe (Image Texture -> Principled
    Base Color). Raises if the name is not in the library (typo guard)."""
    mat = bpy.data.materials.get(name)
    if mat:
        return mat
    with bpy.data.libraries.load(MATERIAL_LIB, link=False) as (src, dst):
        if name not in src.materials:
            raise KeyError("material %r not in %s" % (name, MATERIAL_LIB))
        dst.materials = [name]
    return bpy.data.materials[name]


def slot_for(obj, name):
    """Index of material `name` in obj's slots, adding the slot if needed."""
    mat = ensure_material(name)
    for i, m in enumerate(obj.data.materials):
        if m == mat:
            return i
    obj.data.materials.append(mat)
    return len(obj.data.materials) - 1


# --- slab from a cell mask ---------------------------------------------------

def slab_from_mask(bm, xs, zs, solid, thickness=WALL_T, y0=0.0):
    """A thick wall panel as ONE closed-boundary quad mesh.

    xs, zs : sorted grid-line coordinates (need not be uniform -- put lines
             exactly where a door edge, window edge, timber or beam edge
             should land; that is the whole point of planning the grid).
    solid  : solid[i][k] True if cell (xs[i]..xs[i+1], zs[k]..zs[k+1]) is
             wall. False cells are openings (doors, windows, gaps).
    Front face at y=y0, back face at y=y0+thickness. Reveals (the jambs and
    sills around openings) and the panel's outer edge are quads created
    wherever a solid cell borders a void or the outside, so there is no
    Boolean, no n-gon and no pole.

    Returns dict(front=[faces], back=[faces], side=[faces], reveal=[faces],
    F=front vert grid, B=back vert grid). Only verts that some solid cell
    touches are created.
    """
    nx, nz = len(xs) - 1, len(zs) - 1
    F, B = {}, {}

    def fv(i, k):
        if (i, k) not in F:
            F[(i, k)] = bm.verts.new((xs[i], y0, zs[k]))
        return F[(i, k)]

    def bv(i, k):
        if (i, k) not in B:
            B[(i, k)] = bm.verts.new((xs[i], y0 + thickness, zs[k]))
        return B[(i, k)]

    def is_solid(i, k):
        return 0 <= i < nx and 0 <= k < nz and solid[i][k]

    out = dict(front=[], back=[], side=[], reveal=[])
    for i in range(nx):
        for k in range(nz):
            if not solid[i][k]:
                continue
            # front (normal -Y), back (normal +Y)
            out["front"].append(bm.faces.new((fv(i, k), fv(i + 1, k), fv(i + 1, k + 1), fv(i, k + 1))))
            out["back"].append(bm.faces.new((bv(i, k), bv(i, k + 1), bv(i + 1, k + 1), bv(i + 1, k))))
            # edges shared with a void / outside -> side or reveal quad
            for di, dk, a, b in (
                (-1, 0, (i, k + 1), (i, k)),          # left edge
                (1, 0, (i + 1, k), (i + 1, k + 1)),   # right edge
                (0, -1, (i, k), (i + 1, k)),          # bottom edge
                (0, 1, (i + 1, k + 1), (i, k + 1)),   # top edge
            ):
                if is_solid(i + di, k + dk):
                    continue
                inside = 0 <= i + di < nx and 0 <= k + dk < nz
                f = bm.faces.new((fv(*a), fv(*b), bv(*b), bv(*a)))
                (out["reveal"] if inside else out["side"]).append(f)
    out["F"], out["B"] = F, B
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return out


def slab_lean(bm, xs, zs, solid, back_xs, back_zs, openings, thickness=WALL_T, y0=0.0):
    """Like slab_from_mask, but the BACK face uses its own, much coarser grid.

    The front face needs many grid lines (timbers, plinth, sill, grooves...).
    The back face is a flat wall and only needs lines where an opening edge
    turns a corner, plus rows/cols that keep its opening-edge vertices
    aligned with the front's so the reveals stay quads. Everything the two
    faces do not share is bridged by `_stitch`, which makes quads where the
    two edge chains line up and triangles where they don't. Those triangles
    lie on the flat top/bottom/reveal planes only (the user-approved place
    for tris); no triangle ever touches a raised or textured relief face.

    `openings` = list of (x0, x1, z0, z1); the outer domain is taken from
    xs/zs. Returns the same dict as slab_from_mask (front/back/side/reveal).
    """
    def grid(gxs, gzs, y, keep):
        V, faces = {}, []
        def v(i, k):
            if (i, k) not in V:
                V[(i, k)] = bm.verts.new((gxs[i], y, gzs[k]))
            return V[(i, k)]
        for i in range(len(gxs) - 1):
            for k in range(len(gzs) - 1):
                if keep[i][k]:
                    faces.append((i, k, v(i, k), v(i + 1, k), v(i + 1, k + 1), v(i, k + 1)))
        return V, faces

    back_solid = mask_with_openings(back_xs, back_zs, openings)
    FV, ffaces = grid(xs, zs, y0, solid)
    BV, bfaces = grid(back_xs, back_zs, y0 + thickness, back_solid)
    out = dict(front=[], back=[], side=[], reveal=[])
    for (i, k, a, b, c, d) in ffaces:
        out["front"].append(bm.faces.new((a, b, c, d)))
    for (i, k, a, b, c, d) in bfaces:
        out["back"].append(bm.faces.new((a, d, c, b)))

    # boundary polylines: every rectangle (outer domain + each opening) has 4
    # sides; collect the front and back verts lying on each side, sorted.
    def on_side(verts, axis, val, lo, hi, other):
        pts = [v for v in verts if abs(v.co[axis] - val) < 1e-5 and lo - 1e-5 <= v.co[other] <= hi + 1e-5]
        return sorted(pts, key=lambda v: v.co[other])

    fverts, bverts = list(FV.values()), list(BV.values())
    x_lo, x_hi, z_lo, z_hi = xs[0], xs[-1], zs[0], zs[-1]
    rects = [((x_lo, x_hi, z_lo, z_hi), "side")] + [(o, "reveal") for o in openings]
    for (x0, x1, z0, z1), kind in rects:
        for axis, val, lo, hi, other in ((2, z0, x0, x1, 0), (2, z1, x0, x1, 0),
                                         (0, x0, z0, z1, 2), (0, x1, z0, z1, 2)):
            fch = on_side(fverts, axis, val, lo, hi, other)
            bch = on_side(bverts, axis, val, lo, hi, other)
            # a front vert only counts if it is really on this rect's edge
            # loop (a solid cell borders the void): drop verts strictly
            # inside the rect for "reveal" (they belong to no boundary).
            out[kind].extend(_stitch(bm, fch, bch, other))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return out


def _stitch(bm, F, B, key):
    """Bridge two vertex chains (sorted along axis `key`) with quads where
    their parameters coincide and triangles elsewhere. Chains may share
    their end vertices (a closed outline split in two): degenerate faces
    collapse to triangles / are skipped."""
    faces = []

    def mk(*vs):
        uniq = []
        for v in vs:
            if v not in uniq:
                uniq.append(v)
        if len(uniq) >= 3:
            faces.append(bm.faces.new(uniq))
    i = j = 0
    while i < len(F) - 1 or j < len(B) - 1:
        fa = F[i + 1].co[key] if i < len(F) - 1 else 1e9
        ba = B[j + 1].co[key] if j < len(B) - 1 else 1e9
        if abs(fa - ba) < 1e-5:
            mk(F[i], F[i + 1], B[j + 1], B[j])
            i += 1
            j += 1
        elif fa < ba:
            mk(F[i], F[i + 1], B[j])
            i += 1
        else:
            mk(F[i], B[j + 1], B[j])
            j += 1
    return faces


def planar_partition(bm, xs, zs, rid, y, forced=()):
    """Mesh a flat, axis-aligned region of a grid with as FEW faces as the
    neighbours allow. Vertices exist only where they are needed:

      * a corner of some region (convex/concave, incl. voids), or
      * in `forced` = [(x, z), ...] (e.g. the identical rows every bay must
        carry on its snap planes so any two bays weld).

    rid[i][k] = hashable region id of cell (xs[i]..xs[i+1], zs[k]..zs[k+1]),
    or None for a void. Cells of one region are merged into maximal
    rectangles; a rectangle whose sides pick up extra vertices from its
    neighbours is bridged into quads (where the two opposite chains line up)
    and flat triangles (elsewhere) instead of an n-gon. Returns
    (faces_with_rid, {(i,k): BMVert}) so callers can bridge the boundaries.
    """
    nx, nz = len(xs) - 1, len(zs) - 1
    R = lambda i, k: rid[i][k] if 0 <= i < nx and 0 <= k < nz else None
    K = set()
    for i in range(nx + 1):
        for k in range(nz + 1):
            cells = [R(i - 1, k - 1), R(i, k - 1), R(i - 1, k), R(i, k)]   # SW SE NW NE
            for r in {c for c in cells if c is not None}:
                cnt = [c == r for c in cells]
                n = sum(cnt)
                if n in (1, 3) or (n == 2 and ((cnt[0] and cnt[3]) or (cnt[1] and cnt[2]))):
                    K.add((i, k))
                    break
    def idx(vals, v):
        for n, x in enumerate(vals):
            if abs(x - v) < 1e-6:
                return n
        return None
    for (fx, fz) in forced:
        a, b = idx(xs, fx), idx(zs, fz)
        if a is not None and b is not None:
            K.add((a, b))
    used = [[False] * nz for _ in range(nx)]
    rects = []
    for k in range(nz):
        for i in range(nx):
            if used[i][k] or rid[i][k] is None:
                continue
            r = rid[i][k]
            j = i
            while j + 1 < nx and rid[j + 1][k] == r and not used[j + 1][k]:
                j += 1
            k2 = k
            while k2 + 1 < nz and all(rid[a][k2 + 1] == r and not used[a][k2 + 1] for a in range(i, j + 1)):
                k2 += 1
            for a in range(i, j + 1):
                for b in range(k, k2 + 1):
                    used[a][b] = True
            rects.append((i, j + 1, k, k2 + 1, r))
    for (i0, i1, k0, k1, r) in rects:
        K |= {(i0, k0), (i1, k0), (i1, k1), (i0, k1)}
    V = {}
    def v(i, k):
        if (i, k) not in V:
            V[(i, k)] = bm.verts.new((xs[i], y, zs[k]))
        return V[(i, k)]
    out = []
    for (i0, i1, k0, k1, r) in rects:
        bot = [v(a, k0) for a in range(i0, i1 + 1) if (a, k0) in K]
        top = [v(a, k1) for a in range(i0, i1 + 1) if (a, k1) in K]
        lef = [v(i0, b) for b in range(k0, k1 + 1) if (i0, b) in K]
        rig = [v(i1, b) for b in range(k0, k1 + 1) if (i1, b) in K]
        if len(bot) == 2 and len(top) == 2 and len(lef) == 2 and len(rig) == 2:
            fs = [bm.faces.new((bot[0], bot[1], top[1], top[0]))]
        elif len(bot) == 2 and len(top) == 2:
            fs = _stitch(bm, lef, rig, 2)
        elif len(lef) == 2 and len(rig) == 2:
            fs = _stitch(bm, bot, top, 0)
        else:
            poly = bot + rig[1:] + top[::-1][1:] + lef[::-1][1:-1]
            f = bm.faces.new(poly)
            fs = bmesh.ops.triangulate(bm, faces=[f], quad_method='BEAUTY', ngon_method='EAR_CLIP')["faces"]
        out += [(f, r) for f in fs]
    return out, V


def tensor_partition(bm, xs, zs, rid, y, protect_x=(), protect_z=()):
    """Quad-only meshing of a flat region: a grid whose redundant lines have been
    dissolved. A grid line is redundant when EVERY cell pair it separates has the
    same region id (or both are void) and it is not protected; removing it merges
    the two cell columns/rows into bigger quads, so there are never T-junctions,
    fans, poles or triangles. Returns ([(face, rid)], {(x, z): BMVert}, xs', zs')."""
    xs, zs = list(xs), list(zs)
    rid = [list(col) for col in rid]
    px = {round(v, 5) for v in protect_x}
    pz = {round(v, 5) for v in protect_z}
    changed = True
    while changed:
        changed = False
        for i in range(1, len(xs) - 1):
            if round(xs[i], 5) in px:
                continue
            if all(rid[i - 1][k] == rid[i][k] for k in range(len(zs) - 1)):
                xs.pop(i)
                rid.pop(i)
                changed = True
                break
        if changed:
            continue
        for k in range(1, len(zs) - 1):
            if round(zs[k], 5) in pz:
                continue
            if all(rid[i][k - 1] == rid[i][k] for i in range(len(xs) - 1)):
                zs.pop(k)
                for col in rid:
                    col.pop(k)
                changed = True
                break
    V = {}
    def v(i, k):
        key = (round(xs[i], 5), round(zs[k], 5))
        if key not in V:
            V[key] = bm.verts.new((xs[i], y, zs[k]))
        return V[key]
    out = []
    for i in range(len(xs) - 1):
        for k in range(len(zs) - 1):
            if rid[i][k] is None:
                continue
            out.append((bm.faces.new((v(i, k), v(i + 1, k), v(i + 1, k + 1), v(i, k + 1))), rid[i][k]))
    return out, V, xs, zs


def slab_planar(bm, xs, zs, rid_front, openings, protect_x, protect_z, thickness=WALL_T, y0=0.0,
                split_x=()):
    """Wall slab, all-quad on every visible surface. Front from `rid_front`
    (None = void); the BACK is one flat region with the same voids and a coarser
    grid (only opening edges, the end columns and the rows the openings' reveals
    need), both via tensor_partition. Reveals are 1:1 quads between the front and
    back opening-edge chains. The flat top/bottom strips (hidden under the roof /
    on the floor) are zipped between the two chains, which can leave a few flat
    triangles THERE only. Returns dict(front=[(face, rid)], back=[faces],
    side=[faces], reveal=[faces])."""
    nx, nz = len(xs) - 1, len(zs) - 1
    frontf, FV, fxs, fzs = tensor_partition(bm, xs, zs, rid_front, y0, protect_x=protect_x, protect_z=protect_z)
    def on_open_edge(p):
        for (x0, x1, z0, z1) in openings:
            if x0 - 1e-6 <= p[0] <= x1 + 1e-6 and z0 - 1e-6 <= p[1] <= z1 + 1e-6 and (
                    abs(p[0] - x0) < 1e-6 or abs(p[0] - x1) < 1e-6 or abs(p[1] - z0) < 1e-6 or abs(p[1] - z1) < 1e-6):
                return True
        return False
    need = [p for p in FV if on_open_edge(p)]          # front verts on opening edges
    col = lambda i: sum((xs[i] + xs[i + 1]) / 2 > sx for sx in split_x)
    rid_back = [[None if rid_front[i][k] is None else ("back", col(i)) for k in range(nz)] for i in range(nx)]
    bx = list(protect_x) + [p[0] for p in need]
    bz = list(protect_z) + [p[1] for p in need]
    backf, BV, _, _ = tensor_partition(bm, xs, zs, rid_back, y0 + thickness, protect_x=bx, protect_z=bz)
    out = dict(front=frontf, back=[f for f, _ in backf], side=[], reveal=[])
    fverts, bverts = list(FV.values()), list(BV.values())
    def on_side(verts, axis, val, lo, hi, other):
        pts = [q for q in verts if abs(q.co[axis] - val) < 1e-5 and lo - 1e-5 <= q.co[other] <= hi + 1e-5]
        return sorted(pts, key=lambda q: q.co[other])
    rects = [((xs[0], xs[-1], zs[0], zs[-1]), "side")] + [(o, "reveal") for o in openings]
    for (x0, x1, z0, z1), kind in rects:
        for axis, val, lo, hi, other in ((2, z0, x0, x1, 0), (2, z1, x0, x1, 0),
                                         (0, x0, z0, z1, 2), (0, x1, z0, z1, 2)):
            out[kind].extend(_stitch(bm, on_side(fverts, axis, val, lo, hi, other),
                                     on_side(bverts, axis, val, lo, hi, other), other))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return out


def mask_with_openings(xs, zs, openings):
    """solid[][] all True except cells inside each (x0, x1, z0, z1) opening.
    Opening edges MUST coincide with xs/zs lines (build xs/zs from them)."""
    nx, nz = len(xs) - 1, len(zs) - 1
    solid = [[True] * nz for _ in range(nx)]
    for (x0, x1, z0, z1) in openings:
        for i in range(nx):
            for k in range(nz):
                if xs[i] >= x0 - 1e-6 and xs[i + 1] <= x1 + 1e-6 \
                        and zs[k] >= z0 - 1e-6 and zs[k + 1] <= z1 + 1e-6:
                    solid[i][k] = False
    return solid


def lines_from(*coords):
    """Sorted unique grid lines (rounded to 1 mm) from any mix of numbers /
    iterables -- handy for merging bay edges with opening edges."""
    s = set()
    for c in coords:
        for v in (c if hasattr(c, "__iter__") else [c]):
            s.add(round(v, 3))
    return sorted(s)


# --- detail: grow it out of the surface --------------------------------------

def extrude_faces(bm, faces, dist, along=None, with_sides=False):
    """Extrude `faces` (a region) by `dist` along their average normal (or
    `along`), keeping everything welded to the source surface. This is how a
    timber, a plinth, a sill or a cornice is made: NEVER as a separate box.
    Returns the new cap faces, or (caps, sides) with `with_sides=True`
    (you need the sides to give them the region's material)."""
    faces = list(faces)
    if along is None:
        n = Vector()
        for f in faces:
            n += f.normal
        along = n.normalized()
    ret = bmesh.ops.extrude_face_region(bm, geom=faces)
    # extrude_face_region leaves the source faces in place, which would
    # leave an internal double wall (edges with 3+ faces). Drop them.
    # 'FACES' (not 'FACES_ONLY') also drops the region's now-unused interior
    # edges, which would otherwise linger as loose edges.
    bmesh.ops.delete(bm, geom=faces, context='FACES')
    verts = [g for g in ret["geom"] if isinstance(g, bmesh.types.BMVert)]
    # ret["geom"] holds the cap faces AND the new side-wall faces. Caps are
    # the ones made only of duplicated verts; sides also touch old verts.
    new_verts = set(verts)
    caps = [g for g in ret["geom"] if isinstance(g, bmesh.types.BMFace)
            and all(v in new_verts for v in g.verts)]
    bmesh.ops.translate(bm, verts=verts, vec=along * dist)
    if with_sides:
        capset = set(caps)
        sides = [g for g in ret["geom"] if isinstance(g, bmesh.types.BMFace) and g not in capset]
        return caps, sides
    return caps


def inset(bm, faces, thickness, depth=0.0):
    """Inset a face region. The faces you pass stay valid and become the
    inner region (pushed along the normal by `depth`, + = outward); the
    returned faces are the new ring around it. Quads in, quads out. Inset +
    positive depth on a raised cap is how a chamfered / stepped edge is made."""
    ret = bmesh.ops.inset_region(bm, faces=list(faces), thickness=thickness, depth=depth,
                                 use_even_offset=True)
    return ret["faces"]


def jitter(bm, verts, amount, seed=0, keep_planes=(), period_x=None, share_y=False):
    """Deterministic hand-made irregularity: nudge `verts` by up to `amount`
    (a Vector or float, per axis) so surfaces stop looking machine-flat.
    `period_x` makes the noise repeat every N units in x, so the left and
    right snap planes of a piece (x=0 and x=period_x) get IDENTICAL offsets
    and neighbouring pieces still mate. `keep_planes` = [(axis, value)]:
    verts on those planes are not moved along that axis. `share_y=True`
    ignores y when seeding, so a front and back vert at the same (x, z) move
    together (use it for opening edges so reveals stay planar)."""
    import random
    amt = Vector((amount, amount, amount)) if isinstance(amount, (int, float)) else Vector(amount)
    for v in verts:
        x = v.co.x % period_x if period_x else v.co.x
        rnd = random.Random(hash((round(x, 3), round(v.co.z, 3), 0 if share_y else round(v.co.y, 3), seed)))
        d = Vector(((rnd.random() * 2 - 1) * amt.x,
                    (rnd.random() * 2 - 1) * amt.y,
                    (rnd.random() * 2 - 1) * amt.z))
        for ax, val in keep_planes:
            if abs(v.co[ax] - val) < 1e-4:
                d[ax] = 0.0
        v.co += d


# --- UVs ---------------------------------------------------------------------
# KIT PIECES MUST TILE ACROSS PIECE BOUNDARIES. So UVs are computed from
# piece-local coordinates anchored on the module grid (origin at the piece
# origin, which is itself on the grid) and the tile size divides the module.

def set_grid_uv(face, uv_layer, tile, offset=(0.0, 0.0, 0.0)):
    """Triplanar-by-dominant-axis, anchored to local coords. `tile` = world
    units per texture repeat (see SKILL.md texel table; make it divide BAY).
    Side/back/reveal faces use the same rule, so a wall's jamb reads as a
    continuation of the wall texture."""
    n = face.normal
    ax, ay, az = abs(n.x), abs(n.y), abs(n.z)
    ox, oy, oz = offset
    for loop in face.loops:
        c = loop.vert.co
        if az >= ax and az >= ay:
            uv = ((c.x + ox) / tile, (c.y + oy) / tile)
        elif ay >= ax:
            uv = ((c.x + ox) / tile, (c.z + oz) / tile)
        else:
            uv = ((c.y + oy) / tile, (c.z + oz) / tile)
        loop[uv_layer].uv = uv


def _tri(d):
    """Triangle wave 0..1..0 of a running distance (mirror repeat)."""
    d = d % 2.0
    return d if d <= 1.0 else 2.0 - d


def _fold_coord(c, cen, size, origin, bounds):
    """Texture coordinate 0..1 of world coord `c` along one axis.

    Uniform mode (bounds=None): mirror every `size` metres from `origin`.
    Piecewise mode: `bounds` is a sorted list of world coords (put them on
    real grid lines). Each span between two bounds maps the window at
    `size` metres per window, but never less than the span itself, and
    mirrors at every bound, so the texture stays continuous while no face
    ever has to be cut just for the UVs."""
    if not bounds:
        seg = math.floor((cen - origin) / size + 1e-6)
        f = (c - origin - seg * size) / size
        return 1.0 - f if seg % 2 else f
    d0 = 0.0
    for k in range(len(bounds) - 1):
        lo, hi = bounds[k], bounds[k + 1]
        leff = max(hi - lo, size)
        if cen < hi - 1e-6 or k == len(bounds) - 2:
            return _tri(d0 + (c - lo) / leff)
        d0 += (hi - lo) / leff
    return 0.0


def set_window_uv(face, uv_layer, size, window, swap=False, origin=(0.0, 0.0, 0.0),
                  bounds=None):
    """Map a face into a CROPPED region of a texture, mirror-repeating it
    across the surface.

    Many Gothic city textures (NW_City_Wall_02/03/04, InsideWall_13, ...)
    are *baked panel tiles*: a plaster field with the timber frame painted
    into the border. Tiled normally they print a frame every tile, which
    fights real timber geometry. Crop to the clean interior instead:

      window = (u0, u1, v0, v1)   texture sub-rectangle to use, 0..1
      size   = (sa, sb)           world metres the window covers along the
                                  face's two surface axes (a, b)
      swap   = put the long axis on V (grain along a horizontal beam)
      origin = world point the mirror lines are measured from, per axis
      bounds = {world_axis: [b0, b1, ...]} mirror at these world coords
               instead of every `size` (see _fold_coord). Choose bounds that
               are already grid lines, so mirroring costs NO extra geometry.

    Surface axes: a face facing +-Y uses (x, z); +-X uses (y, z); +-Z (x, y).
    """
    n = face.normal
    ax, ay, az = abs(n.x), abs(n.y), abs(n.z)
    ia, ib = (0, 2) if ay >= ax and ay >= az else ((1, 2) if ax >= az else (0, 1))
    cen = face.calc_center_median()
    u0, u1, v0, v1 = window
    bounds = bounds or {}
    for loop in face.loops:
        c = loop.vert.co
        fa = _fold_coord(c[ia], cen[ia], size[0], origin[ia], bounds.get(ia))
        fb = _fold_coord(c[ib], cen[ib], size[1], origin[ib], bounds.get(ib))
        if swap:
            fa, fb = fb, fa
        loop[uv_layer].uv = (u0 + fa * (u1 - u0), v0 + fb * (v1 - v0))


def set_wrap_uv(face, uv_layer, per_metre, offset=(0.0, 0.0)):
    """Plain planar UVs that rely on the texture REPEATING: u = a * ku + ou,
    v = b * kv + ov on the face's own surface axes (see set_window_uv for
    which). `per_metre = (ku, kv)` is UV units per metre, so
    ku = pixels_per_metre / texture_width_px. Use for tileable textures
    (stone, planks) where no crop is needed. Keep the v range inside the
    'body' of a texture that has a border/cornice band."""
    n = face.normal
    ax, ay, az = abs(n.x), abs(n.y), abs(n.z)
    ia, ib = (0, 2) if ay >= ax and ay >= az else ((1, 2) if ax >= az else (0, 1))
    for loop in face.loops:
        c = loop.vert.co
        loop[uv_layer].uv = (c[ia] * per_metre[0] + offset[0], c[ib] * per_metre[1] + offset[1])


def set_beam_uv(face, uv_layer, orientation, per_metre, u_start, across_origin):
    """UVs for a beam texture whose grain runs along V (e.g. WoodBeam_01).
    orientation 'V' = member runs along z, 'H' = along x. The texture wraps
    along the member (a strap/band repeats every 1/kv metres -- iron bands,
    a feature, not a bug); across it takes a narrow slice starting at
    `u_start` so neighbouring members show different grain.
    `across_origin` = the member's own edge on its across axis.

    Picks "along"/"across" from the face's OWN edges (whichever is closer to
    the grain axis is along, the other is across), not from its normal or a
    single world coordinate. A face square-on to an axis reduces to exactly
    the old formula; a face that isn't (a mitred corner strip, a small end
    cap) still gets its REAL width across, instead of a world-axis reading
    that can be almost zero for it (grain squeezed to a stretched sliver)."""
    ku, kv = per_metre
    axis = 2 if orientation == "V" else 0
    verts = [l.vert for l in face.loops]
    if len(verts) < 3:
        return
    e_a, e_b = verts[1].co - verts[0].co, verts[-1].co - verts[0].co
    along, across = (e_a, e_b) if abs(e_a[axis]) >= abs(e_b[axis]) else (e_b, e_a)
    al = along.length or 1e-6
    dv = along / al
    ac = across.length or 1e-6
    du = across / ac
    origin = Vector((0.0, 0.0, 0.0))
    origin[axis] = 0.0
    ref_axis = 0 if axis == 2 else 2
    origin[ref_axis] = across_origin
    for loop in face.loops:
        rel = loop.vert.co - origin
        loop[uv_layer].uv = (u_start + rel.dot(du) * ku, rel.dot(dv) * kv)


def set_directional_uv(face, uv_layer, origin, dir_u, dir_v, tile_u, tile_v):
    """For anything with grain: beams, planks, stair treads, roads, roof
    courses. dir_u = along the grain (unit Vector), dir_v = across. One
    shared frame per run -- never per-face cube projection."""
    for loop in face.loops:
        rel = loop.vert.co - origin
        loop[uv_layer].uv = (rel.dot(dir_u) / tile_u, rel.dot(dir_v) / tile_v)


# --- piece assembly ----------------------------------------------------------

def new_piece(name, collection=None):
    """Empty mesh object ready to be filled from a bmesh. Naming: see SKILL.md
    (NW_KIT_<FAMILY>_<PIECE>_<VAR>)."""
    me = bpy.data.meshes.new(name)
    ob = bpy.data.objects.new(name, me)
    (collection or bpy.context.scene.collection).objects.link(ob)
    if "Float2" not in me.uv_layers:
        me.uv_layers.new(name="Float2")
    return ob


def write_piece(ob, bm):
    """Flush bm into ob's mesh, force flat shading. Call after all UV /
    material_index work, on the quad master."""
    bm.to_mesh(ob.data)
    ob.data.update()
    for p in ob.data.polygons:
        p.use_smooth = False


def make_export_copy(ob, hidden_collection):
    """Triangulated ZenGin copy: `<name>_ZEN`, hidden, next to the quad
    master. The master is never triangulated (mirrors NW_VILLAGE_01 /
    NW_VILLAGE_01_ZEN in the village file)."""
    cp = ob.copy()
    cp.data = ob.data.copy()
    cp.name = ob.name + "_ZEN"
    cp.data.name = cp.name
    hidden_collection.objects.link(cp)
    bm = bmesh.new()
    bm.from_mesh(cp.data)
    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method='BEAUTY', ngon_method='BEAUTY')
    bm.to_mesh(cp.data)
    bm.free()
    for p in cp.data.polygons:
        p.use_smooth = False
    cp.hide_viewport = True
    return cp


def mark_asset(ob, catalog_id=None):
    """Mark as a Blender asset. Needs context override from a script (see
    documentation/ASSET_LIBRARY_HANDOFF.md). Generate the preview later, one
    piece at a time, from the UI/timer -- batching previews crashes Blender."""
    with bpy.context.temp_override(id=ob):
        bpy.ops.asset.mark_single()
    if catalog_id:
        ob.asset_data.catalog_id = catalog_id


# --- verification (run BEFORE make_export_copy) --------------------------------

def find_stretched_uv_faces(bm, uv_layer, anisotropy=1.8, outlier_factor=4.0):
    """Faces whose UV doesn't preserve the surface's real proportions, so a
    fixed-scale material prints stretched instead of true-to-size. Catches
    what a single world-area/uv-area ratio misses: a SHEARED quad (some
    corners mapped by one formula, others by another -- classically a UV
    function branching on each vertex's OWN position instead of the whole
    face's) has a normal-looking area ratio but very different scale on its
    two edge directions. Two independent checks, either one flags a face:

      * anisotropic -- (world edge length / uv edge length) on two adjacent
        edges of the same face is distorted well beyond what's NORMAL for
        that material in this piece. A non-square base texture (a beam
        strip UV with per_metre=(ku,kv), ku != kv, is a deliberate, uniform
        distortion baked into every beam face) is fine; what's wrong is a
        face whose distortion doesn't match its own material's usual
        distortion (one bad quad among consistent ones).
      * area outlier -- world-area/uv-area more than `outlier_factor`x off
        the median for that material IN THIS PIECE (every other face of the
        same texture is the reference for what "normal" density looks like).

    Returns [(face_index, material_index, reason, ratio)]."""
    import statistics

    def poly_uv_area(f):
        pts = [l[uv_layer].uv for l in f.loops]
        a = 0.0
        for i in range(len(pts)):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % len(pts)]
            a += x1 * y2 - x2 * y1
        return abs(a) / 2.0

    by_mat = {}
    for f in bm.faces:
        if len(f.loops) < 3:
            continue
        verts = [l.vert for l in f.loops]
        uvs = [l[uv_layer].uv for l in f.loops]
        we1 = (verts[1].co - verts[0].co).length
        we2 = (verts[-1].co - verts[0].co).length
        ue1 = (uvs[1] - uvs[0]).length
        ue2 = (uvs[-1] - uvs[0]).length
        wa, ua = f.calc_area(), poly_uv_area(f)
        by_mat.setdefault(f.material_index, []).append((f, we1, we2, ue1, ue2, wa, ua))
    bad = []
    for mi, flist in by_mat.items():
        ratios = [wa / ua for (_, _, _, _, _, wa, ua) in flist if ua > 1e-9 and wa > 1e-9]
        med = statistics.median(ratios) if ratios else 0.0
        dists = [max(we1 / ue1, we2 / ue2) / min(we1 / ue1, we2 / ue2) for (_, we1, we2, ue1, ue2, _, _) in flist
                 if ue1 > 1e-9 and ue2 > 1e-9 and we1 > 1e-9 and we2 > 1e-9]
        med_dist = statistics.median(dists) if dists else 1.0
        for (f, we1, we2, ue1, ue2, wa, ua) in flist:
            if ue1 > 1e-9 and ue2 > 1e-9 and we1 > 1e-9 and we2 > 1e-9:
                d1, d2 = we1 / ue1, we2 / ue2
                dist = max(d1, d2) / min(d1, d2)
                if dist > max(anisotropy, med_dist * 1.5):
                    bad.append((f.index, mi, "anisotropic", round(dist, 2)))
                    continue
            if ua > 1e-9 and wa > 1e-9 and med > 0:
                r = wa / ua
                if r > med * outlier_factor or r < med / outlier_factor:
                    bad.append((f.index, mi, "area_outlier", round(r / med, 2)))
    return bad


def check_piece(ob, snap_planes=None, expect_tris=0, grid=U, eps=1e-4, flat_tri_ok=False):
    """Machine-checkable half of the SKILL.md checklist. Returns a dict; every
    key ending in `_bad` should be 0/empty. `snap_planes` is a list of
    (axis, value) pairs (axis 0/1/2) where open boundary edges are allowed
    (the piece's module faces, e.g. (0, 0.0) and (0, 4.0) for a wall bay's
    left/right edge)."""
    snap_planes = snap_planes or []
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()

    def on_snap(e):
        for ax, val in snap_planes:
            if all(abs(v.co[ax] - val) < eps for v in e.verts):
                return True
        return False

    sides = {}
    for f in bm.faces:
        sides[len(f.verts)] = sides.get(len(f.verts), 0) + 1
    open_edges = [e for e in bm.edges if len(e.link_faces) < 2 and not on_snap(e)]
    nonmanifold = [e for e in bm.edges if len(e.link_faces) > 2]
    loose = [v for v in bm.verts if not v.link_edges]
    # A valence-5 vertex is the normal reflex corner of a rectangular
    # opening (270 deg of surface) and is fine; 6+ is a real pole/fan.
    poles = [v for v in bm.verts if len(v.link_faces) >= 6]
    if flat_tri_ok:
        # tri fans on the flat top/bottom/reveal bridges (slab_lean) may raise
        # valence there; only count poles that touch a raised/relief face
        poles = [v for v in poles if all(len(f.verts) == 4 for f in v.link_faces)]
    val5 = sum(1 for v in bm.verts if len(v.link_faces) == 5)
    degenerate = [f for f in bm.faces if f.calc_area() < 1e-6]

    seen, comps = set(), 0
    for v in bm.verts:
        if v.index in seen:
            continue
        comps += 1
        stack = [v]
        seen.add(v.index)
        while stack:
            c = stack.pop()
            for e in c.link_edges:
                w = e.other_vert(c)
                if w.index not in seen:
                    seen.add(w.index)
                    stack.append(w)

    used = {f.material_index for f in bm.faces}
    dead_slots = [i for i in range(len(ob.data.materials)) if i not in used]
    uv = bm.loops.layers.uv.active
    bad_uv = sum(1 for f in bm.faces if uv and all(l[uv].uv.length == 0 for l in f.loops))
    stretched = find_stretched_uv_faces(bm, uv) if uv else []

    xs = [v.co.x for v in bm.verts]
    ys = [v.co.y for v in bm.verts]
    zs = [v.co.z for v in bm.verts]
    res = dict(
        faces=len(bm.faces), sides=sides,
        tris_bad=(0 if flat_tri_ok else sides.get(3, 0) - expect_tris),
        tris_info=sides.get(3, 0),
        ngons_bad=sum(n for s, n in sides.items() if s > 4),
        components_bad=comps - 1,
        open_edges_bad=len(open_edges),
        nonmanifold_bad=len(nonmanifold),
        loose_bad=len(loose),
        poles_bad=len(poles),
        valence5_info=val5,
        loose_edges_bad=sum(1 for e in bm.edges if not e.link_faces),
        degenerate_bad=len(degenerate),
        dead_material_slots=dead_slots,
        unmapped_faces_bad=bad_uv,
        stretched_uv_bad=len(stretched),
        stretched_uv_info=stretched[:10],
        bounds=((min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))),
        off_grid_verts=sum(1 for v in bm.verts
                           if any(abs(c / grid - round(c / grid)) > 1e-3 for c in v.co)),
        materials=[m.name if m else None for m in ob.data.materials],
        flat_bad=sum(1 for p in ob.data.polygons if p.use_smooth),
    )
    bm.free()
    return res
