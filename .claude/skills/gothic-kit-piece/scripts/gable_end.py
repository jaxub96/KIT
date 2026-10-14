# Roof end with the gable wall built in -- v2 (2026-09-23), replacing
# weld_pieces.build_roof_end_gable. Needs kit_lib.py, roof_gable.py and
# weld_pieces.py exec'd first.
#
# Structure (legacy frame of the run: y = profile, outer wall faces 0 / W, the
# piece spans x = 0 (outer verge cap) .. L (welds to a run's end loop)):
#   * only the roof SLAB overhangs (x = 0 .. T): roofline + a flat verge underside
#     that follows the slab underside zu(y); the old version swept the whole
#     profile, so the solid knee zone under the eave stuck out 0.3 m past the
#     wall line as a block down to the wall top
#   * the gable face sits in the wall's outer plane (x = T) as a timber frame at
#     depth POST_D -- two corner posts (0 .. P and W-P .. W, P = the timber below:
#     corner block 0.4 + wall end post 0.15) and the rafter band under the slab --
#     around a recessed plaster panel
#   * each corner post wraps round the corner onto the long side (x = T .. L), so
#     the corner block below carries on up to the eave; its top edge meets the
#     run's soffit station at y = -POST_D, its x = L end is part of the weld
#   * the attic is closed by a plaster back face at x = L (the run's notch loop)
# Open edges: only the x = L loop, identical to the run's end loop.
import bpy, bmesh, math
from mathutils import Vector

GABLE_L, GABLE_T, POST_W = 0.7, 0.3, 0.55


def wall_top_loop(bay_ob, corner_ob, L=GABLE_L, T=GABLE_T, W=4.8):
    """The open top edges of the walls a gable end sits on -- the end-wall bay
    and its two corner blocks, placed as in a house (gable at its run origin,
    walls one storey below) and expressed in the gable's legacy frame. Returns
    (front, back): the outer chain from (L, -rel) round the end to (L, W+rel),
    and the back chain along x = L, both as ordered point lists at z = 0."""
    from mathutils import Matrix
    sh = Matrix.Translation(Vector(origin_shift("KIT_ROOF_END_GABLE_A")))
    place = [(bay_ob, sh @ Matrix.Translation((0, 4, -3)) @ Matrix.Rotation(math.radians(270), 4, 'Z')),
             (corner_ob, sh @ Matrix.Translation((0, 0, -3))),
             (corner_ob, sh @ Matrix.Translation((0, 4, -3)) @ Matrix.Rotation(math.radians(270), 4, 'Z'))]
    return _wall_loop(place, L, W)


def wall_loop_from_scene(gable_ob, wall_obs, L=GABLE_L, W=4.8):
    """wall_top_loop() for walls already placed in a scene under a placed (rebased)
    gable end -- any width, any number of bays (e.g. two 4 m bays under an 8.8 m
    gable). wall_obs: the end-wall bays and the two corner blocks under it."""
    from mathutils import Matrix
    to_legacy = (gable_ob.matrix_world @ Matrix.Translation(-Vector(origin_shift("KIT_ROOF_END_GABLE_A")))).inverted()
    return _wall_loop([(o, to_legacy @ o.matrix_world) for o in wall_obs], L, W)


def _wall_loop(place, L, W):
    key = lambda co: (round(co.x, 4), round(co.y, 4))
    adj = {}
    for ob_, mx in place:
        bm = bmesh.new(); bm.from_mesh(ob_.data); bm.transform(mx)
        for e in bm.edges:
            if len(e.link_faces) == 1 and all(abs(v.co.z) < 1e-3 for v in e.verts):
                a, b = key(e.verts[0].co), key(e.verts[1].co)
                if a != b:
                    adj.setdefault(a, set()).add(b); adj.setdefault(b, set()).add(a)
        bm.free()
    on_back = lambda p: abs(p[0] - L) < 1e-3 and 0.4 - 1e-3 <= p[1] <= W - 0.4 + 1e-3
    def walk(start, allowed):
        out, prev, cur = [start], None, start
        while True:
            nxt = [q for q in adj[cur] if q != prev and allowed(cur, q) and q not in out]
            if not nxt:
                return out
            prev, cur = cur, nxt[0]
            out.append(cur)
    start = min((p for p in adj if abs(p[0] - L) < 1e-3 and p[1] < 0), key=lambda p: p[1])
    front = walk(start, lambda a, b: not (on_back(a) and on_back(b)))
    back = sorted({p for p in adj if on_back(p)}, key=lambda p: p[1])
    return front, back


def build_gable_end(ob, run_ob, mats_by_kind, bay_ob=None, corner_ob=None, W=4.8, L=GABLE_L, T=GABLE_T, P=POST_W, D=None,
                    wall_loops=None, extra_posts=(), rail=None):
    """bay_ob / corner_ob: the (rebased) wall bay and corner the gable sits on
    (or wall_loops = wall_loop_from_scene(...) for walls placed in a scene).
    extra_posts: more frame posts [(y0, y1), ...] (a wide gable: king post, studs);
    rail = (z0, z1, y0, y1): a horizontal rail between posts, flush with them.
    Given, the gable's bottom is left open along exactly their top edges (a
    ledge strip covers the eave top in front of the frame) so a house merges
    into one shell; without them it gets a closed bottom face (old behaviour)."""
    D = POST_D if D is None else D
    zu = lambda y: KNEE + TAN * (y if y <= W / 2 else W - y)
    loop, mi = boundary_loop(run_ob.data, 0, 0.0)
    y_off = origin_shift(run_ob.name)[1]
    pts = [(round(p.y + y_off, 5), round(p.z, 5)) for p in loop]
    n = len(pts)
    kind_of = {0: "roof", 1: "timber", 2: "plaster"}
    bm = bmesh.new()
    cache = {}

    def V(x, y, z):
        k = (round(x, 5), round(y, 5), round(z, 5))
        if k not in cache:
            cache[k] = bm.verts.new(k)
        return cache[k]
    kinds, tags = {}, {}

    def face(vs, kind, tag=None):
        uniq = []
        for v in vs:
            if v not in uniq:
                uniq.append(v)
        if len(uniq) < 3:
            return None
        f = bm.faces.new(uniq)
        kinds[f], tags[f] = kind, tag
        return f

    # ---- the run's loop: roofline path (over the top) between the two eaves ----
    eave = [i for i in range(n) if abs(pts[i][0] + 0.4) < 1e-4 or abs(pts[i][0] - (W + 0.4)) < 1e-4]
    e0 = min((i for i in eave if pts[i][0] < 0), key=lambda i: pts[i][1])       # (-0.4, soffit end)
    e1 = min((i for i in eave if pts[i][0] > 0), key=lambda i: pts[i][1])
    def path(a, b, step):
        out, i = [a], a
        while i != b:
            i = (i + step) % n
            out.append(i)
        return out
    pa, pb = path(e0, e1, 1), path(e0, e1, -1)
    roof = pa if max(pts[i][1] for i in pa) > max(pts[i][1] for i in pb) else pb
    step = 1 if roof is pa else -1
    edge_mi = lambda i, j: mi[i] if (j - i) % n == 1 else mi[j]                  # material of edge i-j

    # ---- stations -----------------------------------------------------------------
    notch_st = sorted({pts[i][0] for i in range(n) if 0.4 - 1e-4 <= pts[i][0] <= W - 0.4 + 1e-4
                       and abs(pts[i][1] - zu(pts[i][0])) < 1e-3})
    C = sorted({round(c, 5) for c in [-D, 0.0, P, W - P, W, W + D] + notch_st + [y for ab in extra_posts for y in ab]})   # frame columns
    SU = sorted(set(C) | {-0.4, W + 0.4})                                         # underside stations
    xs_front = lambda y: L if (y < -D - 1e-6 or y > W + D + 1e-6) else T - D      # verge underside reach

    # ---- roof slab shell: roofline + fascia swept 0 .. L -------------------------------
    XR = [0.0, T - D, L]
    for a, b in zip(roof, roof[1:]):
        k = kind_of[edge_mi(a, b)]
        (ya, za), (yb, zb) = pts[a], pts[b]
        for x0, x1 in zip(XR, XR[1:]):
            face([V(x0, ya, za), V(x1, ya, za), V(x1, yb, zb), V(x0, yb, zb)], k, "shell")

    # ---- verge underside (the slab's underside, x = 0 .. its reach) ---------------------
    for ya, yb in zip(SU, SU[1:]):
        ym = (ya + yb) / 2
        xl = [0.0, T - D] + ([L] if xs_front(ym) == L else [])
        for x0, x1 in zip(xl, xl[1:]):
            face([V(x0, ya, zu(ya)), V(x0, yb, zu(yb)), V(x1, yb, zu(yb)), V(x1, ya, zu(ya))], "timber", "soffit")

    # ---- outer verge cap at x = 0: the slab section, re-filled ----------------------
    cap_outline = [V(0.0, *pts[i]) for i in roof] + [V(0.0, y, zu(y)) for y in reversed(SU[1:-1])]
    cap = face(cap_outline, "timber", "cap")

    # ---- gable frame front (x = T - D) and plaster panel (x = T) --------------------
    mid = lambda y: zu(y) - GABLE_RAF
    in_extra = lambda y: any(a_ - 1e-6 < y < b_ + 1e-6 for a_, b_ in extra_posts)
    is_post = lambda y: y < P - 1e-6 or y > W - P + 1e-6 or any(a_ < y < b_ for a_, b_ in extra_posts)
    r0, r1, ry0, ry1 = rail if rail else (None, None, 0.0, 0.0)
    has_rail = lambda y: rail is not None and ry0 - 1e-6 < y < ry1 + 1e-6
    rows = lambda y: [0.0, r0, r1, mid(y)] if (rail and in_extra(y) and mid(y) > r1 + 0.05) else [0.0, mid(y)]
    for ca, cb in zip(C, C[1:]):
        ym = (ca + cb) / 2
        xf = T - D
        md = [V(xf, ca, mid(ca)), V(xf, cb, mid(cb))]
        top = [V(xf, ca, zu(ca)), V(xf, cb, zu(cb))]
        face([md[0], md[1], top[1], top[0]], "timber", "post" if is_post(ym) else "rafter")
        if is_post(ym):
            za, zb_ = rows(ca), rows(cb)
            if len(za) == len(zb_):
                for k_ in range(len(za) - 1):
                    face([V(xf, ca, za[k_]), V(xf, cb, zb_[k_]), V(xf, cb, zb_[k_ + 1]), V(xf, ca, za[k_ + 1])], "timber", "post")
            else:
                face([V(xf, ca, z) for z in za] + [V(xf, cb, z) for z in reversed(zb_)], "timber", "post")
        elif has_rail(ym):                                    # panel / rail / panel
            face([V(T, ca, 0.0), V(T, cb, 0.0), V(T, cb, r0), V(T, ca, r0)], "plaster", "panel")
            face([V(T, ca, r0), V(T, cb, r0), V(xf, cb, r0), V(xf, ca, r0)], "timber", "rail")
            face([V(xf, ca, r0), V(xf, cb, r0), V(xf, cb, r1), V(xf, ca, r1)], "timber", "rail")
            face([V(xf, ca, r1), V(xf, cb, r1), V(T, cb, r1), V(T, ca, r1)], "timber", "rail")
            face([V(T, ca, r1), V(T, cb, r1), V(T, cb, mid(cb)), V(T, ca, mid(ca))], "plaster", "panel")
            face([V(T, ca, mid(ca)), V(T, cb, mid(cb)), md[1], md[0]], "timber", "rafter")
        else:                                                 # a stud's split side rows stay on the panel's edge
            face([V(T, cb, z) for z in rows(cb)] + [V(T, ca, z) for z in reversed(rows(ca))], "plaster", "panel")
            face([V(T, ca, mid(ca)), V(T, cb, mid(cb)), md[1], md[0]], "timber", "rafter")   # reveal under the rafter
    for y in (P, W - P):                                                        # post inner sides (reveals)
        face([V(T - D, y, 0.0), V(T, y, 0.0), V(T, y, mid(y)), V(T - D, y, mid(y))], "timber", "post")
    for a_, b_ in extra_posts:                                                  # extra posts' sides
        for y in (a_, b_):
            zz = rows(y)
            if has_rail(y + (0.01 if y == b_ else -0.01)) and len(zz) == 4:     # the rail side: flush, no reveal there
                spans = [(zz[0], zz[1]), (zz[2], zz[3])]
            else:
                spans = list(zip(zz, zz[1:]))
            for z0_, z1_ in spans:
                face([V(T - D, y, z0_), V(T, y, z0_), V(T, y, z1_), V(T - D, y, z1_)], "timber", "post")

    # ---- corner posts' long-side arms (y = -D and W + D, x = T - D .. L) ------------------
    for y, yw in ((-D, 0.0), (W + D, W)):
        face([V(T - D, y, 0.0), V(L, y, 0.0), V(L, y, mid(y)), V(T - D, y, mid(y))], "timber", "post")
        face([V(T - D, y, mid(y)), V(L, y, mid(y)), V(L, y, zu(y)), V(T - D, y, zu(y))], "timber", "post")
        # the arm's end in the weld plane x = L: wall plane (yw) to the arm face (y)
        face([V(L, yw, 0.0), V(L, y, 0.0), V(L, y, mid(y)), V(L, y, zu(y)), V(L, yw, KNEE)], "timber", "post_end")

    def _frame_foot(C_, P_, W_):
        """the frame's bottom between the corner posts: panel feet at T, extra posts
        stepping out to their front at T - D"""
        out_ = []
        for y in C_:
            if not (P_ - 1e-6 <= y <= W_ - P_ + 1e-6):
                continue
            if any(abs(y - a_) < 1e-6 for a_, b_ in extra_posts):
                out_ += [V(T, y, 0.0), V(T - D, y, 0.0)]
            elif any(abs(y - b_) < 1e-6 for a_, b_ in extra_posts):
                out_ += [V(T - D, y, 0.0), V(T, y, 0.0)]
            elif any(a_ < y < b_ for a_, b_ in extra_posts):
                out_.append(V(T - D, y, 0.0))            # a column through a post: its foot is at the front
            else:
                out_.append(V(T, y, 0.0))
        return out_

    # ---- attic back face at x = L (the run's notch loop) -------------------------------
    welded = (bay_ob is not None and corner_ob is not None) or wall_loops is not None
    if welded:
        front, back = wall_loops if wall_loops is not None else wall_top_loop(bay_ob, corner_ob, L=L, T=T, W=W)
    for ca, cb in zip(notch_st, notch_st[1:]):
        if not welded:
            face([V(L, ca, 0.0), V(L, ca, mid(ca)), V(L, cb, mid(cb)), V(L, cb, 0.0)], "plaster", "back")
        face([V(L, ca, mid(ca)), V(L, ca, zu(ca)), V(L, cb, zu(cb)), V(L, cb, mid(cb))], "plaster", "back")
    if welded:
        # attic back face below the rafter band, laid out like the user's hand
        # version: a row at each course station's rafter height, running across
        # to a centre column at the ridge line, and one ladder of quads down to
        # the walls' back chain (the columns every bay shares: ends + mirror line)
        R = W / 2
        lefts = [y for y in notch_st if 0.4 + 1e-6 < y < R - 1e-6]
        for i in range(len(lefts) - 1):
            s0, s1 = lefts[i], lefts[i + 1]
            ctop = mid(s1) if i < len(lefts) - 2 else mid(R)
            face([V(L, s0, mid(s0)), V(L, R, mid(s0)), V(L, R, ctop), V(L, s1, mid(s1))], "plaster", "back")
            face([V(L, W - s0, mid(s0)), V(L, W - s1, mid(s1)), V(L, R, ctop), V(L, R, mid(s0))], "plaster", "back")
        up = [V(L, 0.4, mid(0.4)), V(L, lefts[0], mid(lefts[0])), V(L, R, mid(lefts[0])),
              V(L, W - lefts[0], mid(lefts[0])), V(L, W - 0.4, mid(W - 0.4))]
        dn = [V(L, y, 0.0) for (x, y) in back]
        if len(dn) == len(up):
            for i in range(len(dn) - 1):
                face([dn[i], dn[i + 1], up[i + 1], up[i]], "plaster", "back")
        else:
            for f in _stitch(bm, dn, up, 1):
                kinds[f], tags[f] = "plaster", "back"
        # ledge: the eave top between the walls' front chain and the gable's own
        # bottom outline (long-side arm, frame / panel, other arm), per side
        outline = ([V(L, -D, 0.0), V(T - D, -D, 0.0)]
                   + [V(T - D, y, 0.0) for y in C if -D + 1e-6 < y <= P + 1e-6]
                   + _frame_foot(C, P, W)
                   + [V(T - D, y, 0.0) for y in C if W - P - 1e-6 <= y < W + D - 1e-6]
                   + [V(T - D, W + D, 0.0), V(L, W + D, 0.0)])
        F = [V(x, y, 0.0) for (x, y) in front]
        c0 = min(range(len(F)), key=lambda i: F[i].co.x + (0 if F[i].co.y < W / 2 else 99))   # south mitre point
        c1 = min(range(len(F)), key=lambda i: F[i].co.x + (0 if F[i].co.y > W / 2 else 99))   # north mitre point
        segs = [(F[:c0 + 1], outline[:2], 0), (F[c0:c1 + 1], outline[1:-1], 1), (F[c1:], outline[-2:], 0)]
        for fch, och, ax in segs:                            # one flat polygon each; re-filled below
            face(list(fch) + list(reversed(och)), "timber", "ledge")
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bottom = ([V(T - D, -D, 0.0), V(L, -D, 0.0), V(L, 0.0, 0.0)] + [V(L, y, 0.0) for y in notch_st]
              + [V(L, W, 0.0), V(L, W + D, 0.0), V(T - D, W + D, 0.0)]
              + [V(T - D, y, 0.0) for y in reversed(C) if y >= W - P - 1e-6 and y < W + D - 1e-6]
              + [V(T, y, 0.0) for y in reversed(C) if P - 1e-6 <= y <= W - P + 1e-6]
              + [V(T - D, y, 0.0) for y in reversed(C) if -D + 1e-6 < y <= P + 1e-6])
    if not welded:
        face(bottom, "plaster", "bottom")

    # ---- n-gons (cap, bottom, post ends) -> quads where possible ------------------------
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    big = [f for f in bm.faces if len(f.verts) > 4]
    tagged = {f: (kinds[f], tags[f]) for f in big}
    res = bmesh.ops.triangulate(bm, faces=big, quad_method='BEAUTY', ngon_method='BEAUTY')
    for new, old in res["face_map"].items():                # face_map: new face -> its source face
        if old in tagged:
            kinds[new], tags[new] = tagged[old]
    tri = [f for f in res["faces"]]
    before = set(bm.faces)
    bmesh.ops.join_triangles(bm, faces=tri, cmp_seam=False, cmp_sharp=False, cmp_uvs=False, cmp_vcols=False,
                             cmp_materials=False, angle_face_threshold=math.radians(2.0),
                             angle_shape_threshold=math.radians(180.0))
    for f in bm.faces:
        if f not in kinds:                                  # a joined face: take a neighbour's tag in its plane
            for e in f.edges:
                for g in e.link_faces:
                    if g is not f and g in kinds and abs(g.normal.dot(f.normal)) > 0.99:
                        kinds[f], tags[f] = kinds[g], tags[g]
                        break
                if f in kinds:
                    break
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    top = max(bm.faces, key=lambda f: f.calc_center_median().z)
    if top.normal.z < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])

    # ---- materials + UVs --------------------------------------------------------------
    ob.data.materials.clear()
    for k in ("roof", "timber", "plaster"):
        ob.data.materials.append(mats_by_kind[k])
    slot = {"roof": 0, "timber": 1, "plaster": 2}
    uvl = bm.loops.layers.uv.get("Float2") or bm.loops.layers.uv.new("Float2")
    TI = (300 / 256, 300 / 512)
    for f in bm.faces:
        k, t = kinds.get(f, "timber"), tags.get(f)
        f.material_index = slot[k]
        if k == "roof":
            for l in f.loops:
                c = l.vert.co
                l[uvl].uv = ((c.x - L) * 0.5, roof_slope_uv(c.y, c.z, W=W))
        elif k == "plaster":
            set_window_uv(f, uvl, (1.5, 1.0), (0.12, 0.88, 0.43, 0.90), bounds={1: [0, W / 2, W], 2: [0, 2.4]})
        elif t == "post" or t == "post_end":
            set_beam_uv(f, uvl, "V", TI, 0.3, 0.0)
        elif t == "rail":                                   # grain along the rail
            n_ = f.normal
            along = Vector((0.0, 1.0, 0.0))
            a_ = (along - n_ * along.dot(n_))
            if a_.length < 1e-3:
                set_wrap_uv(f, uvl, (TI[0], TI[1]), (0.25, 0.0))
            else:
                a_.normalize(); c_ = n_.cross(a_).normalized()
                for l in f.loops:
                    p = l.vert.co
                    l[uvl].uv = (0.4 + p.dot(c_) * TI[0], p.dot(a_) * TI[1])
        elif t == "rafter":                                 # grain along the slope
            c = f.calc_center_median()
            sgn = 1.0 if c.y < W / 2 else -1.0
            along = Vector((0.0, sgn * math.cos(math.atan(TAN)), math.sin(math.atan(TAN))))
            across = f.normal.cross(along).normalized()
            for l in f.loops:
                p = l.vert.co
                l[uvl].uv = (0.25 + p.dot(across) * TI[0], p.dot(along) * TI[1])
        elif t == "ledge":
            set_wrap_uv(f, uvl, (TI[0], TI[1]), (0.25, 0.0))
        elif t == "cap" or abs(f.normal.x) > 0.9:
            set_wrap_uv(f, uvl, (TI[0], TI[1]), (0.25, 0.0))
        else:
            set_beam_uv(f, uvl, "H", TI, 0.25, 0.0)
    write_piece(ob, bm)
    bm.free()
    return check_piece(ob, snap_planes=[(0, L)] + ([(2, 0.0)] if welded else []), flat_tri_ok=True)
