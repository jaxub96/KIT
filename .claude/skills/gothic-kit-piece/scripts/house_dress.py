# House dressing: small surface-mounted pieces that make a kit house read less
# plain (frame braces, eave brackets, glazed windows, window boxes, a gabled
# dormer, a porch). Needs kit_lib.py exec'd first (and roof_gable.py for the
# roof constants KNEE / TAN).
#
# Like the chimney and the fascia these are NOT welded to the walls / roof:
# they sit on or in front of them, so they can be added to any house. Trim
# pieces (brace, bracket, glazing, window box) use the WALL BAY's frame: put
# them at the same transform as the bay they dress (rebased bay: x 0..4 along
# the bay, inside face y = 0, outer plaster plane y = -0.4, z = storey floor).
# The dormer uses the roof run's frame, the porch the door bay's frame.
import bpy, bmesh, math, random
from mathutils import Vector

OUT = -0.4                       # outer plaster plane of a rebased bay
TI = (300 / 256, 300 / 512)      # timber texel density (kit standard)
WIN = (1.5, 2.5, 1.62, 2.70)     # the kit's window opening (both storeys)
GLASS_CROP = (0.22, 0.78, 0.56, 0.84)   # NW_Misc_Window_01: the black pane only


def _finish(ob, bm, kinds, mats, order, uv_fn, components_ok=False):
    """Material slots by kind, UVs, write, check."""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.normal_update()
    ob.data.materials.clear()
    slot = {}
    for k in order:
        ob.data.materials.append(mats[k])
        slot[k] = len(ob.data.materials) - 1
    uvl = bm.loops.layers.uv.get("Float2") or bm.loops.layers.uv.new("Float2")
    for f in bm.faces:
        k = kinds.get(f, order[0])
        f.material_index = slot[k]
        uv_fn(f, k, uvl)
    write_piece(ob, bm)
    bm.free()
    return check_piece(ob, snap_planes=[], flat_tri_ok=True)


def _box(bm, quad_front, quad_back, kinds, kind):
    """Closed hexahedron from two 4-vertex loops (same winding)."""
    F = [bm.verts.new(p) for p in quad_front]
    B = [bm.verts.new(p) for p in quad_back]
    fs = [bm.faces.new(F), bm.faces.new(B[::-1])]
    for i in range(4):
        j = (i + 1) % 4
        fs.append(bm.faces.new((F[j], F[i], B[i], B[j])))
    for f in fs:
        kinds[f] = kind
    return fs


def _beam_uv(f, uvl, along):
    """Beam grain along `along` (a unit Vector), measured on the face itself."""
    n = f.normal
    a = along - n * along.dot(n)
    if a.length < 1e-4:                       # end grain: plain wrap
        set_wrap_uv(f, uvl, TI, (0.25, 0.0))
        return
    a.normalize()
    c = n.cross(a).normalized()
    for l in f.loops:
        p = l.vert.co
        l[uvl].uv = (0.2 + p.dot(c) * TI[0], p.dot(a) * TI[1])


def beam(bm, kinds, p0, p1, w, d, normal_dir, kind="timber"):
    """Rectangular timber from p0 to p1 (centre line), width w across in the
    plane of `normal_dir`, depth d along normal_dir. Closed, 6 quads."""
    p0, p1 = Vector(p0), Vector(p1)
    ax = (p1 - p0).normalized()
    nd = Vector(normal_dir).normalized()
    side = ax.cross(nd).normalized() * (w / 2)
    dep = nd * d
    q0 = [p0 - side, p1 - side, p1 + side, p0 + side]
    return _box(bm, q0, [q + dep for q in q0], kinds, kind)


def slab_ring(xe, under, t, n_c, tip, rb=0.07, cap=0.07):
    """Section of a small gabled shingle slab (x across, centred on 0): the
    underside eave - apex - eave, then the top from the right eave up to a
    flat ridge board and down the left side, with n_c course steps per side.
    Returns (points, kinds per edge i -> i+1)."""
    ring = [(-xe, under(-xe)), (0.0, under(0.0)), (xe, under(xe))]
    kinds = ["timber", "timber", "timber"]                  # underside x2, right fascia
    right = []
    for c in range(n_c):
        xa = xe - (xe - rb) * c / n_c
        xb = xe - (xe - rb) * (c + 1) / n_c
        right += [(xa, under(xa) + t + tip), (xb, under(xb) + t)]
    zr = under(rb) + t + cap
    for k, p in enumerate(right):
        ring.append(p)
        kinds.append("roof")                                # course faces (the last one -> ridge board)
    kinds[-1] = "timber"                                    # course end -> up the ridge board side
    ring += [(rb, zr), (-rb, zr)]
    kinds += ["timber", "timber"]                           # board top, board left side
    left = [(-x, z) for (x, z) in right][::-1]              # ridge -> left eave
    for p in left:
        ring.append(p)
        kinds.append("roof")
    kinds[-1] = "timber"                                    # left fascia back to the underside
    return ring, kinds


# =========================================================================
# frame brace (upper bay, lower panel)
# =========================================================================
def build_brace(ob, mats, side="L", z0=0.15, z1=1.50, x_post=0.15, x_top=1.25, b=0.20,
                proud=0.08, seed=3):
    """Diagonal brace in an upper bay's lower panel, from the end post's foot
    (on the sole plate) up to the mid rail. side 'L' = at the bay's left post
    rising right, 'R' = mirror at the right post."""
    bm = bmesh.new()
    kinds = {}
    pts = [(x_post, z0), (x_post + b, z0), (x_top, z1), (x_top - b, z1)]
    if side == "R":
        pts = [(4.0 - x, z) for (x, z) in pts][::-1]
    front = [(x, OUT - proud, z) for (x, z) in pts]
    back = [(x, OUT + 0.01, z) for (x, z) in pts]          # 1 cm into the plaster: no gap
    fs = _box(bm, front, back, kinds, "timber")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    cap = [f for f in bm.faces if f.normal.y < -0.9]
    inset(bm, cap, 0.022, depth=0.018)                      # the kit's stepped chamfer
    rnd = random.Random(seed)
    for v in bm.verts:                                      # a touch of hand-cut wobble
        if v.co.y < OUT - 0.01:
            v.co.y += (rnd.random() * 2 - 1) * 0.006
    d = Vector((pts[2][0] - pts[1][0], 0, pts[2][1] - pts[1][1])).normalized()
    return _finish(ob, bm, kinds, mats, ("timber",), lambda f, k, uvl: _beam_uv(f, uvl, d))


# =========================================================================
# eave bracket (upper wall top, under the roof overhang)
# =========================================================================
def build_eave_bracket(ob, mats, w=0.12):
    """Timber bracket on the upper eave beam's front, carrying the roof's
    soffit near the eave. Centred on x = 0 (place at any x along a bay at the
    bay's transform, moved along x). Profile from the roof run (KNEE / TAN):
    the top follows the soffit."""
    soff = lambda y_leg: 3.0 + KNEE + TAN * y_leg           # roof underside over the wall top
    y_b, y_f = -0.16, -0.38                                 # eave beam front .. near the fascia
    prof = [(y_b, 2.72), (y_b, soff(y_b) - 0.005), (y_f, soff(y_f) - 0.005), (y_f, 3.16)]
    bm = bmesh.new()
    kinds = {}
    L = [(-w / 2, y + OUT, z) for (y, z) in prof]
    R = [(w / 2, y + OUT, z) for (y, z) in prof]
    _box(bm, L, R, kinds, "timber")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    under = [f for f in bm.faces if f.normal.z < -0.3 and f.normal.y < -0.3]
    inset(bm, under, 0.015, depth=0.012)
    d = Vector((0, y_f - y_b, 3.16 - 2.72)).normalized()
    return _finish(ob, bm, kinds, mats, ("timber",), lambda f, k, uvl: _beam_uv(f, uvl, d))


# =========================================================================
# glazed window (fills the kit window opening)
# =========================================================================
def build_window_glazing(ob, mats, cols=2, rows=2, bar=0.055, set_back=0.10, t=0.05):
    """Leaded window in the kit's 1.0 x 1.08 opening: a timber frame with
    mullion(s) / transom(s) around dark panes, recessed `set_back` behind the
    outer plaster plane. One closed grid slab, panes inset."""
    x0, x1, z0, z1 = WIN
    x0, x1, z0, z1 = x0 - 0.01, x1 + 0.01, z0 - 0.01, z1 + 0.01   # tucks into the jittered reveal
    xs = [x0, x0 + bar]
    for c in range(1, cols):
        xm = x0 + (x1 - x0) * c / cols
        xs += [xm - bar / 2, xm + bar / 2]
    xs += [x1 - bar, x1]
    zs = [z0, z0 + bar]
    for r in range(1, rows):
        zm = z0 + (z1 - z0) * r / rows
        zs += [zm - bar / 2, zm + bar / 2]
    zs += [z1 - bar, z1]
    yf, yb = OUT + set_back, OUT + set_back + t
    bm = bmesh.new()
    F = [[bm.verts.new((x, yf, z)) for z in zs] for x in xs]
    B = [[bm.verts.new((x, yb, z)) for z in zs] for x in xs]
    kinds, panes = {}, []
    nx, nz = len(xs) - 1, len(zs) - 1
    for i in range(nx):
        for k in range(nz):
            f = bm.faces.new((F[i][k], F[i + 1][k], F[i + 1][k + 1], F[i][k + 1]))
            pane = i % 2 == 1 and k % 2 == 1
            kinds[f] = "glass" if pane else "timber"
            if pane:
                panes.append(f)
            g = bm.faces.new((B[i][k + 1], B[i + 1][k + 1], B[i + 1][k], B[i][k]))
            kinds[g] = "glass" if pane else "timber"
    for i in range(nx):                                     # perimeter
        for k in (0, nz):
            q = (F[i][k], F[i + 1][k], B[i + 1][k], B[i][k]) if k == 0 else (F[i + 1][k], F[i][k], B[i][k], B[i + 1][k])
            kinds[bm.faces.new(q)] = "timber"
    for k in range(nz):
        for i in (0, nx):
            q = (F[i][k + 1], F[i][k], B[i][k], B[i][k + 1]) if i == 0 else (F[i][k], F[i][k + 1], B[i][k + 1], B[i][k])
            kinds[bm.faces.new(q)] = "timber"
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    res = bmesh.ops.inset_individual(bm, faces=panes, thickness=0.0, depth=-0.02)
    for f in res["faces"]:
        kinds[f] = "timber"                                 # the rebate around each pane
    for f in panes:
        kinds[f] = "glass"

    def uv(f, k, uvl):
        if k == "glass":
            set_window_uv(f, uvl, (0.5, 0.5), GLASS_CROP)
        else:
            n = f.normal
            _beam_uv(f, uvl, Vector((0, 0, 1)) if abs(n.z) < 0.5 else Vector((1, 0, 0)))
    return _finish(ob, bm, kinds, mats, ("timber", "glass"), uv)


# =========================================================================
# window box
# =========================================================================
def build_window_box(ob, mats, seed=11, nx=8, ny=3):
    """Planted window box hanging under the kit window's sill (sill front at
    y = -0.6). One closed grid box: plank sides and bottom, a lumpy planted top."""
    xa, xb = 1.42, 2.58
    ya, yb = -0.62, -0.86
    zb, zt = 1.30, 1.55
    xs = [xa + (xb - xa) * i / nx for i in range(nx + 1)]
    ys = [ya + (yb - ya) * j / ny for j in range(ny + 1)]
    rnd = random.Random(seed)
    bm = bmesh.new()
    T, Bt = {}, {}
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            edge = i in (0, nx) or j in (0, ny)
            h = zt if edge else zt + 0.05 + rnd.random() * 0.11         # foliage mounds
            T[i, j] = bm.verts.new((x, y, h))
            Bt[i, j] = bm.verts.new((x, y, zb))
    kinds = {}
    for i in range(nx):
        for j in range(ny):
            kinds[bm.faces.new((T[i, j], T[i + 1, j], T[i + 1, j + 1], T[i, j + 1]))] = "plants"
            kinds[bm.faces.new((Bt[i, j + 1], Bt[i + 1, j + 1], Bt[i + 1, j], Bt[i, j]))] = "planks"
    for i in range(nx):
        for j in (0, ny):
            kinds[bm.faces.new((T[i, j], Bt[i, j], Bt[i + 1, j], T[i + 1, j]))] = "planks"
    for j in range(ny):
        for i in (0, nx):
            kinds[bm.faces.new((T[i, j], T[i, j + 1], Bt[i, j + 1], Bt[i, j]))] = "planks"
    # a slight lean outward and jitter on the planks
    for v in bm.verts:
        if v.co.z <= zt + 1e-6:
            v.co.y -= 0.01 * (v.co.z - zb) / (zt - zb)

    def uv(f, k, uvl):
        if k == "plants":
            set_window_uv(f, uvl, (0.30, 0.30), (0.725, 0.905, 0.50, 0.87))   # inside the leafy disk
        else:
            _beam_uv(f, uvl, Vector((1, 0, 0)))
    return _finish(ob, bm, kinds, mats, ("planks", "plants"), uv)


# =========================================================================
# gabled dormer (sits on a 38 deg roof run)
# =========================================================================
def build_dormer_gable(ob, mats, y0=0.30, y1=2.30, hw=0.80, base=0.95, E=2.35, pitch=45.0,
                       over=0.16, seed=21):
    """Gabled dormer in the ROOF RUN's legacy frame (x along the ridge, centred
    on x = 0; y from the outer wall face up the slope; z from the wall top).
    The box (front wall with a glazed window, cheeks) is buried in the run
    below the roof surface; its gable roof runs back until it dies into the
    slope. Works on any run with the kit pitch (the slope near the eave is the
    same for every width). Two closed parts: box and roof."""
    tp = math.tan(math.radians(pitch))
    top = lambda x: E + 0.08 + (hw - abs(x)) * tp           # roof underside / gable top
    xs = [-hw, -0.65, -0.30, -0.03, 0.03, 0.30, 0.65, hw]
    zs = [base, 1.30, 1.40, 1.72, 1.78, 2.10, 2.20, E, None]   # None = gable top row
    zat = lambda x, k: top(x) if zs[k] is None else zs[k]
    bm = bmesh.new()
    F = [[bm.verts.new((x, y0, zat(x, k))) for k in range(len(zs))] for x in xs]
    B = [[bm.verts.new((x, y1, zat(x, k) - (0.01 if zs[k] is None else 0))) for k in range(len(zs))] for x in xs]
    kinds, front = {}, {}
    nx, nz = len(xs) - 1, len(zs) - 1

    def region(cx, cz, k):
        if k == nz - 1:
            return "plaster"                                # gable
        if abs(cx) > 0.65 or 1.30 < cz < 1.40 or 2.20 < cz < E:
            return "timber"
        if abs(cx) < 0.30 and 1.40 < cz < 2.10:
            return "bar" if (abs(cx) < 0.03 or 1.72 < cz < 1.78) else "glass"
        return "plaster"
    for i in range(nx):
        for k in range(nz):
            f = bm.faces.new((F[i][k], F[i + 1][k], F[i + 1][k + 1], F[i][k + 1]))
            cx = (xs[i] + xs[i + 1]) / 2
            cz = (zat(xs[i], k) + zat(xs[i], k + 1)) / 2
            front[f] = region(cx, cz, k)
            kinds[bm.faces.new((B[i][k + 1], B[i + 1][k + 1], B[i + 1][k], B[i][k]))] = "plaster"
    for k in range(nz):                                     # cheeks
        kinds[bm.faces.new((F[0][k + 1], F[0][k], B[0][k], B[0][k + 1]))] = "plaster"
        kinds[bm.faces.new((F[nx][k], F[nx][k + 1], B[nx][k + 1], B[nx][k]))] = "plaster"
    for i in range(nx):                                     # bottom and top
        kinds[bm.faces.new((F[i + 1][0], F[i][0], B[i][0], B[i + 1][0]))] = "plaster"
        kinds[bm.faces.new((F[i][nz], F[i + 1][nz], B[i + 1][nz], B[i][nz]))] = "plaster"
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    kinds.update(front)
    timber = [f for f, r in front.items() if r == "timber"]
    caps, _ = extrude_faces(bm, timber, 0.05, with_sides=True)
    for f in bm.faces:
        if f not in kinds:
            kinds[f] = "timber"
    inset(bm, caps, 0.02, depth=0.015)
    for f in bm.faces:
        kinds.setdefault(f, "timber")
    win = [f for f, r in front.items() if r in ("glass", "bar")]
    wcaps, _ = extrude_faces(bm, win, -0.10, with_sides=True)
    for f in bm.faces:
        kinds.setdefault(f, "timber")
    bars = []
    for f in wcaps:
        c = f.calc_center_median()
        r = "bar" if (abs(c.x) < 0.03 or 1.72 < c.z < 1.78) else "glass"
        kinds[f] = "glass" if r == "glass" else "timber"
        if r == "bar":
            bars.append(f)
    bcaps, _ = extrude_faces(bm, bars, 0.05, with_sides=True)
    for f in bm.faces:
        kinds.setdefault(f, "timber")
    for f in bcaps:
        kinds[f] = "timber"

    # ---- the gable roof: a thin slab with shingle courses, swept along y -------
    t, n_c, tip = 0.14, 3, 0.035
    xe = hw + over
    ring, rk = slab_ring(xe, top, t, n_c, tip)
    ry0 = y0 - 0.22
    ry1 = (top(0.0) + t + 0.07 - (KNEE + 0.22)) / TAN + 0.25   # dies into the run's slope
    R0 = [bm.verts.new((x, ry0, z)) for (x, z) in ring]
    R1 = [bm.verts.new((x, ry1, z)) for (x, z) in ring]
    n = len(ring)
    for i in range(n):
        j = (i + 1) % n
        kinds[bm.faces.new((R0[i], R0[j], R1[j], R1[i]))] = rk[i]
    for R, rev in ((R0, True), (R1, False)):
        cap = bm.faces.new(R[::-1] if rev else R)
        kinds[cap] = "timber"
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    big = [f for f in bm.faces if len(f.verts) > 4]
    tagged = {f: kinds[f] for f in big}
    tri = bmesh.ops.triangulate(bm, faces=big, quad_method='BEAUTY', ngon_method='BEAUTY')
    new = tri["faces"]
    for f in new:
        kinds[f] = "timber"
    bmesh.ops.join_triangles(bm, faces=new, cmp_seam=False, cmp_sharp=False, cmp_uvs=False, cmp_vcols=False,
                             cmp_materials=False, angle_face_threshold=math.radians(2.0),
                             angle_shape_threshold=math.radians(180.0))
    for f in bm.faces:
        kinds.setdefault(f, "timber")
    rnd = random.Random(seed)
    for v in bm.verts:                                      # hand-made wobble on the roof
        if v.co.y < ry1 - 0.01 and v.co.z > E + 0.2:
            v.co.z += (rnd.random() * 2 - 1) * 0.008
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    topf = max(bm.faces, key=lambda f: f.calc_center_median().z)
    if topf.normal.z < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    slope = math.sqrt(1 + tp * tp)

    def uv(f, k, uvl):
        if k == "roof":
            for l in f.loops:
                c = l.vert.co
                l[uvl].uv = (c.y * 0.5, (xe - abs(c.x)) * slope / (xe * slope / n_c) * 0.25)
        elif k == "glass":
            set_window_uv(f, uvl, (0.5, 0.5), GLASS_CROP)
        elif k == "plaster":
            set_window_uv(f, uvl, (1.5, 1.0), (0.12, 0.88, 0.43, 0.90))
        else:
            n = f.normal
            _beam_uv(f, uvl, Vector((0, 0, 1)) if abs(n.z) < 0.5 and abs(f.calc_center_median().x) > 0.6
                     else Vector((1, 0, 0)) if abs(n.y) > 0.5 else Vector((0, 1, 0)))
    return _finish(ob, bm, kinds, mats, ("plaster", "timber", "roof", "glass"), uv)


# =========================================================================
# porch: stone steps + timber canopy (door bay frame)
# =========================================================================
PORCH_X = (0.75, 3.25)            # along the door bay (door 1.4..2.6)


def build_porch_steps(ob, mats, x=PORCH_X, top=0.46, depth=1.20, n=3, going=0.30, seed=5, back=OUT):
    """Stone landing level with the door threshold (FOOT 0.46) and n-1 steps
    down to the ground, in front of a door bay. Closed, all quads: the two
    sides are a grid of step columns x step rows."""
    xa, xb = x
    ys = [back] + [OUT - depth - k * going for k in range(n)]  # column j spans ys[j]..ys[j+1]; back = the wall face
    zs = [top * k / n for k in range(n + 1)]
    kmax = lambda j: n - j if j < n else 0                      # rows column j reaches
    bm = bmesh.new()
    kinds = {}
    G = {(s, j, k): bm.verts.new((xx, ys[j], zs[k]))
         for s, xx in (("a", xa), ("b", xb)) for j in range(n + 1) for k in range(n + 1)}

    def quad(p, q, r, t, kind="stone"):
        kinds[bm.faces.new((G[p], G[q], G[r], G[t]))] = kind
    for j in range(n):
        for k in range(kmax(j)):
            quad(("a", j, k), ("a", j, k + 1), ("a", j + 1, k + 1), ("a", j + 1, k))      # sides
            quad(("b", j + 1, k), ("b", j + 1, k + 1), ("b", j, k + 1), ("b", j, k))
        km = kmax(j)
        quad(("a", j, km), ("b", j, km), ("b", j + 1, km), ("a", j + 1, km))           # tread
        quad(("a", j, 0), ("a", j + 1, 0), ("b", j + 1, 0), ("b", j, 0))               # bottom
        for k in range(kmax(j + 1), km):                                               # riser at its front
            quad(("a", j + 1, k), ("a", j + 1, k + 1), ("b", j + 1, k + 1), ("b", j + 1, k))
    for k in range(n):                                                                  # back, at the wall
        quad(("a", 0, k + 1), ("a", 0, k), ("b", 0, k), ("b", 0, k + 1))
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    rnd = random.Random(seed)
    for v in bm.verts:                                          # worn, hand-set stones
        if v.co.z > 0.01 and abs(v.co.y - back) > 1e-4:
            v.co.z += (rnd.random() * 2 - 1) * 0.008
            v.co.y += (rnd.random() * 2 - 1) * 0.01

    def uv(f, k, uvl):
        set_wrap_uv(f, uvl, (0.566, 0.566), (0.0, 0.10))
    return _finish(ob, bm, kinds, mats, ("stone",), uv)


def build_porch_canopy(ob, mats, x=PORCH_X, post_y=-1.45, floor=0.46, plate=2.95, pitch=40.0,
                       front=-1.85, seed=7, knee_braces=True):
    """Timber porch canopy in front of a door bay: two posts on the landing, a
    tie beam and two side plates back to the wall, knee braces, a king post,
    and a small gabled shingle roof that dies into the wall. Several closed
    timber members that touch (a freestanding assembly, like a fence)."""
    xa, xb = x
    xc = (xa + xb) / 2
    px = (xa + 0.20, xb - 0.20)
    tp = math.tan(math.radians(pitch))
    bm = bmesh.new()
    kinds = {}
    pw = 0.20
    zt = plate + 0.20

    def box(x0, x1, y0, y1, z0, z1, kind="timber"):
        q = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)]
        return _box(bm, q, [(a, b, z1) for (a, b, _) in q], kinds, kind)
    h = pw / 2
    for X in px:
        box(X - h, X + h, post_y - h, post_y + h, floor, plate)                   # posts
        box(X - 0.15, X + 0.15, post_y - 0.15, post_y + 0.15, floor, floor + 0.12, "stone")  # post bases
        box(X - h, X + h, post_y + h - 0.001, OUT, plate, zt)                      # side plates to the wall
    box(xa, xb, post_y - h, post_y + h, plate, zt)                                 # tie beam
    # knee braces (post -> tie beam, post -> side plate)
    for X, s in (((px[0], 1), (px[1], -1)) if knee_braces else ()):
        beam(bm, kinds, (X + s * 0.08, post_y - 0.05, plate - 0.55), (X + s * 0.55, post_y - 0.05, plate + 0.02),
             0.12, 0.10, (0, 1, 0))
        beam(bm, kinds, (X - 0.05, post_y + 0.08, plate - 0.55), (X - 0.05, post_y + 0.55, plate + 0.02),
             0.12, 0.10, (1, 0, 0))
    # roof: gabled slab over xa-0.2 .. xb+0.2, ridge at xc, from the wall to `front`
    xe = (xb - xa) / 2 + 0.22
    under = lambda dx: zt + ((xb - xa) / 2 - abs(dx)) * tp
    t, n_c, tip = 0.14, 4, 0.04
    ring, rk = slab_ring(xe, under, t, n_c, tip)
    ring = [(xc + x_, z) for (x_, z) in ring]
    R0 = [bm.verts.new((x_, front, z)) for (x_, z) in ring]
    R1 = [bm.verts.new((x_, OUT + 0.05, z)) for (x_, z) in ring]
    n = len(ring)
    for i in range(n):
        j = (i + 1) % n
        kinds[bm.faces.new((R0[i], R1[i], R1[j], R0[j]))] = rk[i]
    c0 = bm.faces.new(R0)
    c1 = bm.faces.new(R1[::-1])
    kinds[c0] = kinds[c1] = "timber"
    # king post in the front gable
    box(xc - 0.07, xc + 0.07, post_y - 0.07, post_y + 0.07, zt, under(0) - 0.01)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    big = [f for f in bm.faces if len(f.verts) > 4]
    tri = bmesh.ops.triangulate(bm, faces=big, quad_method='BEAUTY', ngon_method='BEAUTY')
    for f in tri["faces"]:
        kinds[f] = "timber"
    bmesh.ops.join_triangles(bm, faces=tri["faces"], cmp_seam=False, cmp_sharp=False, cmp_uvs=False,
                             cmp_vcols=False, cmp_materials=False, angle_face_threshold=math.radians(2.0),
                             angle_shape_threshold=math.radians(180.0))
    for f in bm.faces:
        kinds.setdefault(f, "timber")
    rnd = random.Random(seed)
    for v in bm.verts:
        if v.co.z > zt + 0.1:
            v.co.z += (rnd.random() * 2 - 1) * 0.006
    slope = math.sqrt(1 + tp * tp)

    def uv(f, k, uvl):
        if k == "roof":
            for l in f.loops:
                c = l.vert.co
                l[uvl].uv = (c.y * 0.5, (xe - abs(c.x - xc)) * slope / (xe * slope / n_c) * 0.25)
        elif k == "stone":
            set_wrap_uv(f, uvl, (0.566, 0.566), (0.0, 0.10))
        else:
            e = max(f.edges, key=lambda e: e.calc_length())
            d = (e.verts[1].co - e.verts[0].co).normalized()
            _beam_uv(f, uvl, d)
    return _finish(ob, bm, kinds, mats, ("timber", "roof", "stone"), uv)
