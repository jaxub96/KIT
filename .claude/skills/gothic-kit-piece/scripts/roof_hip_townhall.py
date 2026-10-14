# Townhall roof: turn the main roof's north end into a HIP at the kit pitch (38 deg).
# Needs kit_lib.py and roof_gable.py exec'd first (KNEE, TAN, roof_slope_uv, _stitch, ...).
#
# The townhall roof (KIT_ROOF_T_A in the scene) is the kit T roof widened: an 8.8 m
# main roof (ridge along y at x = -1, outer wall faces x = -5.4 / 3.4) and the 4.8 m
# wing (ridge along x at y = 0, to x = 7). Every roof point's height depends only on
# its distance d from its own eave line, so a hip is the same mitre trick as the
# kit's valleys: a main-roof profile point at distance d from the west / east eave
# meets the north plane's point with the same d on the 45 deg hip line
#   west hip  y = 2.4 - (x + 5.4)        east hip  y = x - 1
# (2.4 = the north wall's outer face). The east hip is the SAME line as the wing's
# north valley, and the north plane is coplanar with the wing's north slope (same
# eave line, same pitch): north of the wing the two are one continuous tiled plane.
# The main ridge stops 4.4 m before the north wall (board top ends at y = -1.7).
#
# Edited in place: faces south of y = -4 and the wing keep their geometry and UVs;
# the main roof north of y = -4 and the wing-ridge junction are rebuilt, welded to
# the existing vertices (found by position, the old roof's jitter included).
import bpy, bmesh, math
from mathutils import Vector, kdtree

X0, ZW, YN = -5.4, 6.0, 2.4        # main profile p=0 at x = X0; wall top; north wall outer face
WM, WW = 8.8, 4.8
EPS = 1e-4


def _run_loop(W, courses, mats):
    me = bpy.data.meshes.new("_tmp_run")
    ob = bpy.data.objects.new("_tmp_run", me)
    bpy.context.scene.collection.objects.link(ob)
    build_roof_run(ob, mats, W=W, courses=courses)
    loop, mi = boundary_loop(me, 0, 0.0)
    pts = [(round(p.y, 5), round(p.z, 5)) for p in loop]
    bpy.data.objects.remove(ob)
    bpy.data.meshes.remove(me)
    return pts, list(mi)


def main_ring(mats):
    """W=8.8 run section + the point on each side where the wing's ridge board
    top meets the course above it (the townhall roof carries that row)."""
    pts, mi = _run_loop(WM, 9, mats)
    wpts, _ = _run_loop(WW, 5, mats)
    z_board = max(z for _, z in wpts)
    y_board = min(y for y, z in wpts if abs(z - z_board) < EPS)
    n = len(pts)
    ins = []
    for i in range(n):
        if mi[i] != 0:
            continue
        a, b = pts[i], pts[(i + 1) % n]
        for (ya, za), (yb, zb) in ((a, b), (b, a)):
            if za < z_board < zb and ((abs(ya - y_board) < EPS and yb > ya) or (abs(WM - ya - y_board) < EPS and yb < ya)):
                t = (z_board - za) / (zb - za)
                ins.append((i, (round(ya + t * (yb - ya), 5), round(z_board, 5))))
    assert len(ins) == 2, ins
    for i, p in sorted(ins, reverse=True):
        pts.insert(i + 1, p)
        mi.insert(i + 1, mi[i])
    return pts, mi, z_board, y_board


def sag(y):
    return 0.025 * math.sin(math.pi * ((y + 6.0) % 4.0) / 4.0)


def build_hip(R, mats):
    """R: the townhall roof object (object mode)."""
    pts, mi, z_board, y_board = main_ring(mats)
    n = len(pts)
    d_board = None
    for p, z in pts:
        if abs(z - z_board) < EPS and p > WM / 2:
            d_board = WM - p
    mw = R.matrix_world
    bm = bmesh.new()
    bm.from_mesh(R.data)
    bm.transform(mw)
    uvl = bm.loops.layers.uv["Float2"]

    # ---- what goes: the main roof north of y = -4 and the old wing-ridge junction ----
    # a wing face lies east of both valleys (x >= 1 + |y|); everything else is the main
    # roof -- including the old ridge-board junction faces (their west edge is at x = 1.21)
    on_wing = lambda co: co.x >= 1.0 + abs(co.y) - 1e-3
    kill = [f for f in bm.faces
            if not all(on_wing(v.co) for v in f.verts) and any(v.co.y > -4.0 + 1e-3 for v in f.verts)]
    bmesh.ops.delete(bm, geom=kill, context='FACES_ONLY')
    killed = len(kill)

    # ---- vertex lookup: reuse an existing vertex at (about) that position -----------
    old = list(bm.verts)                               # stable list: the tree indexes into it
    kd = kdtree.KDTree(len(old))
    for i, v in enumerate(old):
        kd.insert(v.co, i)
    kd.balance()
    new_verts = {}

    def V(x, y, z, tol=0.004):
        c = Vector((x, y, z))
        hit = kd.find(c)
        if hit[0] is not None and hit[2] < tol:
            return old[hit[1]]
        k = (round(x, 4), round(y, 4), round(z, 4))
        if k not in new_verts:
            new_verts[k] = bm.verts.new(c)
        return new_verts[k]

    def Vstart(p, z):
        """A main row's existing vertex on the y = -4 station (jittered there)."""
        c = Vector((X0 + p, -4.0, ZW + z - (sag(-4.0) if z > 0.5 else 0.0)))
        best = None
        for co, idx, dist in kd.find_range(c, 0.04):
            if abs(old[idx].co.y + 4.0) < 0.002 and (best is None or dist < best[1]):
                best = (idx, dist)
        assert best is not None, (p, z)
        return old[best[0]]

    def P(x, y, z):                                  # a profile point at (x, y), sagged like the roof
        return V(x, y, ZW + z - (sag(y) if z > 0.5 else 0.0))

    kind_of = {0: "roof", 1: "timber", 2: "plaster"}
    kinds, dirs = {}, {}

    def side(p):
        if p < WM / 2 - EPS:
            return "w", p
        if p > WM / 2 + EPS:
            return "e", WM - p
        return "a", WM / 2

    # ---- main rows, from the y = -4 station north to the hip / valley --------------
    rows = []
    for p, z in pts:
        s, d = side(p)
        x = X0 + p
        r = [Vstart(p, z)]
        if s == "e" and d <= y_board + EPS:           # beside the wing: ends on the south valley
            r.append(P(x, -(YN - d), z))
        else:
            if s == "e" and abs(d - d_board) < 1e-3:
                r.append(P(x, -0.3, z))              # the wing ridge board's south edge
            r.append(P(x, YN - d, z))
        rows.append(r)
    for i in range(n):
        j = (i + 1) % n
        A, B = rows[i], rows[j]
        sa, da = side(pts[i][0])
        sb, db = side(pts[j][0])
        # under the wing's ridge board: the course face between the tip row (d = 2.1)
        # and the board row (d = 2.19) stops at the board's south edge
        if sa == sb == "e" and {round(da, 3), round(db, 3)} == {round(y_board, 3), round(d_board, 3)}:
            A = [v for v in A if v.co.y <= -0.3 + 1e-3]
            B = [v for v in B if v.co.y <= -0.3 + 1e-3]
        if len(A) == len(B):
            fs = [bm.faces.new(q) for q in ([A[k], B[k], B[k + 1], A[k + 1]] for k in range(len(A) - 1))
                  if len(set(q)) == 4 and bm.faces.get(q) is None]
        else:
            fs = _stitch(bm, A, B, 1)
        for f in fs:
            kinds[f] = kind_of[mi[i]]
            dirs[f] = "main"

    # ---- the north (hip) plane: the west half of the section swept along x -----------
    apex = [i for i in range(n) if abs(pts[i][0] - WM / 2) < 1e-3][0]                 # attic apex (inner)
    bw = max((i for i in range(n) if abs(pts[i][0] - (WM / 2 - 0.3)) < 1e-3), key=lambda i: pts[i][1])  # board top, west
    chain = None
    for step in (1, -1):                       # the arc apex -> ... -> board top that stays on the west half
        c, i = [apex], apex
        while i != bw and len(c) <= n:
            i = (i + step) % n
            c.append(i)
        if all(pts[k][0] <= WM / 2 + EPS for k in c):
            chain = c
    assert chain, "west half of the section not found"
    XST = (-3.0, 1.0)
    nrows = {}
    for i in chain:
        p, z = pts[i]
        d = p
        y = YN - d
        xs = [X0 + d] + [x for x in XST if X0 + d + EPS < x < 3.4 - d - EPS]
        if d <= y_board + EPS and 1.20927 < 3.4 - d - EPS:
            xs.append(X0 + WM - d_board)              # under the wing ridge board's west end
        xs.append(3.4 - d)
        xs = sorted(set(round(x, 5) for x in xs))
        nrows[i] = [P(x, y, z) for x in xs]
    for k in range(len(chain) - 1):
        i, j = chain[k], chain[k + 1]
        A, B = nrows[i], nrows[j]
        e = i if (i + 1) % n == j else j               # ring edge index (its material)
        da, db = pts[i][0], pts[j][0]
        if {round(da, 3), round(db, 3)} == {round(y_board, 3), round(d_board, 3)}:
            lim = X0 + WM - d_board + 1e-3             # course face under the board: stop at its west end
            A = [v for v in A if v.co.x <= lim]
            B = [v for v in B if v.co.x <= lim]
        if len(A) == len(B):
            fs = [bm.faces.new(q) for q in ([A[m], B[m], B[m + 1], A[m + 1]] for m in range(len(A) - 1))
                  if len(set(q)) == 4 and bm.faces.get(q) is None]
        else:
            fs = _stitch(bm, A, B, 0)
        for f in fs:
            kinds[f] = kind_of[mi[e]]
            dirs[f] = "north"

    # ---- the wing ridge board's west end ------------------------------------------------
    xb = X0 + WM - d_board                             # = the board row on both roofs
    tip_z = [z for p, z in pts if abs(p - y_board) < EPS and z > KNEE + TAN * y_board + 0.1]
    zt_, ztip = min(tip_z), max(tip_z)
    S, N = -(YN - y_board), YN - y_board               # the board's sides, y = -0.3 / +0.3

    def face(vs, k="timber"):
        f = bm.faces.new(vs)
        kinds[f] = k
        dirs[f] = "wing"
        return f
    s_foot, s_tip, s_top = P(1.3, S, zt_), P(1.3, S, ztip), P(xb, S, z_board)
    n_foot, n_tip, n_top = P(1.3, N, zt_), P(1.3, N, ztip), P(xb, N, z_board)
    w5 = lambda y, z: V(5.0, y, ZW + z - sag(y), tol=0.04)
    face([s_foot, w5(S, zt_), w5(S, z_board), s_top])                # south side (as before)
    face([s_foot, s_top, s_tip])
    n_mid = P(1.3, N, z_board)
    hip_pt = P(xb, YN - d_board, z_board)
    face([n_foot, n_tip, n_mid, w5(N, z_board), w5(N, zt_)])          # north side, east of x = 1.3
    face([P(xb, N, ztip), n_tip, n_mid, n_top])                       # ... and over the north plane's step
    face([P(xb, N, ztip), n_top, hip_pt])                             # the board's west end above the hip
    face([s_top, w5(S, z_board), w5(N, z_board), n_mid])                 # board top: a quad and two
    face([s_top, n_mid, hip_pt])                                          # triangles (its west edge has
    face([n_top, hip_pt, n_mid])                                          # the hip point on it)
    # attic underside under the wing's apex (hidden)
    zu = lambda d: KNEE + TAN * d
    D = P(1.0, 0.0, zu(2.4))
    a1, a2 = P(1.3, S, zu(2.1)), P(1.3, N, zu(2.1))
    b = P(0.8, YN - 2.6, zu(2.6))
    for tri in ((a1, b, D), (D, b, a2)):
        if bm.faces.get(tri) is None:
            f = bm.faces.new(tri)
            kinds[f] = "timber"
            dirs[f] = "main"

    # n-gons -> quads (flat junction faces only)
    big = [f for f in kinds if f.is_valid and len(f.verts) > 4]
    tag = {f: (kinds[f], dirs[f]) for f in big}
    res = bmesh.ops.triangulate(bm, faces=big, quad_method='BEAUTY', ngon_method='BEAUTY')
    for new, old in res["face_map"].items():
        if old in tag:
            kinds[new], dirs[new] = tag[old]
    bmesh.ops.delete(bm, geom=[e for e in bm.edges if not e.link_faces], context='EDGES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.normal_update()
    top = max(bm.faces, key=lambda f: f.calc_center_median().z)
    if top.normal.z < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
        bm.normal_update()

    # ---- materials + UVs for the new faces (the kept faces keep theirs) -------------
    slot = {"roof": 0, "timber": 1, "plaster": 2}
    TI = (300 / 256, 300 / 512)
    for f, k in kinds.items():
        if not f.is_valid:
            continue
        f.material_index = slot[k]
        dr = dirs[f]
        if k == "roof":
            for l in f.loops:
                c = l.vert.co
                if dr == "north":
                    l[uvl].uv = (-c.x * 0.5, roof_slope_uv(YN - c.y, c.z - ZW, W=WM))
                else:
                    l[uvl].uv = (c.y * 0.5, roof_slope_uv(c.x - X0, c.z - ZW, W=WM))
        elif k == "plaster":
            set_window_uv(f, uvl, (1.5, 1.0), (0.12, 0.88, 0.43, 0.90))
        else:
            n_ = f.normal
            along = Vector((1, 0, 0)) if dr in ("north", "wing") else Vector((0, 1, 0))
            a = along - n_ * along.dot(n_)
            if a.length < 1e-3:
                set_wrap_uv(f, uvl, TI, (0.25, 0.0))
                continue
            a.normalize()
            cdir = n_.cross(a).normalized()
            for l in f.loops:
                p_ = l.vert.co
                l[uvl].uv = (0.2 + p_.dot(cdir) * TI[0], p_.dot(a) * TI[1])
    bm.transform(mw.inverted())
    bm.to_mesh(R.data)
    R.data.update()
    bm.free()
    for poly in R.data.polygons:
        poly.use_smooth = False
    return dict(killed=killed, new_faces=len([f for f in kinds]), d_board=round(d_board, 4), z_board=z_board)


# =========================================================================
# north GABLE instead of the hip: the main roof runs on to a gable at y = YJ,
# 0.4 m out over the north wall (flush with the wing's north eave, which stops
# the wing's slope from colliding with the gable). Same rows, valleys and
# ridge-board junction as the T roof; the end is the patch layout: the slab's
# section capped in timber, the attic closed by a plaster gable panel, a soffit
# under the overhang.
# =========================================================================
YJ = 2.8


def build_gable_north(R, mats):
    pts, mi, z_board, y_board = main_ring(mats)
    n = len(pts)
    d_board = [WM - p for p, z in pts if abs(z - z_board) < EPS and p > WM / 2][0]
    xb = X0 + WM - d_board
    mw = R.matrix_world
    bm = bmesh.new()
    bm.from_mesh(R.data)
    bm.transform(mw)
    uvl = bm.loops.layers.uv["Float2"]
    on_wing = lambda co: co.x >= 1.0 + abs(co.y) - 1e-3
    board = lambda f: all(abs(v.co.y) <= 0.301 and v.co.x < 5.0 + 1e-3 for v in f.verts) \
        and max(v.co.z for v in f.verts) > ZW + 2.0
    kill = [f for f in bm.faces
            if (not all(on_wing(v.co) for v in f.verts) and any(v.co.y > -4.0 + 1e-3 for v in f.verts)) or board(f)]
    bmesh.ops.delete(bm, geom=kill, context='FACES_ONLY')
    old = list(bm.verts)
    kd = kdtree.KDTree(len(old))
    for i, v in enumerate(old):
        kd.insert(v.co, i)
    kd.balance()
    new_verts = {}

    def V(x, y, z, tol=0.004):
        c = Vector((x, y, z))
        hit = kd.find(c)
        if hit[0] is not None and hit[2] < tol:
            return old[hit[1]]
        k = (round(x, 4), round(y, 4), round(z, 4))
        if k not in new_verts:
            new_verts[k] = bm.verts.new(c)
        return new_verts[k]

    def Vstart(p, z):
        c = Vector((X0 + p, -4.0, ZW + z - (sag(-4.0) if z > 0.5 else 0.0)))
        best = None
        for co, idx, dist in kd.find_range(c, 0.04):
            if abs(old[idx].co.y + 4.0) < 0.002 and (best is None or dist < best[1]):
                best = (idx, dist)
        assert best is not None, (p, z)
        return old[best[0]]
    P = lambda x, y, z: V(x, y, ZW + z - (sag(y) if z > 0.5 else 0.0))
    kind_of = {0: "roof", 1: "timber", 2: "plaster"}
    kinds = {}

    def side(p):
        if p < WM / 2 - EPS:
            return "w", p
        if p > WM / 2 + EPS:
            return "e", WM - p
        return "a", WM / 2
    split = lambda i: side(pts[i][0])[0] == "e" and side(pts[i][0])[1] <= y_board + EPS
    # the attic arc: the inner outline between the two inner wall-top points
    inner = [i for i, (p, z) in enumerate(pts) if abs(z) < 1e-4 and abs(min(p, WM - p) - 0.4) < 1e-3]
    w_in = [i for i in inner if pts[i][0] < WM / 2][0]
    e_in = [i for i in inner if pts[i][0] > WM / 2][0]

    def path(a, b, step):
        out, i = [a], a
        while i != b:
            i = (i + step) % n
            out.append(i)
        return out
    pa, pb = path(e_in, w_in, 1), path(e_in, w_in, -1)
    attic = pa if max(pts[i][1] for i in pa) < max(pts[i][1] for i in pb) else pb
    attic_mid = set(attic[1:-1])
    attic_edges = {frozenset((attic[k], attic[k + 1])) for k in range(len(attic) - 1)}

    south, north = {}, {}
    for i, (p, z) in enumerate(pts):
        s, d = side(p)
        x = X0 + p
        end = [YN] if i in attic_mid else [YN, YJ]
        if split(i):
            south[i] = [Vstart(p, z), P(x, -(YN - d), z)]
            yv = YN - d
            north[i] = [P(x, y, z) for y in [yv] + [y for y in end if y > yv + 1e-4]]
        else:
            south[i] = [Vstart(p, z)] + [P(x, y, z) for y in [-0.3, 0.3] + end]
            north[i] = None

    def strip(A, B, k):
        dd = lambda R_: [v for m, v in enumerate(R_) if m == 0 or v is not R_[m - 1]]
        A, B = dd(A), dd(B)
        if len(A) < 2 and len(B) < 2:
            return
        if len(A) == 1 or len(B) == 1:
            one, many = (A, B) if len(A) == 1 else (B, A)
            fs = [bm.faces.new((one[0], many[m], many[m + 1])) for m in range(len(many) - 1)
                  if one[0] not in (many[m], many[m + 1])]
        elif len(A) == len(B):
            fs = [bm.faces.new(q) for q in ([A[m], B[m], B[m + 1], A[m + 1]] for m in range(len(A) - 1))
                  if len(set(q)) == 4 and bm.faces.get(q) is None]
        else:
            fs = _stitch(bm, A, B, 1)
        for f in fs:
            kinds[f] = k
    for i in range(n):
        j = (i + 1) % n
        k = kind_of[mi[i]]
        att = frozenset((i, j)) in attic_edges
        cut = (lambda R_: [v for v in R_ if v.co.y <= YN + 1e-3]) if att else (lambda R_: R_)
        si, sj = split(i), split(j)
        if not si and not sj:
            strip(cut(south[i]), cut(south[j]), k)
            continue
        for part in ("s", "n"):
            if part == "s":
                A = south[i] if si else [v for v in south[i] if v.co.y <= south[j][-1].co.y + 1e-3]
                B = south[j] if sj else [v for v in south[j] if v.co.y <= south[i][-1].co.y + 1e-3]
            else:
                A = north[i] if si else [v for v in south[i] if v.co.y >= north[j][0].co.y - 1e-3]
                B = north[j] if sj else [v for v in south[j] if v.co.y >= north[i][0].co.y - 1e-3]
            strip(cut(A), cut(B), k)

    # ---- the wing ridge board's junction (both sides, as in the T roof) ------------------
    tip_z = [z for p, z in pts if abs(p - y_board) < EPS and z > KNEE + TAN * y_board + 0.1]
    zt_, ztip = min(tip_z), max(tip_z)
    w5 = lambda y, z: V(5.0, y, ZW + z - sag(y), tol=0.04)

    def face(vs, k="timber"):
        f = bm.faces.new(vs)
        kinds[f] = k
    for y in (-(YN - y_board), YN - y_board):
        foot, tip, top = P(1.3, y, zt_), P(1.3, y, ztip), P(xb, y, z_board)
        face([foot, w5(y, zt_), w5(y, z_board), top])
        face([foot, top, tip])
    S, N = -(YN - y_board), YN - y_board
    face([P(xb, S, z_board), w5(S, z_board), w5(N, z_board), P(xb, N, z_board)])
    zu = lambda d: KNEE + TAN * d
    A_, E_ = P(1.3, S, zu(2.1)), P(1.3, N, zu(2.1))
    B_, C_ = P(0.8, -0.3, zu(2.6)), P(0.8, 0.3, zu(2.6))
    D_ = P(1.0, 0.0, zu(2.4))
    for tri in ((A_, B_, D_), (D_, B_, C_), (D_, C_, E_)):
        if bm.faces.get(tri) is None:
            face(list(tri))

    # ---- the gable end at y = YJ ------------------------------------------------------
    G = lambda i: P(X0 + pts[i][0], YJ, pts[i][1])
    gable = [(bm.faces.new([G(i) for i in range(n)]), "timber"),
             (bm.faces.new([G(i) for i in attic]), "plaster")]
    xw, xe = X0 + pts[w_in][0], X0 + pts[e_in][0]
    face([V(xw, YN, ZW), V(xe, YN, ZW), V(xe, YJ, ZW), V(xw, YJ, ZW)])            # soffit over the wall
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for f_, k in gable:
        tri = bmesh.ops.triangulate(bm, faces=[f_], quad_method='BEAUTY', ngon_method='BEAUTY')["faces"]
        bmesh.ops.join_triangles(bm, faces=tri, cmp_seam=False, cmp_sharp=False, cmp_uvs=False, cmp_vcols=False,
                                 cmp_materials=False, angle_face_threshold=math.radians(2.0),
                                 angle_shape_threshold=math.radians(180.0))
        for f in bm.faces:
            if f not in kinds and abs(f.calc_center_median().y - YJ) < 1e-3 and f.normal.length > 0 \
                    and all(abs(v.co.y - YJ) < 1e-3 for v in f.verts):
                kinds[f] = k
    big = [f for f in kinds if f.is_valid and len(f.verts) > 4]
    tag = {f: kinds[f] for f in big}
    res = bmesh.ops.triangulate(bm, faces=big, quad_method='BEAUTY', ngon_method='BEAUTY')
    for nf, of in res["face_map"].items():
        if of in tag:
            kinds[nf] = tag[of]
    bmesh.ops.delete(bm, geom=[e for e in bm.edges if not e.link_faces], context='EDGES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.normal_update()
    top = max(bm.faces, key=lambda f: f.calc_center_median().z)
    if top.normal.z < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
        bm.normal_update()
    slot = {"roof": 0, "timber": 1, "plaster": 2}
    TI = (300 / 256, 300 / 512)
    for f, k in kinds.items():
        if not f.is_valid:
            continue
        f.material_index = slot[k]
        if k == "roof":
            for l in f.loops:
                c = l.vert.co
                l[uvl].uv = (c.y * 0.5, roof_slope_uv(c.x - X0, c.z - ZW, W=WM))
        elif k == "plaster":
            n_ = f.normal
            ax = max(range(3), key=lambda i: abs(n_[i]))
            a, b2 = {0: (1, 2), 1: (0, 2), 2: (0, 1)}[ax]
            for l in f.loops:
                l[uvl].uv = (l.vert.co[a] / 2.0, l.vert.co[b2] / 2.0)
        else:
            n_ = f.normal
            along = Vector((0, 1, 0))
            a = along - n_ * along.dot(n_)
            if a.length < 1e-3:
                set_wrap_uv(f, uvl, TI, (0.25, 0.0))
                continue
            a.normalize()
            cdir = n_.cross(a).normalized()
            for l in f.loops:
                p_ = l.vert.co
                l[uvl].uv = (0.2 + p_.dot(cdir) * TI[0], p_.dot(a) * TI[1])
    bm.transform(mw.inverted())
    bm.to_mesh(R.data)
    R.data.update()
    bm.free()
    for poly in R.data.polygons:
        poly.use_smooth = False
    return dict(killed=len(kill))
