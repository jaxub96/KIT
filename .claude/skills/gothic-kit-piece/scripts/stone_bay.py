# Stone ground floor with a jettied timber storey above (KIT_WALL_STONE_*_A).
# Needs kit_lib.py exec'd first.
#
# The idea (reference: a manor with a rubble-stone ground floor and an
# overhanging half-timbered upper floor): the kit's upper storey stays exactly
# where it is, and the stone wall under it is set back JETTY metres, so the
# timber storey sails out over it. A timber girt (bressummer) runs along the
# top of the stone wall and carries the overhang; small timber brackets under
# it read as the jetty's joist ends / corbels.
#
# Frame = the timber bays' (rebased): x 0..4 along the bay, z 0..3, the upper
# wall's inside face at y = 0 and outer plaster plane at y = -0.4. The stone
# wall's outer face is at -0.4 + JETTY, it is STONE_T thick (its inside face is
# a little into the room -- hidden behind/under the floor tiles), the girt's
# front sits just proud of the upper wall. So a stone bay goes on exactly the
# same grid point / rotation as the timber ground bay it replaces.
#
# Openings use the timber bays' rows (window 1.5-2.5 x 1.62-2.70, so the kit's
# glazing fits, moved JETTY inward), doors are round-arched. The mossy stone
# texture (NW_Seq_Maya_Stone_GreyTrans_03_XL: stone with a grass/moss band at
# its bottom edge) shows its moss only along the foot of the wall: above
# FOLD0 the v coordinate mirror-repeats inside the clean stone part.
# Welding (2026-10-04): every bay carries the same end rows (Z_ALL, the union of
# every kind's rows) and is OPEN at x = 0 / 4, so any two bays weld like the timber
# bays; corners are the end loop mitre-swept (build_stone_corner), inner corners the
# L (wall_l_inner) of two plain bays. The girt's front is the upper storey's seam
# front (-0.4 - SEAM_D), so the closed stone top covers the upper bay's open bottom.
import bpy, bmesh, math, random
from mathutils import Vector

JETTY = 0.30
STONE_T = 0.40
Y_OUT = -0.4 + JETTY                 # stone outer face
GIRT = (2.75, 3.00)                  # girt beam z range
GIRT_Y = -0.56                       # girt front = the upper storey's seam front (-0.4 - SEAM_D)
BRACKET = (2.40, 0.07)               # bracket bottom z, half width
KU, KV = 0.25, 0.5                   # stone UV per metre (1024x512 texture = 4 x 2 m)
FOLD0, FOLD = 0.46, 1.16             # moss band height (= door threshold row), then the clean stone's mirror period (fold row 1.62)
V1 = 1.0 - FOLD * KV                 # the clean stone band ends at the texture's top
V0, V2 = V1 - FOLD0 * KV, 1.0       # moss band runs continuously into it at FOLD0
TI = (300 / 256, 300 / 512)
STONE_WIN = (1.5, 2.5, 1.62, 2.62)
STONE_SILL = (1.40, 2.60, 1.50, 1.62)
DOOR_Z0 = 0.46

KINDS = {   # openings and the brackets that fit around them
    "plain": dict(brackets=(0.5, 1.5, 2.5, 3.5)),
    "window": dict(window=True, brackets=(0.55, 1.15, 2.85, 3.45)),
    "door": dict(arch=(1.4, 2.6), brackets=(0.5, 1.0, 3.0, 3.5)),
    "door_wide": dict(arch=(1.0, 3.0), brackets=(0.45, 3.55)),
}
SEAM_COLS = (0.4, 0.5, 1.25, 1.4, 1.5, 1.6, 2.4, 2.5, 2.6, 2.75, 3.5, 3.6)   # = wall_bay.SEAM_COLS
APEX = 2.62                          # every opening's top (window, both arches)
# The rows EVERY stone bay carries (so all end loops are identical): ground, door
# threshold = moss fold, sill, window bottom = fold = wide-arch spring, narrow-arch
# spring, bracket foot, opening top, girt. Everything else is dissolved
# (kit_lib.tensor_partition): a bay is ~100-200 quads like the timber bays.
ZS = (0.0, 0.46, 1.50, 1.62, 2.02, 2.40, 2.62, 2.75, 3.0)


def stone_v(z):
    """v of the stone texture at height z: moss band at the foot, then the
    clean stone mirror-repeated (continuous across every fold row)."""
    if z <= FOLD0:
        return V0 + z * KV
    t = (z - FOLD0) * KV
    span = FOLD * KV
    seg = int(t / span + 1e-9)
    frac = t - seg * span
    return V1 + frac if seg % 2 == 0 else V2 - frac


def stone_uv(f, uvl, along_x=True):
    n = f.normal
    if abs(n.z) > 0.7:                                # sills, reveals' tops / bottoms, wall top
        for l in f.loops:
            c = l.vert.co
            l[uvl].uv = (c.x * KU, V1 + 0.2 + c.y * KV)
        return
    for l in f.loops:
        c = l.vert.co
        a = c.x if abs(n.y) >= abs(n.x) else c.y
        l[uvl].uv = (a * KU, stone_v(c.z))


def _arch_grid(x0, x1, spring, n=16):
    """Grid lines a round-arched opening needs (n arc segments): jamb rows
    above the spring and top-edge columns, spaced so that _arch_point puts
    them at equal angles."""
    r = (x1 - x0) / 2
    q = n // 4
    rows = [spring + r * k / q for k in range(q + 1)]
    cols = [x0 + (x1 - x0) * k / (2 * q) for k in range(2 * q + 1)]
    return cols, rows, spring + r


def _arch_point(x, z, x0, x1, spring):
    """Where a vertex on the rectangular opening's boundary goes on the arch:
    the jambs above the spring map to 180..135 / 0..45 deg, the top edge to
    135..45 deg -- monotonic, so ANY row or column crossing the opening (not
    just the arch's own) lands on the arc in order. None = not on the arch."""
    r = (x1 - x0) / 2
    xc, apex = (x0 + x1) / 2, spring + r
    e = 1e-4
    if abs(z - apex) < e and x0 - e <= x <= x1 + e:
        a = 135.0 - 90.0 * (x - x0) / (x1 - x0)
    elif abs(x - x0) < e and spring + e < z < apex:
        a = 180.0 - 45.0 * (z - spring) / r
    elif abs(x - x1) < e and spring + e < z < apex:
        a = 45.0 * (z - spring) / r
    else:
        return None
    return xc + r * math.cos(math.radians(a)), spring + r * math.sin(math.radians(a))


def _arch(x0, x1):
    r = (x1 - x0) / 2
    return r, APEX - r                                # radius, spring


def build_stone_bay(ob, mats, kind="plain", seed=1):
    """mats = {'stone', 'timber'}. Low poly (tensor_partition), open ends with the
    shared ZS rows, open top seam in front of the upper wall. Returns check_piece()."""
    spec = KINDS[kind]
    xl = [0.0, 4.0]
    openings, regions, protect_x = [], [], [0.0, 4.0]
    if spec.get("window"):
        openings.append(STONE_WIN)
        xl += [STONE_WIN[0], STONE_WIN[1], STONE_SILL[0], STONE_SILL[1]]
        regions.append((STONE_SILL, "sill"))
    arch = None
    if spec.get("arch"):
        x0, x1 = spec["arch"]
        r, spring = _arch(x0, x1)
        arch = (x0, x1, spring)
        openings.append((x0, x1, DOOR_Z0, APEX))
        cols = [x0 + (x1 - x0) * k / 4 for k in range(5)]   # arc points along the top (45..135 deg)
        xl += cols + [x0 - 0.15, x1 + 0.15]
        protect_x += cols
        regions += [((x0 - 0.15, x0, DOOR_Z0, GIRT[0]), "surround"), ((x1, x1 + 0.15, DOOR_Z0, GIRT[0]), "surround"),
                    ((x0, x1, APEX, GIRT[0]), "surround")]
    for i, c in enumerate(spec["brackets"]):
        xl += [c - BRACKET[1], c + BRACKET[1]]
        regions.append(((c - BRACKET[1], c + BRACKET[1], BRACKET[0], GIRT[0]), ("bracket", i)))
    regions.append(((0.0, 4.0, GIRT[0], GIRT[1]), "girt"))
    xs, zs = lines_from(xl), lines_from(ZS)
    inside = lambda x, z: any(o[0] < x < o[1] and o[2] < z < o[3] for o in openings)

    def rid_at(x, z):
        if inside(x, z):
            return None
        for (a0, a1, b0, b1), rg in regions:
            if a0 < x < a1 and b0 < z < b1:
                return rg
        return ("stone", 0 if z < FOLD0 else (1 if z < FOLD0 + FOLD else 2))   # faces never cross a moss fold
    rid = [[rid_at((xs[i] + xs[i + 1]) / 2, (zs[k] + zs[k + 1]) / 2) for k in range(len(zs) - 1)]
           for i in range(len(xs) - 1)]
    bm = bmesh.new()
    r_ = slab_planar(bm, xs, zs, rid, openings, protect_x, ZS, thickness=STONE_T, y0=Y_OUT)
    if arch:                                          # the opening's top onto a semicircle (reveals follow)
        for v in bm.verts:
            p = _arch_point(v.co.x, v.co.z, *arch)
            if p:
                v.co.x, v.co.z = p
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.normal_update()
    tag = {f: q for f, q in r_["front"]}
    raised = [f for f, q in tag.items() if q is not None and q[0] != "stone"]
    caps, _ = extrude_faces(bm, raised, 0.1, with_sides=True)
    capset = set(caps)
    reg = lambda f: next((rg for (a0, a1, b0, b1), rg in regions
                          if a0 - 1e-4 < f.calc_center_median().x < a1 + 1e-4 and b0 - 1e-4 < f.calc_center_median().z < b1 + 1e-4), None)
    ctag = {f: reg(f) or "surround" for f in caps}    # (a surround face pulled down onto the arc)
    name = lambda rg: rg[0] if isinstance(rg, tuple) else rg
    DEPTH = {"girt": Y_OUT - GIRT_Y, "sill": 0.10, "surround": 0.05}
    for v in {v for f in caps for v in f.verts}:
        regs = {name(ctag[f]) for f in v.link_faces if f in capset}
        if "girt" in regs:
            d = DEPTH["girt"]
        elif "bracket" in regs:                       # slanted: deep at the girt, shallow at the foot
            t = (v.co.z - BRACKET[0]) / (GIRT[0] - BRACKET[0])
            d = 0.06 + t * (DEPTH["girt"] - 0.06)
        else:
            d = max(DEPTH[g_] for g_ in regs)
        v.co.y = Y_OUT - d
    inset(bm, [f for f in caps if name(ctag[f]) == "bracket"], 0.022, depth=0.016)
    inset(bm, [f for f in caps if name(ctag[f]) in ("sill", "surround")], 0.02, depth=0.012)
    # open ends + open top seam (in front of the upper wall's inside face y = 0)
    ends = [f for f in bm.faces if all(abs(v.co.x) < 1e-4 for v in f.verts) or all(abs(v.co.x - 4.0) < 1e-4 for v in f.verts)]
    bmesh.ops.delete(bm, geom=ends, context='FACES')
    top = [f for f in bm.faces if all(abs(v.co.z - GIRT[1]) < 1e-4 for v in f.verts)]
    bmesh.ops.bisect_plane(bm, geom=list({e for f in top for e in f.edges}) + top, plane_co=(0, 0, 0), plane_no=(0, 1, 0))
    seam = [f for f in bm.faces if all(abs(v.co.z - GIRT[1]) < 1e-4 for v in f.verts) and f.calc_center_median().y < 0]
    bmesh.ops.delete(bm, geom=seam, context='FACES')
    bm.normal_update()

    def is_timber(f):
        c = f.calc_center_median()
        if c.y > Y_OUT - 1e-4 and abs(f.normal.y) > 0.5:
            return False
        return c.y < Y_OUT - 1e-4 and any(name(rg) in ("girt", "bracket") and a0 - 1e-4 < c.x < a1 + 1e-4
                                            and b0 - 1e-4 < c.z < b1 + 1e-4 for (a0, a1, b0, b1), rg in regions)
    rnd = random.Random(seed)
    for v in bm.verts:                                # hand-laid rubble: a touch of wobble on the face
        if abs(v.co.y - Y_OUT) < 1e-4 and 0.05 < v.co.z < GIRT[0] - 0.01 and 0.01 < v.co.x < 3.99:
            v.co.y += (rnd.random() * 2 - 1) * 0.008
    ob.data.materials.clear()
    ob.data.materials.append(mats["stone"])
    ob.data.materials.append(mats["timber"])
    uvl = bm.loops.layers.uv.get("Float2") or bm.loops.layers.uv.new("Float2")
    bm.normal_update()
    for f in bm.faces:
        if is_timber(f):
            f.material_index = 1
            c = f.calc_center_median()
            if c.z < GIRT[0] - 1e-3:
                set_beam_uv(f, uvl, "V", TI, 0.3, c.x - 0.07)
            else:
                set_beam_uv(f, uvl, "H", TI, 0.12, GIRT[0])
        else:
            f.material_index = 0
            stone_uv(f, uvl)
    # the girt's top front edge = the upper storey's seam front: give it every
    # SEAM_COLS vertex so the two weld vertex for vertex (wall_bay does the same)
    on_chain = lambda v: abs(v.co.z - GIRT[1]) < 1e-4 and abs(v.co.y - GIRT_Y) < 1e-3
    grown = set()
    for c in sorted({0.15, 3.85} | set(SEAM_COLS)):
        if any(on_chain(v) and abs(v.co.x - c) < 1e-4 for v in bm.verts):
            continue
        for e in [e for e in bm.edges if e.is_boundary]:
            a, b = e.verts
            if on_chain(a) and on_chain(b) and min(a.co.x, b.co.x) < c < max(a.co.x, b.co.x):
                ne, nv = bmesh.utils.edge_split(e, a, (c - a.co.x) / (b.co.x - a.co.x))
                nv.co.x = c
                grown.update(nv.link_faces)
                break
    big = [f for f in grown if f.is_valid and len(f.verts) > 4]
    if big:
        tri = bmesh.ops.triangulate(bm, faces=big, quad_method='BEAUTY', ngon_method='BEAUTY')["faces"]
        bmesh.ops.join_triangles(bm, faces=tri, cmp_seam=False, cmp_sharp=False, cmp_uvs=True, cmp_vcols=False,
                                 cmp_materials=True, angle_face_threshold=math.radians(10.0),
                                 angle_shape_threshold=math.radians(180.0))
    write_piece(ob, bm)
    bm.free()
    return check_piece(ob, snap_planes=[(0, 0.0), (0, 4.0), (2, GIRT[1])], flat_tri_ok=True)


def build_stone_corner(ob, bay_ob, mats):
    """Outer corner: the stone bay's end loop swept round a 45 deg mitre (like
    weld_pieces.build_corner_from_bay, for the recessed stone face). Corner frame
    = KIT_WALL_CORNER_A's: inside corner at the origin; bay A runs +x (face -y),
    bay B runs +y (face -x). A loop point at depth d (bay y) lands at (0, d) on A's
    end, (d, d) on the mitre and (d, 0) on B's end, so both bays weld to it."""
    pts, mi = boundary_loop(bay_ob.data, 0, 0.0)
    pts = [(round(p.y, 5), round(p.z, 5)) for p in pts]
    n = len(pts)
    bm = bmesh.new()
    cache = {}

    def V(x, y, z):
        k = (round(x, 5), round(y, 5), round(z, 5))
        if k not in cache:
            cache[k] = bm.verts.new(k)
        return cache[k]
    kinds = {}
    for i in range(n):
        (da, za), (db, zb) = pts[i], pts[(i + 1) % n]
        if abs(za - GIRT[1]) < 1e-4 and abs(zb - GIRT[1]) < 1e-4 and max(da, db) < 1e-4:
            continue                                   # the open top seam (boundary_loop's joining lid)
        for q in ((V(0, da, za), V(0, db, zb), V(db, db, zb), V(da, da, za)),
                  (V(da, da, za), V(db, db, zb), V(db, 0, zb), V(da, 0, za))):
            u = [v for k_, v in enumerate(q) if v not in q[:k_]]
            if len(u) >= 3:                            # a loop point at depth 0 makes a triangle
                kinds[bm.faces.new(u)] = mi[i]
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.normal_update()
    ob.data.materials.clear()
    for m in bay_ob.data.materials:
        ob.data.materials.append(m)
    uvl = bm.loops.layers.uv.new("Float2")
    for f in bm.faces:
        f.material_index = kinds[f]
        if kinds[f] == 1:
            set_beam_uv(f, uvl, "H", TI, 0.12, GIRT[0])
        else:
            stone_uv(f, uvl)
    write_piece(ob, bm)
    bm.free()
    return check_piece(ob, snap_planes=[(0, 0.0), (1, 0.0), (2, GIRT[1])], flat_tri_ok=True)


# =========================================================================
# outer corner: quoin pier + girt corner block (voxel union, one mesh)
# =========================================================================
def voxel_mesh(bm, xs, ys, zs, solid):
    """Boundary quads of a union of grid cells; shared verts, no T-junctions
    (every face is one grid cell side). Returns {face: (i, j, k, axis, sign)}."""
    V = {}

    def vert(i, j, k):
        if (i, j, k) not in V:
            V[i, j, k] = bm.verts.new((xs[i], ys[j], zs[k]))
        return V[i, j, k]
    nx, ny, nz = len(xs) - 1, len(ys) - 1, len(zs) - 1
    S = lambda i, j, k: 0 <= i < nx and 0 <= j < ny and 0 <= k < nz and solid(i, j, k)
    info = {}
    for i in range(nx):
        for j in range(ny):
            for k in range(nz):
                if not S(i, j, k):
                    continue
                for ax, d in ((0, -1), (0, 1), (1, -1), (1, 1), (2, -1), (2, 1)):
                    o = [i, j, k]
                    o[ax] += d
                    if S(*o):
                        continue
                    p = [i, j, k]
                    if d == 1:
                        p[ax] += 1
                    a, b = [(1, 2), (0, 2), (0, 1)][ax]
                    q = [list(p) for _ in range(4)]
                    q[1][a] += 1
                    q[2][a] += 1
                    q[2][b] += 1
                    q[3][b] += 1
                    vs = [vert(*c) for c in q]
                    f = bm.faces.new(vs if d == -1 else vs[::-1])
                    info[f] = (i, j, k, ax, d)
    return info


def build_stone_corner_quoin(ob, mats, q=0.08, long=0.40, short=0.22, course=0.46):
    """Outer corner for two stone bays (rebased corner frame like
    KIT_WALL_CORNER_A: inside corner at the origin, one bay runs +x with its
    face to -y, the other +y with its face to -x). A quoin pier, `q` proud of
    the stone faces, with long/short corner stones alternating per course,
    and the girt's corner block on top."""
    o = Y_OUT - q                                         # pier's outer faces
    zc = [0.0]
    while zc[-1] + course < GIRT[0] - 0.2:
        zc.append(round(zc[-1] + course, 3))
    zc.append(GIRT[0])
    zs = lines_from(zc, [GIRT[1]])
    xs = lines_from([GIRT_Y, o, 0.0, o + short + q, o + long + q])
    ys = list(xs)
    k_girt = zs.index(GIRT[0])

    def solid(i, j, k):
        cx, cy, cz = (xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2, (zs[k] + zs[k + 1]) / 2
        if k >= k_girt:                                   # girt corner block
            return cx < 0.0 + 1e-6 and cy < 0.0 + 1e-6 and cx > GIRT_Y and cy > GIRT_Y and xs[i + 1] <= 0.0 + 1e-6 \
                and ys[j + 1] <= 0.0 + 1e-6
        if cx < o or cy < o:
            return False
        lx, ly = (long, short) if k % 2 == 0 else (short, long)   # alternating quoins
        return cx < o + q + lx and cy < o + q + ly
    bm = bmesh.new()
    info = voxel_mesh(bm, xs, ys, zs, solid)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.normal_update()
    ob.data.materials.clear()
    ob.data.materials.append(mats["stone"])
    ob.data.materials.append(mats["timber"])
    uvl = bm.loops.layers.uv.get("Float2") or bm.loops.layers.uv.new("Float2")
    for f in bm.faces:
        c = f.calc_center_median()
        if c.z > GIRT[0] + 1e-4:
            f.material_index = 1
            set_beam_uv(f, uvl, "H", TI, 0.12, GIRT[0])
        else:
            f.material_index = 0
            stone_uv(f, uvl)
    write_piece(ob, bm)
    bm.free()
    return check_piece(ob, snap_planes=[], flat_tri_ok=True)
