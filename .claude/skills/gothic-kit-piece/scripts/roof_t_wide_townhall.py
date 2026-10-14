# Townhall T roof, built fresh: an 8.8 m main roof (8 m room, x -5..3 inside; ridge along
# y at x = -1) from y = -6 to +6 and the kit's 4.8 m wing (y -2..2 inside) to x = 7, joined
# by two valleys like roof_t.py: a profile point at distance d from its eave meets the
# other roof's point with the same d on the 45 deg valley. The wing's ridge board dies into
# the main slope (a 2.19 m row on the main section carries its top). Ends open: y = -6 / +6
# (8.8 m gable ends) and x = 7 (the kit gable end). No jitter / sag: clean welds everywhere.
# Needs kit_lib.py, roof_gable.py, weld_pieces.py and roof_hip_townhall.py exec'd first.
import bpy, bmesh, math
from mathutils import Vector, Matrix

YS_, YN_ = -6.0, 6.0
G_ = [-6.0, -4.0, -0.3, 0.3, 4.0, 6.0]
XW_ = [5.0, 7.0]                       # wing stations after the valley


def ledge_ring(pts, mi, W, out=-0.16, post=-0.12):
    """The section's bottom strip (outer face .. inside face at the wall top) is
    left OPEN and a ledge runs out to the walls' seam front (out = -SEAM_D), with a
    point at the gable posts' arm (post = -POST_D): the roof then welds onto the
    walls' open top seam instead of leaving the eave beam's top uncovered. mi -1 =
    open edge."""
    n = len(pts)
    eq = lambda p, q: abs(p[0] - q[0]) < 1e-4 and abs(p[1] - q[1]) < 1e-4
    sides = [((0.0, 0.0), (0.4, 0.0), out, post), ((W, 0.0), (W - 0.4, 0.0), W - out, W - post)]
    P2, M2 = [], []
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        P2.append(a)
        done = False
        for o, inn, yo, yp in sides:
            if eq(a, o) and eq(b, inn):                  # outer bottom -> inside: ledge out, then open
                M2 += [1, 1, -1]
                P2 += [(yp, 0.0), (yo, 0.0)]
                done = True
            elif eq(a, inn) and eq(b, o):                # inside -> outer bottom: open, then ledge in
                M2 += [-1, 1, 1]
                P2 += [(yo, 0.0), (yp, 0.0)]
                done = True
        if not done:
            M2.append(mi[i])
    return P2, M2


def build_t_wide(ob, mats):
    pts, mi, z_board, y_board = main_ring(mats)
    pts, mi = ledge_ring(pts, mi, WM)
    wpts, wmi = _run_loop(WW, 5, mats)
    wpts, wmi = ledge_ring(wpts, wmi, WW)
    n, nw = len(pts), len(wpts)
    d_board = [WM - p for p, z in pts if abs(z - z_board) < EPS and p > WM / 2][0]
    xb = X0 + WM - d_board
    R2 = WW / 2
    bm = bmesh.new()
    cache = {}

    def V(x, y, z):
        k = (round(x, 4), round(y, 4), round(z, 4))
        if k not in cache:
            cache[k] = bm.verts.new(k)
        return cache[k]
    P = lambda x, y, z: V(x, y, ZW + z)
    kinds, part = {}, {}
    kind_of = {0: "roof", 1: "timber", 2: "plaster"}

    def side(p):
        if p < WM / 2 - EPS:
            return "w", p
        if p > WM / 2 + EPS:
            return "e", WM - p
        return "a", WM / 2
    split = lambda i: side(pts[i][0])[0] == "e" and side(pts[i][0])[1] <= y_board + EPS

    def strip(A, B, key, k, pt):
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
            fs = _stitch(bm, A, B, key)
        for f in fs:
            kinds[f], part[f] = k, pt

    # ---- main roof ---------------------------------------------------------------------
    S_, N_ = {}, {}
    for i, (p, z) in enumerate(pts):
        s, d = side(p)
        x = X0 + p
        if split(i):
            yv = YN - d                                      # valley offset from y = 0
            S_[i] = [P(x, y, z) for y in G_ if y < -yv - 1e-4] + [P(x, -yv, z)]
            N_[i] = [P(x, yv, z)] + [P(x, y, z) for y in G_ if y > yv + 1e-4]
        else:
            S_[i] = [P(x, y, z) for y in G_]
            N_[i] = None
    for i in range(n):
        j = (i + 1) % n
        if mi[i] < 0:
            continue
        k = kind_of[mi[i]]
        si, sj = split(i), split(j)
        if not si and not sj:
            strip(S_[i], S_[j], 1, k, "main")
            continue
        A = S_[i] if si else [v for v in S_[i] if v.co.y <= S_[j][-1].co.y + 1e-3]
        B = S_[j] if sj else [v for v in S_[j] if v.co.y <= S_[i][-1].co.y + 1e-3]
        strip(A, B, 1, k, "main")
        A = N_[i] if si else [v for v in S_[i] if v.co.y >= N_[j][0].co.y - 1e-3]
        B = N_[j] if sj else [v for v in S_[j] if v.co.y >= N_[i][0].co.y - 1e-3]
        strip(A, B, 1, k, "main")

    # ---- wing --------------------------------------------------------------------------
    WR = []
    for q, z in wpts:
        d = min(q, WW - q)
        x0 = xb if abs(z - z_board) < EPS else 3.4 - d
        WR.append([P(x, -R2 + q, z) for x in [x0] + XW_])
    for i in range(nw):
        j = (i + 1) % nw
        if wmi[i] < 0:
            continue
        strip(WR[j], WR[i], 0, kind_of[wmi[i]], "wing")

    # ---- the ridge board's west end and the attic under the wing's apex ------------------
    tip_z = [z for p, z in pts if abs(p - y_board) < EPS and z > KNEE + TAN * y_board + 0.1]
    zt_, ztip = min(tip_z), max(tip_z)
    for y in (-(R2 - y_board), R2 - y_board):
        f = bm.faces.new((P(1.3, y, zt_), P(xb, y, z_board), P(1.3, y, ztip)))
        kinds[f], part[f] = "timber", "wing"
    zu = lambda d: KNEE + TAN * d
    A_, E_ = P(1.3, -0.3, zu(2.1)), P(1.3, 0.3, zu(2.1))
    B_, C_ = P(0.8, -0.3, zu(2.6)), P(0.8, 0.3, zu(2.6))
    D_ = P(1.0, 0.0, zu(2.4))
    for tri in ((A_, B_, D_), (D_, B_, C_), (D_, C_, E_)):
        f = bm.faces.new(tri)
        kinds[f], part[f] = "timber", "main"
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.normal_update()
    top = max(bm.faces, key=lambda f: f.calc_center_median().z)
    if top.normal.z < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
        bm.normal_update()

    # ---- materials + UVs ----------------------------------------------------------------
    ob.data.materials.clear()
    for k in ("roof", "timber", "plaster"):
        ob.data.materials.append(mats[k])
    slot = {"roof": 0, "timber": 1, "plaster": 2}
    uvl = bm.loops.layers.uv.new("Float2")
    TI = (300 / 256, 300 / 512)
    for f in bm.faces:
        k, pt = kinds.get(f, "timber"), part.get(f, "main")
        f.material_index = slot[k]
        if k == "roof":
            fy = f.calc_center_median().y
            for l in f.loops:
                c = l.vert.co
                if pt == "main":
                    l[uvl].uv = (c.y * 0.5, roof_slope_uv(c.x - X0, c.z - ZW, W=WM))
                else:                                  # both wing slopes read left -> right
                    l[uvl].uv = (((c.x - 7.0) if fy < 0 else (7.0 - c.x)) * 0.5,
                                 roof_slope_uv(c.y + R2, c.z - ZW, W=WW))
        elif k == "plaster":
            set_window_uv(f, uvl, (1.5, 1.0), (0.12, 0.88, 0.43, 0.90))
        else:
            n_ = f.normal
            along = Vector((0, 1, 0)) if pt == "main" else Vector((1, 0, 0))
            a = along - n_ * along.dot(n_)
            if a.length < 1e-3:
                set_wrap_uv(f, uvl, TI, (0.25, 0.0))
                continue
            a.normalize()
            cdir = n_.cross(a).normalized()
            for l in f.loops:
                p_ = l.vert.co
                l[uvl].uv = (0.2 + p_.dot(cdir) * TI[0], p_.dot(a) * TI[1])
    write_piece(ob, bm)
    bm.free()
    return pts, mi, wpts, wmi


def temp_run(pts, mi, mats):
    """A throwaway run object whose x = 0 end loop is this section (gable_end reads it)."""
    me = bpy.data.meshes.new("KIT_ROOF_TMPRUN")
    run = bpy.data.objects.new("KIT_ROOF_TMPRUN", me)
    bpy.context.scene.collection.objects.link(run)
    bm = bmesh.new()
    nn = len(pts)
    A = [bm.verts.new((0, y - 0.4, z)) for y, z in pts]
    B = [bm.verts.new((1, y - 0.4, z)) for y, z in pts]
    for i in range(nn):
        f = bm.faces.new((A[i], A[(i + 1) % nn], B[(i + 1) % nn], B[i]))
        f.material_index = mi[i]
    bm.to_mesh(me)
    bm.free()
    for k in ("roof", "timber", "plaster"):
        me.materials.append(mats[k])
    return run


def build_welded_gable(ob, pts, mi, mats, W, loc, rot, walls, **frame):
    """A gable end welded to the walls under it (gable_end, welded mode), from this section."""
    ob.location, ob.rotation_euler, ob.scale = loc, (0, 0, rot), (1, 1, 1)
    bpy.context.view_layer.update()
    loops = wall_loop_from_scene(ob, walls, W=W)
    run = temp_run(pts, [m if m >= 0 else 2 for m in mi], mats)
    res = build_gable_end(ob, run, mats, W=W, wall_loops=loops, **frame)
    ob.data.transform(Matrix.Translation((-0.7, -0.4, 0)))
    me = run.data
    bpy.data.objects.remove(run)
    bpy.data.meshes.remove(me)
    return res
