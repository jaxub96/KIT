# TEST: the townhall roof fully hipped (no gables): every side leans to the centre.
# Needs kit_lib.py, roof_gable.py, weld_pieces.py and roof_hip_townhall.py exec'd first.
#
# Same rule as the north hip (roof_hip_townhall.py), applied to every end: a profile
# point at distance d from its eave meets the neighbouring plane's point with the same
# d on the 45 deg hip line. Main roof outer faces x = -5.4 / 3.4, y = -6.4 / 2.4 (a
# square: the hips meet in a small flat cap at (-1, -2)); wing outer faces y = -/+2.4,
# x = 7.4. The wing joins the main roof in the old valleys and with the same
# ridge-board junction. Built fresh as its own object (no jitter / sag: a clean test).
import bpy, bmesh, math
from mathutils import Vector

YS, XE = -6.4, 7.4                  # main south / wing east outer faces
Y0W = -2.4                          # wing profile q=0 at y = -2.4


def build_full_hip(ob, mats):
    pts, mi, z_board, y_board = main_ring(mats)
    wpts, wmi = _run_loop(WW, 5, mats)
    n, nw = len(pts), len(wpts)
    d_board = [WM - p for p, z in pts if abs(z - z_board) < EPS and p > WM / 2][0]
    xb = X0 + WM - d_board
    bm = bmesh.new()
    cache = {}

    def V(x, y, z):
        k = (round(x, 4), round(y, 4), round(z, 4))
        if k not in cache:
            cache[k] = bm.verts.new(k)
        return cache[k]
    P = lambda x, y, z: V(x, y, ZW + z)
    kinds, plane = {}, {}
    kind_of = {0: "roof", 1: "timber", 2: "plaster"}

    def side(p, W):
        if p < W / 2 - EPS:
            return "w", p
        if p > W / 2 + EPS:
            return "e", W - p
        return "a", W / 2

    def strip(A, B, key, k, pl):
        dd = lambda R: [v for m, v in enumerate(R) if m == 0 or v is not R[m - 1]]   # an apex row is one point
        A, B = dd(A), dd(B)
        if len(A) == 1 and len(B) == 1:
            return
        if len(A) == 1 or len(B) == 1:
            one, many = (A, B) if len(A) == 1 else (B, A)
            fs = [bm.faces.new((one[0], many[m], many[m + 1])) for m in range(len(many) - 1)
                  if one[0] not in (many[m], many[m + 1])]
            for f in fs:
                kinds[f], plane[f] = k, pl
            return
        if len(A) == len(B):
            fs = [bm.faces.new(q) for q in ([A[m], B[m], B[m + 1], A[m + 1]] for m in range(len(A) - 1))
                  if len(set(q)) == 4 and bm.faces.get(q) is None]
        else:
            fs = _stitch(bm, A, B, key)
        for f in fs:
            kinds[f], plane[f] = k, pl

    # ---- main roof: rows along y between the south and north hips -------------------
    rows = []
    for p, z in pts:
        s, d = side(p, WM)
        x = X0 + p
        ys = [YS + d]
        if s == "e" and d <= y_board + EPS:
            ys.append(-(YN - d))                     # beside the wing: to the south valley
        else:
            if s == "e" and abs(d - d_board) < 1e-3:
                ys.append(-0.3)
            ys.append(YN - d)
        rows.append([P(x, y, z) for y in ys])
    for i in range(n):
        j = (i + 1) % n
        A, B = rows[i], rows[j]
        sa, da = side(pts[i][0], WM)
        sb, db = side(pts[j][0], WM)
        if sa == sb == "e" and {round(da, 3), round(db, 3)} == {round(y_board, 3), round(d_board, 3)}:
            A = [v for v in A if v.co.y <= -0.3 + 1e-3]
            B = [v for v in B if v.co.y <= -0.3 + 1e-3]
        strip(A, B, 1, kind_of[mi[i]], "main")

    # ---- the hip planes: a half section swept across ----------------------------------
    def half_chain(P_, W):
        apex = [i for i in range(len(P_)) if abs(P_[i][0] - W / 2) < 1e-3][0]
        top = max((i for i in range(len(P_)) if abs(P_[i][0] - (W / 2 - 0.3)) < 1e-3), key=lambda i: P_[i][1])
        for step in (1, -1):
            c, i = [apex], apex
            while i != top and len(c) <= len(P_):
                i = (i + step) % len(P_)
                c.append(i)
            if all(P_[k][0] <= W / 2 + EPS for k in c):
                return c
        raise RuntimeError("half section not found")

    chain = half_chain(pts, WM)
    for which in ("north", "south"):
        hrows = {}
        for i in chain:
            p, z = pts[i]
            d = p
            y = YN - d if which == "north" else YS + d
            xs = [X0 + d]
            if which == "north" and d <= y_board + EPS and xb < 3.4 - d - EPS:
                xs.append(xb)
            xs.append(3.4 - d)
            hrows[i] = [P(x, y, z) for x in sorted(set(round(x, 5) for x in xs))]
        for k in range(len(chain) - 1):
            i, j = chain[k], chain[k + 1]
            A, B = hrows[i], hrows[j]
            e = i if (i + 1) % n == j else j
            if which == "north" and {round(pts[i][0], 3), round(pts[j][0], 3)} == {round(y_board, 3), round(d_board, 3)}:
                A = [v for v in A if v.co.x <= xb + 1e-3]
                B = [v for v in B if v.co.x <= xb + 1e-3]
            strip(A, B, 0, kind_of[mi[e]], which)

    # ---- wing: rows along x from its valleys to its east hip --------------------------
    skip_first = set()                                # the ridge board's west end is built below
    wrows = []
    for q, z in wpts:
        s, d = side(q, WW)
        y = Y0W + q
        x0 = xb if abs(z - z_board) < EPS else 3.4 - d
        x1 = XE - d
        xs = [x0] + ([5.0] if x0 < 5.0 - EPS and 5.0 < x1 - EPS else []) + [x1]
        wrows.append([P(x, y, z) for x in xs])
    for i in range(nw):
        j = (i + 1) % nw
        A, B = wrows[i], wrows[j]
        za, zb_ = wpts[i][1], wpts[j][1]
        if (abs(za - z_board) < EPS) != (abs(zb_ - z_board) < EPS) or (abs(za - z_board) < EPS and abs(zb_ - z_board) < EPS):
            A = [v for v in A if v.co.x >= 5.0 - 1e-3]       # board sides / top: start at x = 5
            B = [v for v in B if v.co.x >= 5.0 - 1e-3]
            if len(A) < 2 or len(B) < 2:
                continue
        strip(B, A, 0, kind_of[wmi[i]], "wing")
    wchain = half_chain(wpts, WW)
    erows = {}
    for i in wchain:
        q, z = wpts[i]
        d = q
        erows[i] = [P(XE - d, y, z) for y in sorted({Y0W + d, -Y0W - d})]
    for k in range(len(wchain) - 1):
        i, j = wchain[k], wchain[k + 1]
        e = i if (i + 1) % nw == j else j
        strip(erows[i], erows[j], 1, kind_of[wmi[e]], "east")

    # ---- the wing ridge board's west end (as on the north hip) --------------------------
    tip_z = [z for p, z in pts if abs(p - y_board) < EPS and z > KNEE + TAN * y_board + 0.1]
    zt_, ztip = min(tip_z), max(tip_z)
    S, N = -(YN - y_board), YN - y_board

    def face(vs, k="timber"):
        f = bm.faces.new(vs)
        kinds[f], plane[f] = k, "wing"
    s_foot, s_tip, s_top = P(1.3, S, zt_), P(1.3, S, ztip), P(xb, S, z_board)
    n_foot, n_tip, n_top = P(1.3, N, zt_), P(1.3, N, ztip), P(xb, N, z_board)
    w5 = lambda y, z: P(5.0, y, z)
    n_mid = P(1.3, N, z_board)
    hip_pt = P(xb, YN - d_board, z_board)
    face([s_foot, w5(S, zt_), w5(S, z_board), s_top])
    face([s_foot, s_top, s_tip])
    face([n_foot, n_tip, n_mid, w5(N, z_board), w5(N, zt_)])
    face([P(xb, N, ztip), n_tip, n_mid, n_top])
    face([P(xb, N, ztip), n_top, hip_pt])
    face([s_top, w5(S, z_board), w5(N, z_board), n_mid])
    face([s_top, n_mid, hip_pt])
    face([n_top, hip_pt, n_mid])
    zu = lambda d: KNEE + TAN * d
    D = P(1.0, 0.0, zu(2.4))
    a1, a2, b = P(1.3, S, zu(2.1)), P(1.3, N, zu(2.1)), P(0.8, YN - 2.6, zu(2.6))
    for tri in ((a1, b, D), (D, b, a2)):
        if bm.faces.get(tri) is None:
            face(list(tri))

    big = [f for f in kinds if f.is_valid and len(f.verts) > 4]
    tag = {f: (kinds[f], plane[f]) for f in big}
    res = bmesh.ops.triangulate(bm, faces=big, quad_method='BEAUTY', ngon_method='BEAUTY')
    for new, old in res["face_map"].items():
        if old in tag:
            kinds[new], plane[new] = tag[old]
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
        k, pl = kinds.get(f, "timber"), plane.get(f, "main")
        f.material_index = slot[k]
        if k == "roof":
            for l in f.loops:
                c = l.vert.co
                z = c.z - ZW
                if pl == "main":
                    uv = (c.y * 0.5, roof_slope_uv(c.x - X0, z, W=WM))
                elif pl == "north":
                    uv = (-c.x * 0.5, roof_slope_uv(YN - c.y, z, W=WM))
                elif pl == "south":
                    uv = (c.x * 0.5, roof_slope_uv(c.y - YS, z, W=WM))
                elif pl == "east":
                    uv = (c.y * 0.5, roof_slope_uv(XE - c.x, z, W=WW))
                else:                                            # wing: south / north slope
                    uv = ((c.x if c.y < 0 else -c.x) * 0.5, roof_slope_uv(c.y - Y0W, z, W=WW))
                l[uvl].uv = uv
        elif k == "plaster":
            n_ = f.normal
            ax = max(range(3), key=lambda i: abs(n_[i]))
            a, b2 = {0: (1, 2), 1: (0, 2), 2: (0, 1)}[ax]
            for l in f.loops:
                c = l.vert.co
                l[uvl].uv = (c[a] / 2.0, c[b2] / 2.0)
        else:
            n_ = f.normal
            along = Vector((0, 1, 0)) if pl in ("main", "east") else Vector((1, 0, 0))
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
    return check_piece(ob, snap_planes=[], flat_tri_ok=True)
