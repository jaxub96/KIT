# Corner post, gable end wall and roof run: the pieces that turn wall bays into
# a building. Needs kit_lib.py exec'd first (and wall_bay.py for choose_bounds).
#
# Assembly contract (see documentation/KIT_USER_GUIDE.md "Building a house"):
#   ground floor top = z 3.0.   KNEE = 0.6 m of wall above that (in the roof run's
#   skirts and in the gable); roof pitch 38 deg; building depth 4 m.
import bpy, bmesh, math
from mathutils import Vector

PITCH = math.radians(38.0)
TAN, COS, SIN = math.tan(PITCH), math.cos(PITCH), math.sin(PITCH)
KNEE = 0.60
APEX = KNEE + 2.0 * TAN            # underside height at the ridge, 2.16 m
COURSE_DY = 0.50                               # y spacing of shingle courses (slope length = COURSE_DY / COS)
GABLE_RAF = 0.28                               # rafter row height


def roof_slope_uv(y, z, W=4.8, N=5, OVER=0.40):
    """Even shingle UV: v = distance along the slope from the eave line, scaled so
    one course (COURSE_DY in y) is 0.25 = 4 rows of the 512 px roof tile. Works for
    every point of the roof profile (ramps, steps, ridge) and both slopes, and is
    shared by the run and the end piece so the mapping is continuous across the weld."""
    yy = y if y <= W / 2 else W - y
    zu = lambda t: KNEE + TAN * t
    b0y, b0z = -OVER, zu(-OVER) + 0.22
    s = COURSE_DY / COS
    return ((yy - b0y) * COS + (z - b0z) * SIN) / s * 0.25


def _mk(ob, bm, kinds, mats, order, uv_fn):
    """Assign material slots by kind, run uv_fn(face, kind, uvl), write mesh."""
    ob.data.materials.clear()
    slot = {}
    for k in order:
        ob.data.materials.append(mats[k])
        slot[k] = len(ob.data.materials) - 1
    uvl = bm.loops.layers.uv.get("Float2") or bm.loops.layers.uv.new("Float2")
    for f in bm.faces:
        k = kinds.get(f, "timber")
        f.material_index = slot[k]
        uv_fn(f, k, uvl)
    write_piece(ob, bm)


# =========================================================================
# corner post
# =========================================================================
def build_corner_post(ob, mats, zen_coll=None, seed=5):
    """Free-standing 0.5 m timber post with stone plinth and eave cap. Sits on
    the outer corner where two wall bays overlap; origin = the outer corner of
    the two wall slabs (post centre at 0.2, 0.2)."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    if zen_coll is not None:
        for o in [o for o in bpy.data.objects if o.name == ob.name + "_ZEN"]:
            bpy.data.meshes.remove(o.data)
    cx = cy = 0.20
    # (z, half-width, kind of the vertical band ABOVE this ring)
    rings = [(0.00, 0.30, "stone"), (0.46, 0.30, None), (0.46, 0.22, "timber"),
             (0.50, 0.22, None), (0.50, 0.25, "timber"), (2.70, 0.25, None),
             (2.70, 0.31, "timber"), (3.00, 0.31, None), (3.00, 0.24, None)]
    bm = bmesh.new()
    R = []
    for (z, hw, _) in rings:
        R.append([bm.verts.new((cx - hw, cy - hw, z)), bm.verts.new((cx + hw, cy - hw, z)),
                  bm.verts.new((cx + hw, cy + hw, z)), bm.verts.new((cx - hw, cy + hw, z))])
    kinds = {}
    for i in range(len(rings) - 1):
        a, b = R[i], R[i + 1]
        z0, z1 = rings[i][0], rings[i + 1][0]
        k = "stone" if max(z0, z1) <= 0.50 + 1e-6 and min(z0, z1) < 0.50 else "timber"
        if z0 >= 0.5 - 1e-6:
            k = "timber"
        for j in range(4):
            f = bm.faces.new((a[j], a[(j + 1) % 4], b[(j + 1) % 4], b[j]))
            kinds[f] = k
    bot = bm.faces.new(R[0][::-1]); kinds[bot] = "stone"
    top = bm.faces.new(R[-1]); kinds[top] = "timber"
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.verts.ensure_lookup_table()
    tv = [v for v in bm.verts if 0.5 < v.co.z < 2.75]
    jitter(bm, tv, (0.008, 0.008, 0.0), seed=seed)
    jitter(bm, [v for v in bm.verts if v.co.z <= 0.5 and v.co.z > 0.01], (0.02, 0.02, 0.0), seed=seed + 1)
    for v in tv:                               # a slight lean/bow
        v.co.x += 0.010 * math.sin(math.pi * (v.co.z - 0.5) / 2.2)
    bm.normal_update()
    TI = (300 / 256, 300 / 512)

    def uv(f, k, uvl):
        if k == "stone":
            set_wrap_uv(f, uvl, (0.566, 0.566), (0.0, 0.10))
        else:
            set_beam_uv(f, uvl, "V", TI, 0.30, cx - 0.25)
    _mk(ob, bm, kinds, mats, ("timber", "stone"), uv)
    bm.free()
    res = check_piece(ob, snap_planes=[], flat_tri_ok=True)
    if zen_coll is not None:
        make_export_copy(ob, zen_coll)
    return res


# =========================================================================
# gable end wall
# =========================================================================
def build_gable(ob, mats, zen_coll=None, seed=7):
    """4 m wide gable wall that fits BETWEEN the two corner blocks (building
    depth 4.8 m, roof underside plane), 0.91 m at its ends, apex 2.475 m; timber
    frame with king post and barge boards along the slopes. Quads only
    (two-trapezoid back face). Origin = bottom-left front corner."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    if zen_coll is not None:
        for o in [o for o in bpy.data.objects if o.name == ob.name + "_ZEN"]:
            bpy.data.meshes.remove(o.data)

    def top(x):
        return KNEE + TAN * (0.4 + min(x, 4.0 - x))          # follows the roof underside (gable spans y .4..4.4)
    RAF = 0.28
    X = [0.0, 0.15, 1.92, 2.08, 3.85, 4.0]
    T = WALL_T
    bm = bmesh.new()
    rows = lambda x: [0.0, top(x) - RAF, top(x)]
    F = [[bm.verts.new((x, 0.0, z)) for z in rows(x)] for x in X]
    B = {(x, z): bm.verts.new((x, T, z)) for x in (0.0, 2.0, 4.0) for z in (0.0, top(x))}
    fronts, backs, plast = [], [], set()
    for i in range(len(X) - 1):
        for j in range(2):
            f = bm.faces.new((F[i][j], F[i + 1][j], F[i + 1][j + 1], F[i][j + 1]))
            fronts.append(f)
    for xa, xb in ((0.0, 2.0), (2.0, 4.0)):
        f = bm.faces.new((B[(xa, 0.0)], B[(xa, top(xa))], B[(xb, top(xb))], B[(xb, 0.0)]))
        backs.append(f)
    # bridge front and back outlines (flat planes: quads where aligned, tris else)
    def chain_front(sel):
        return [F[i][sel] for i in range(len(X))]
    bridge = []
    bridge += _stitch(bm, chain_front(0), [B[(0.0, 0.0)], B[(2.0, 0.0)], B[(4.0, 0.0)]], 0)            # bottom
    bridge += _stitch(bm, chain_front(2), [B[(0.0, top(0.0))], B[(2.0, top(2.0))], B[(4.0, top(4.0))]], 0)  # top
    bridge += _stitch(bm, [F[0][0], F[0][1], F[0][2]], [B[(0.0, 0.0)], B[(0.0, top(0.0))]], 2)        # left
    bridge += _stitch(bm, [F[-1][0], F[-1][1], F[-1][2]], [B[(4.0, 0.0)], B[(4.0, top(4.0))]], 2)     # right
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    plast = set(backs) | set(bridge)

    def tag(x, z):
        if z > top(x) - RAF:
            return "rafter"
        if x < 0.15 or x > 3.85 or 1.92 < x < 2.08:
            return "timber"
        return None
    raised = [f for f in fronts if tag(f.calc_center_median().x, f.calc_center_median().z)]
    caps, _ = extrude_faces(bm, raised, 0.09, with_sides=True)
    ctag = {f: tag(f.calc_center_median().x, f.calc_center_median().z) for f in caps}
    capset = set(caps)
    for v in {v for f in caps for v in f.verts}:
        v.co.y = -max(0.15 if ctag[f] == "rafter" else 0.09 for f in v.link_faces if f in capset)
    inset(bm, caps, 0.028, depth=0.03)
    kinds = {}
    for f in bm.faces:
        kinds[f] = "plaster" if (f in plast or f in fronts) else "timber"
    bm.verts.ensure_lookup_table()
    rv = [v for v in bm.verts if v.co.y < -0.005]
    jitter(bm, rv, (0.008, 0.012, 0.008), seed=seed, keep_planes=[(2, 0.0)], period_x=4.0)
    for v in rv:                                # the rafters sag a touch
        if v.co.z > top(v.co.x) - 0.35:
            v.co.z -= 0.02 * math.sin(math.pi * v.co.x / 4.0)
    bm.normal_update()
    TI = (300 / 256, 300 / 512)

    def uv(f, k, uvl):
        c = f.calc_center_median()
        if k == "plaster":
            set_window_uv(f, uvl, (2.0, 1.7), (0.12, 0.88, 0.43, 0.90), bounds={0: [0, 2, 4]})
            return
        if c.z > top(c.x) - RAF - 0.02 and c.z > 0.5:       # rafter: grain along the slope
            sgn = 1 if c.x < 2.0 else -1
            d = Vector((COS * sgn, SIN))
            nrm = Vector((-SIN * sgn, COS))
            for loop in f.loops:
                p = loop.vert.co
                loop[uvl].uv = (0.2 + (p.x * nrm.x + p.z * nrm.y) * TI[0], (p.x * d.x + p.z * d.y) * TI[1])
        else:
            set_beam_uv(f, uvl, "V", TI, 0.14 + 0.2 * (c.x > 2), 0.0)
    _mk(ob, bm, kinds, mats, ("plaster", "timber"), uv)
    bm.free()
    res = check_piece(ob, snap_planes=[], flat_tri_ok=True)
    if zen_coll is not None:
        make_export_copy(ob, zen_coll)
    return res


# =========================================================================
# roof run
# =========================================================================
def build_roof_run(ob, mats, zen_coll=None, seed=9, courses=5, W=4.8):
    """4 m roof section spanning the 4 m building depth: knee-wall skirts, sloped
    soffit and fascia, stepped shingle courses, ridge cap. Open at x=0 and x=4.
    Origin: x at the left end, y at the front wall's outer face, z at the wall top."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    if zen_coll is not None:
        for o in [o for o in bpy.data.objects if o.name == ob.name + "_ZEN"]:
            bpy.data.meshes.remove(o.data)
    zu = lambda y: KNEE + TAN * (y if y <= W / 2 else W - y)      # underside height
    FASCIA, H, N = 0.22, 0.06, courses
    OVER = 0.40
    # ---- left half of the outer profile: points (y, z, v) + kind of edge to next ---
    # Course boundaries are spaced COURSE_DY apart in y and START at y=-OVER, so the
    # top chain (course tips/ends) and the underside stations share y positions and
    # the closed end cap bridges 1:1 (quads) instead of fans.
    yo = -OVER
    zt = lambda y: zu(y) + FASCIA
    pts = [(0.0, 0.0, None), (0.0, KNEE, None), (yo, zu(yo), None)]
    ek = ["plaster", "timber", "timber"]                    # skirt front, soffit, fascia
    ys = [yo + k * COURSE_DY for k in range(N + 1)]
    for k in range(N):
        pts.append((ys[k], zt(ys[k]) + H, None))            # course tip (thick edge)
        ek.append("roof")
        pts.append((ys[k + 1], zt(ys[k + 1]), None))        # tucks under the next course
        ek.append("roof")
    pts.append((ys[N], zt(ys[N]) + 0.12, None))             # ridge board step up
    ek[-1] = "timber"                                       # last course end -> ridge board
    mir = lambda p: (W - p[0], p[1], p[2])
    ring, kinds_e = list(pts), list(ek)
    kinds_e.append("timber")                                 # flat ridge top
    for j in range(len(pts) - 1, 0, -1):
        ring.append(mir(pts[j]))
        kinds_e.append(ek[j - 1])
    ring.append(mir(pts[0]))                                 # (W, 0)
    kinds_e.append("plaster")                                # bottom strip: (W,0) -> inner's (W-0.4,0), a
    # flat z=0 soffit strip WALL_T (0.4 m) wide -- the same width, same z, as
    # the wall bay's own flat top cap, so the two now share that whole strip
    # instead of touching along one edge: the wall-to-roof seam actually
    # welds there now, not just touches. (Used to detour through an extra
    # vertex at W-0.1/0.1 with nothing on the wall side to weld it to,
    # leaving those two short spans permanently open.)
    # notch = the attic cavity outline. Its stations are the course y's, so the end piece's
    # gable columns line up with the run's underside vertices and weld exactly.
    left = [0.4] + [y for y in ys if y > 0.4 + 1e-6]
    st = sorted({round(y, 4) for y in left} | {round(W / 2, 4)} | {round(W - y, 4) for y in left})
    inner = [((W - 0.4, 0.0, None), "plaster"),
             ((W - 0.4, zu(W - 0.4) - GABLE_RAF, None), "plaster"),
             ((W - 0.4, zu(W - 0.4), None), "timber")]
    for y in reversed(st[1:-1]):
        inner.append(((y, zu(y), None), "timber"))
    inner += [((0.4, zu(0.4), None), "plaster"), ((0.4, zu(0.4) - GABLE_RAF, None), "plaster"),
              ((0.4, 0.0, None), "plaster")]                  # -> wraps to ring[0] = (0.0, 0.0): the south strip
    for (p, k) in inner:
        ring.append(p)
        kinds_e.append(k)
    kind_edge = kinds_e
    n = len(ring)
    xs_st = (0.0, 2.0, 4.0)
    bm = bmesh.new()
    V = [[bm.verts.new((x, p[0], p[1])) for x in xs_st] for p in ring]
    kinds, vmap = {}, {}
    for i, p in enumerate(ring):
        for j in range(3):
            vmap[V[i][j]] = p[2]
    fl = []
    for i in range(n):
        a, b = i, (i + 1) % n
        k = kind_edge[i] if i < len(kind_edge) else "timber"
        for j in range(2):
            f = bm.faces.new((V[a][j], V[a][j + 1], V[b][j + 1], V[b][j]))
            kinds[f] = k
            fl.append(f)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.verts.ensure_lookup_table()
    # irregularity: courses wander, roof sags, ends stay put so runs mate
    # mirror-symmetric irregularity: the run must be identical under a 180 deg
    # turn about z so the SAME end piece fits both ends of a building
    import random
    for v in bm.verts:
        if v.co.z <= 0.2 or abs(v.co.x) < 1e-4 or abs(v.co.x - 4.0) < 1e-4:
            continue
        ym = min(v.co.y, W - v.co.y)
        rnd = random.Random(hash((round(v.co.x % 4.0, 3), round(v.co.z, 3), round(ym, 3), seed)))
        sgn = 0.0 if abs(v.co.y - W / 2) < 1e-4 else (1.0 if v.co.y < W / 2 else -1.0)
        v.co.y += (rnd.random() * 2 - 1) * 0.012 * sgn
        v.co.z += (rnd.random() * 2 - 1) * 0.014
    for v in bm.verts:
        if v.co.z > 0.5:
            v.co.z -= 0.025 * math.sin(math.pi * v.co.x / 4.0)
    bm.normal_update()
    TI = (300 / 256, 300 / 512)

    def uv(f, k, uvl):
        if k == "roof":
            for loop in f.loops:
                c = loop.vert.co
                loop[uvl].uv = (c.x * 0.5, roof_slope_uv(c.y, c.z, W=W, N=N))
        elif k == "plaster":
            set_window_uv(f, uvl, (1.5, 1.0), (0.12, 0.88, 0.43, 0.90), bounds={0: [0, 2, 4]})
        else:
            set_beam_uv(f, uvl, "H", TI, 0.25, 0.0)
    _mk(ob, bm, kinds, mats, ("roof", "timber", "plaster"), uv)
    bm.free()
    res = check_piece(ob, snap_planes=[(0, 0.0), (0, 4.0)], flat_tri_ok=True)
    if zen_coll is not None:
        make_export_copy(ob, zen_coll)
    return res


# =========================================================================
# chimney
# =========================================================================
def build_chimney(ob, mats, zen_coll=None, seed=13):
    """Stone chimney stack that sits on the roof ridge (origin = ridge top line,
    centre of the stack; x along the ridge, y across). Saddle base follows the
    38 deg roof, courses step in/out, corbelled cap, recessed flue. Solid,
    quads only, closed."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    if zen_coll is not None:
        for o in [o for o in bpy.data.objects if o.name == ob.name + "_ZEN"]:
            bpy.data.meshes.remove(o.data)
    # (z, half width); z=None on the first ring = saddle (follows the roof)
    levels = [(None, 0.46), (0.50, 0.46), (0.50, 0.42), (1.60, 0.42), (1.60, 0.50),
              (1.75, 0.50), (1.75, 0.44), (1.95, 0.44), (1.95, 0.30), (1.80, 0.30)]
    bm = bmesh.new()

    def ring(z, hw):
        pts = [(-hw, -hw), (hw, -hw), (hw, 0.0), (hw, hw), (-hw, hw), (-hw, 0.0)]
        out = []
        for (x, y) in pts:
            zz = (-TAN * abs(y) - 0.10) if z is None else z
            out.append(bm.verts.new((x, y, zz)))
        return out
    R = [ring(z, hw) for (z, hw) in levels]
    n = 6
    for i in range(len(levels) - 1):
        for j in range(n):
            bm.faces.new((R[i][j], R[i][(j + 1) % n], R[i + 1][(j + 1) % n], R[i + 1][j]))
    # flue floor and saddle bottom: two quads each (split along y = 0)
    top = R[-1]
    bm.faces.new((top[0], top[1], top[2], top[5]))
    bm.faces.new((top[5], top[2], top[3], top[4]))
    bot = R[0]
    bm.faces.new((bot[5], bot[2], bot[1], bot[0]))
    bm.faces.new((bot[4], bot[3], bot[2], bot[5]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.verts.ensure_lookup_table()
    jitter(bm, [v for v in bm.verts if v.co.z > 0.05], (0.02, 0.02, 0.0), seed=seed)
    for v in bm.verts:                                   # a slight lean of the shaft
        if v.co.z > 0.5:
            v.co.x += 0.012 * (v.co.z - 0.5)
    bm.normal_update()
    ob.data.materials.clear()
    ob.data.materials.append(mats["stone"])
    uvl = bm.loops.layers.uv.get("Float2") or bm.loops.layers.uv.new("Float2")
    for f in bm.faces:
        f.material_index = 0
        set_wrap_uv(f, uvl, (0.566, 0.566), (0.0, 0.10))
    write_piece(ob, bm)
    bm.free()
    res = check_piece(ob, snap_planes=[], flat_tri_ok=True)
    if zen_coll is not None:
        make_export_copy(ob, zen_coll)
    return res
