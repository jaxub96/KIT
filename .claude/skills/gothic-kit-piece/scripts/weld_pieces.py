# Pieces that are DERIVED from another piece's open end loop, so their seams
# share vertices exactly and can be welded with Merge by Distance:
#   * corner block  = mitre sweep of a wall bay's end loop
#   * roof end cap  = a roof run's end loop swept outward and closed
# Needs kit_lib.py exec'd first.
import bpy, bmesh, math
from mathutils import Vector


def boundary_loop(mesh, axis, value, eps=1e-4):
    """Ordered closed loop of the open edges lying on the plane
    co[axis] == value. Returns (points, material_indices) where points are
    the vertex coordinates (Vector) in cycle order and material_indices[i]
    is the material of the face behind the edge points[i] -> points[i+1]."""
    bm = bmesh.new()
    bm.from_mesh(mesh)
    edges = [e for e in bm.edges if len(e.link_faces) == 1
             and all(abs(v.co[axis] - value) < eps for v in e.verts)]
    adj = {}
    for e in edges:
        a, b = e.verts
        adj.setdefault(a, []).append((b, e))
        adj.setdefault(b, []).append((a, e))
    start = edges[0].verts[0]
    order, mats, prev, cur, seen = [start], [], None, start, set()
    while True:
        nxt = None
        for (w, e) in adj[cur]:
            if e in seen:
                continue
            nxt = (w, e)
            break
        if nxt is None:
            break
        w, e = nxt
        seen.add(e)
        mats.append(e.link_faces[0].material_index)
        if w == start:
            break
        order.append(w)
        cur = w
    pts = [v.co.copy() for v in order]
    bm.free()
    return pts, mats


def build_corner_from_bay(ob, bay_ob, kind_of_slot, mats_by_kind, zen_coll=None, T=0.4,
                          nudge_top=False, nudge_bottom=False):
    """Mitre-sweep `bay_ob`'s end loop into a corner block.

    Local frame: outer corner at (0,0); plan [0,T]^2. The bay that runs along
    +x attaches at plane x=T (its end loop coincides with loop A), the bay that
    runs along +y attaches at plane y=T (loop B). Every profile vertex (y_i, z_i)
    becomes L_A=(T,y_i,z_i), M=(y_i,y_i,z_i), L_B=(y_i,T,z_i).

    That assumes the bay's own y runs 0 (true outer corner) to T (its
    thickness). A jettied bay's y is the same SPAN, just shifted outward
    (y0 = its own front FLAT plane, not 0) -- the "T" plane the OTHER bay's
    mitre meets is then y0+T, not T; the diagonal mitre point stays
    (y_i, y_i) unchanged, since it's already parametrized by the bay's own
    (shifted) y_i. For a normal bay y0=0 and this is exactly the formula
    above. y0 is derived from the loop's BACK plane (max y), not its front
    -- the front is contaminated by relief (timber/eave caps project
    further out than the flat plane), the back never has any."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    if zen_coll is not None:
        for o in [o for o in bpy.data.objects if o.name == ob.name + "_ZEN"]:
            bpy.data.meshes.remove(o.data)
    pts, mi = boundary_loop(bay_ob.data, 0, 0.0)
    zlo, zhi = min(p.z for p in pts), max(p.z for p in pts)
    y0 = max(p.y for p in pts) - T
    T = y0 + T
    bm = bmesh.new()
    cache = {}

    def V(x, y, z):
        k = (round(x, 5), round(y, 5), round(z, 5))
        if k not in cache:
            cache[k] = bm.verts.new((x, y, z))
        return cache[k]
    kinds = {}
    n = len(pts)
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        # the loop's own top/bottom-closing edge (both ends on the same
        # z=0/z=top plane) would sweep into a lid -- skip it so the corner
        # stays an open tube like the wall bay it's built from (the floor
        # tile / roof closes it instead, same as any wall bay run). Capping
        # it here duplicated that closing face and made those edges
        # non-manifold once welded.
        if abs(a.z - b.z) < 0.01 and (abs(a.z - zlo) < 0.01 or abs(a.z - zhi) < 0.01):
            continue
        kind = kind_of_slot[mi[i]]
        quads = [
            (V(T, a.y, a.z), V(T, b.y, b.z), V(b.y, b.y, b.z), V(a.y, a.y, a.z)),   # strip A
            (V(a.y, a.y, a.z), V(b.y, b.y, b.z), V(b.y, T, b.z), V(a.y, T, a.z)),   # strip B
        ]
        for q in quads:
            uniq = []
            for v in q:
                if v not in uniq:
                    uniq.append(v)
            if len(uniq) < 3:
                continue
            try:
                f = bm.faces.new(uniq)
            except ValueError:
                continue
            kinds[f] = kind
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    # An upper corner's flat top lip now lands exactly on the roof run/gable's
    # own bottom line (the LIP fix in wall_bay.py made it flat enough to
    # coincide) -- three pieces (wall, roof, gable) converging is fine, but
    # a fourth copy from the corner too makes one of those edges non-manifold.
    # Nudge the corner's OWN copy a hair off the plane; its ground-corner
    # counterpart must stay exactly where it is (that end genuinely welds to
    # the storey above/below), so this is opt-in per call, never both ends.
    for v in bm.verts:
        if nudge_top and abs(v.co.z - zhi) < 1e-4:
            v.co.z -= 0.004
        elif nudge_bottom and abs(v.co.z - zlo) < 1e-4:
            v.co.z += 0.004
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.normal_update()
    TI = (300 / 256, 300 / 512)
    ob.data.materials.clear()
    slot = {}
    for k in ("plaster", "timber", "stone"):
        ob.data.materials.append(mats_by_kind[k])
        slot[k] = len(ob.data.materials) - 1
    uvl = bm.loops.layers.uv.get("Float2") or bm.loops.layers.uv.new("Float2")
    for f in bm.faces:
        k = kinds.get(f, "timber")
        f.material_index = slot[k]
        if k == "stone":
            set_wrap_uv(f, uvl, (0.566, 0.566), (0.0, 0.10))
        elif k == "plaster":
            set_window_uv(f, uvl, (1.5, 1.0), (0.12, 0.88, 0.43, 0.90))
        else:
            set_beam_uv(f, uvl, "V", TI, 0.3, -0.1)
    write_piece(ob, bm)
    bm.free()
    if zen_coll is not None:
        make_export_copy(ob, zen_coll)
    top_snap = zhi - 0.004 if nudge_top else zhi
    bot_snap = zlo + 0.004 if nudge_bottom else zlo
    return check_piece(ob, snap_planes=[(0, T), (1, T), (2, bot_snap), (2, top_snap)], flat_tri_ok=True)


def build_roof_end_gable(ob, run_ob, mats_by_kind, zen_coll=None, W=4.8, length=0.7, tunnel=0.3, seed=21):
    """Closed roof end WITH the gable wall built in. Local frame: outer cap at x=0,
    open end at x=length (welds to a roof run's end loop; place it at
    x = run_x0 - length). Between x=0 and x=tunnel the attic cavity is open (a
    small overhang; the gable's face is recessed at x=tunnel and carries the
    timber frame); from x=tunnel to x=length the cavity is plugged solid and its
    back face at x=length closes the attic. Every vertex on the seam is taken from
    the run's own end loop, so Merge by Distance welds them exactly."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    if zen_coll is not None:
        for o in [o for o in bpy.data.objects if o.name == ob.name + "_ZEN"]:
            bpy.data.meshes.remove(o.data)
    kind_of = {0: "roof", 1: "timber", 2: "plaster"}
    zu = lambda y: KNEE + TAN * (y if y <= W / 2 else W - y)
    pts, mi = boundary_loop(run_ob.data, 0, 0.0)
    n = len(pts)
    notch = [(0.4 - 1e-4 <= p.y <= W - 0.4 + 1e-4 and p.z <= zu(p.y) + 1e-3) for p in pts]
    bm = bmesh.new()
    V0 = [bm.verts.new((0.0, p.y, p.z)) for p in pts]
    V7 = [bm.verts.new((length, p.y, p.z)) for p in pts]
    V3 = {i: bm.verts.new((tunnel, pts[i].y, pts[i].z)) for i in range(n)}   # every point: the plug starts here
    kinds = {}
    for i in range(n):
        j = (i + 1) % n
        k = kind_of[mi[i]]
        f = bm.faces.new((V0[i], V0[j], V3[j], V3[i]))                       # x 0 .. tunnel (tunnel wall / overhang)
        kinds[f] = k
        if not (notch[i] and notch[j]):
            f = bm.faces.new((V3[i], V3[j], V7[j], V7[i]))                   # x tunnel .. length, outer path only
            kinds[f] = k
    # outer cap (x=0): bridge the ring's upper and lower chains
    ys = [p.y for p in pts]
    i0, i1 = ys.index(min(ys)), ys.index(max(ys))
    def path(a, b, step):
        out, i = [a], a
        while i != b:
            i = (i + step) % n
            out.append(i)
        return out
    c1, c2 = path(i0, i1, 1), path(i0, i1, -1)
    up, dn = (c1, c2) if max(pts[i].z for i in c1) >= max(pts[i].z for i in c2) else (c2, c1)
    for f in _stitch(bm, [V0[i] for i in up], [V0[i] for i in dn], 1):
        kinds[f] = "timber"
    # gable grid: columns = the run's notch stations, rows = 0 / rafter line / underside
    st = sorted({round(pts[i].y, 4) for i in range(n) if notch[i] and abs(pts[i].z - zu(pts[i].y)) < 1e-3})

    def grid(x, vd):
        G = []
        for y in st:
            zt = zu(y)
            col = []
            for z in (0.0, zt - GABLE_RAF, zt):
                hit = [vd[i] for i in vd if abs(pts[i].y - y) < 1e-4 and abs(pts[i].z - z) < 1e-3]
                col.append(hit[0] if hit else bm.verts.new((x, y, z)))
            G.append(col)
        return G
    F = grid(tunnel, {i: V3[i] for i in range(n) if notch[i]})
    B = grid(length, {i: V7[i] for i in range(n) if notch[i]})
    def tagcell(c, r):
        ya, yb = st[c], st[c + 1]
        if r == 1:
            return "rafter"
        if c in (0, len(st) - 2):
            return "timber"
        return None
    raised, cell_tag = [], {}
    for c in range(len(st) - 1):
        for r in (0, 1):
            f = bm.faces.new((F[c][r], F[c + 1][r], F[c + 1][r + 1], F[c][r + 1]))
            t = tagcell(c, r)
            if t:
                raised.append(f)
            else:
                kinds[f] = "plaster"
            fb = bm.faces.new((B[c][r], B[c][r + 1], B[c + 1][r + 1], B[c + 1][r]))
            kinds[fb] = "plaster"
        fbot = bm.faces.new((F[c][0], F[c + 1][0], B[c + 1][0], B[c][0]))            # plug floor
        kinds[fbot] = "plaster"
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    def gtag(y, z):
        if z > zu(y) - GABLE_RAF + 1e-3:
            return "rafter"
        return "timber"
    caps, _ = extrude_faces(bm, raised, 0.09, along=Vector((-1.0, 0.0, 0.0)), with_sides=True)
    ctag = {f: gtag(f.calc_center_median().y, f.calc_center_median().z) for f in caps}
    capset = set(caps)
    for v in {v for f in caps for v in f.verts}:
        v.co.x = tunnel - max(0.15 if ctag[f] == "rafter" else 0.09 for f in v.link_faces if f in capset)
    inset(bm, caps, 0.028, depth=0.03)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.verts.ensure_lookup_table()
    relief = [v for v in bm.verts if v.co.x < tunnel - 0.005]
    jitter(bm, relief, (0.012, 0.008, 0.008), seed=seed)
    bm.normal_update()
    ob.data.materials.clear()
    slot = {}
    for k in ("roof", "timber", "plaster"):
        ob.data.materials.append(mats_by_kind[k])
        slot[k] = len(ob.data.materials) - 1
    uvl = bm.loops.layers.uv.get("Float2") or bm.loops.layers.uv.new("Float2")
    TI = (300 / 256, 300 / 512)
    for f in bm.faces:
        k = kinds.get(f, "timber")
        f.material_index = slot[k]
        if k == "roof":
            for loop in f.loops:
                c = loop.vert.co
                loop[uvl].uv = ((c.x - length) * 0.5, roof_slope_uv(c.y, c.z, W=W))
        elif k == "plaster":
            set_window_uv(f, uvl, (1.5, 1.0), (0.12, 0.88, 0.43, 0.90), bounds={1: [0, W / 2, W], 2: [0, 2.4]})
        elif abs(f.normal.x) > 0.9:
            set_wrap_uv(f, uvl, (TI[0], TI[1]), (0.25, 0.0))
        else:
            set_beam_uv(f, uvl, "H", TI, 0.25, 0.0)
    write_piece(ob, bm)
    bm.free()
    if zen_coll is not None:
        make_export_copy(ob, zen_coll)
    return check_piece(ob, snap_planes=[(0, length)], flat_tri_ok=True)


COS_P, SIN_P = math.cos(math.radians(38.0)), math.sin(math.radians(38.0))
