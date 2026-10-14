# T roof junction: a 12 m main roof (three 4 m bays) with a 4 m wing roof
# running off its middle bay at 90 degrees, joined by two real valleys.
# Needs kit_lib.py, roof_gable.py and weld_pieces.py exec'd first.
#
# Built FROM the roof run's own end loop, like the corner block is built from
# the wall bay's: the main roof is that profile swept along x, the wing is the
# same profile swept along y, and each valley is their mitre. Both roofs have
# the same pitch, eave height and course spacing, so a profile point at
# distance s from its ridge meets the other roof's point at the same s exactly
# on the 45 deg valley line -- every shingle course, the soffit, the knee
# skirts and the attic outline turn the corner vertex for vertex.
#
# Legacy frame (the run's build frame): main ridge along x, the middle bay's
# run origin at x=0 (bay x 0..4), y = profile (outer wall faces 0 / 4.8, ridge
# at 2.4). Wing centre line x = 2, wing runs off to +y. Open ends, all exactly
# the run's end loop: main x = -4 and x = 8, wing y = 8.4. rebase_origin() then
# puts the origin on the middle bay's run origin, like a run: the piece snaps
# on the grid point of the middle bay, and runs / gable ends snap onto the
# three ends at x = -4, x = 8 and y = 8 (wing, run rotated 90).
import bpy, bmesh, math, random
from mathutils import Vector

T_WEST, T_EAST, T_NORTH = -4.0, 8.0, 8.4
WING_C = 2.0                                  # wing centre line (x)


def build_roof_t(ob, run_ob, seed=9, W=4.8):
    """Rebuild `ob` as the T junction from `run_ob`'s end loop and materials."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    # the run's end loop, back in its legacy build frame (y at the outer wall)
    loop, mi = boundary_loop(run_ob.data, 0, 0.0)
    y_off = origin_shift(run_ob.name)[1]            # the kit's run is rebased
    pts = [(round(p.y + y_off, 5), round(p.z, 5)) for p in loop]
    R = W / 2
    n = len(pts)
    side = lambda p: 0 if abs(p[0] - R) < 1e-4 else (-1 if p[0] < R else 1)
    s_of = lambda p: abs(p[0] - R)
    G = [T_WEST, -2.0, WING_C - 0.3, WING_C + 0.3, 6.0, T_EAST]   # main stations (0.3 = half ridge cap)

    bm = bmesh.new()
    cache = {}

    def V(x, y, z):
        k = (round(x, 4), round(y, 4), round(z, 4))
        if k not in cache:
            cache[k] = bm.verts.new(k)
        return cache[k]

    def main_cols(p, part):
        """Main-roof vertex row for profile point p: 'full' (south / apex) or the
        west / east part of a north point, which stops at its valley."""
        y, z = p
        if side(p) < 0 or part == "full":
            xs = sorted(set(G) | ({WING_C} if side(p) == 0 else set()))
        elif part == "west":
            xs = [x for x in G if x < WING_C - s_of(p) - 1e-6] + [WING_C - s_of(p)]
        else:
            xs = [WING_C + s_of(p)] + [x for x in G if x > WING_C + s_of(p) + 1e-6]
        if side(p) == 0 and part == "west":
            xs = [x for x in G if x < WING_C] + [WING_C]
        if side(p) == 0 and part == "east":
            xs = [WING_C] + [x for x in G if x > WING_C]
        return [V(x, y, z) for x in xs]

    def wing_cols(p):
        y, z = p
        return [V(y - 0.4, R + s_of(p), z), V(y - 0.4, 6.4, z), V(y - 0.4, T_NORTH, z)]

    def strip(A, B, key):
        if len(A) == len(B):
            return [bm.faces.new((A[i], A[i + 1], B[i + 1], B[i])) for i in range(len(A) - 1)]
        return _stitch(bm, A, B, key)

    kinds, wing_faces = {}, set()
    kind_of = {0: "roof", 1: "timber", 2: "plaster"}
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        k = kind_of[mi[i]]
        sa, sb = side(a), side(b)
        new = []
        if sa * sb < 0:                                    # the flat ridge top: straddles the ridge
            south, north = (a, b) if sa < 0 else (b, a)
            A = main_cols(south, "full")
            Bn = main_cols(north, "west") + main_cols(north, "east")
            F = strip(A, Bn, 0) if sa < 0 else strip(Bn, A, 0)
            new += F
        elif sa <= 0 and sb <= 0 and not (sa == 0 and sb == 0):   # south half (apex included)
            new += strip(main_cols(a, "full"), main_cols(b, "full"), 0)
        else:                                              # north half: two parts, each stops at a valley
            new += strip(main_cols(a, "west"), main_cols(b, "west"), 0)
            new += strip(main_cols(a, "east"), main_cols(b, "east"), 0)
        wf = strip(wing_cols(b), wing_cols(a), 1)          # wing: same loop edge, swept along +y
        wing_faces.update(wf)
        for f in new + wf:
            kinds[f] = k
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    top = max(bm.faces, key=lambda f: f.calc_center_median().z)
    if top.normal.z < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])

    # same hand-made irregularity as the run, on the stations a run would carry
    # (a run's x=2; here x=-2 / 6 on the main roof and y=6.4 on the wing), and
    # the same sag per 4 m module; open ends and valleys stay exact
    def along(v):
        return ("wing", v.co.y - 4.4) if v.co.y > 5.3 else ("main", v.co.x)
    for v in bm.verts:
        role, t = along(v)
        station = abs((t % 4.0) - 2.0) < 1e-4 and not (role == "main" and abs(v.co.x - WING_C) < 0.35)
        if v.co.z <= 0.2 or not station:
            continue
        yp = v.co.y if role == "main" else v.co.x + 0.4
        ym = min(yp, W - yp)
        rnd = random.Random(hash((round(t % 4.0, 3), round(v.co.z, 3), round(ym, 3), seed)))
        sgn = 0.0 if abs(yp - R) < 1e-4 else (1.0 if yp < R else -1.0)
        d = (rnd.random() * 2 - 1) * 0.012 * sgn
        if role == "main":
            v.co.y += d
        else:
            v.co.x += d
        v.co.z += (rnd.random() * 2 - 1) * 0.014
    for v in bm.verts:
        if v.co.z > 0.5:
            role, t = along(v)
            v.co.z -= 0.025 * math.sin(math.pi * (t % 4.0) / 4.0)
    bm.normal_update()

    # materials + UVs: the run's own mappings, turned 90 deg on the wing
    ob.data.materials.clear()
    for m in run_ob.data.materials:
        ob.data.materials.append(m)
    slot = {"roof": 0, "timber": 1, "plaster": 2}
    uvl = bm.loops.layers.uv.get("Float2") or bm.loops.layers.uv.new("Float2")
    TI = (300 / 256, 300 / 512)
    for f in bm.faces:
        k = kinds.get(f, "timber")
        f.material_index = slot[k]
        wing = f in wing_faces
        if k == "roof":
            for l in f.loops:
                c = l.vert.co
                l[uvl].uv = (((c.y - T_NORTH) if wing else c.x) * 0.5,
                             roof_slope_uv(c.x + 0.4 if wing else c.y, c.z, W=W))
        elif k == "plaster":
            set_window_uv(f, uvl, (1.5, 1.0), (0.12, 0.88, 0.43, 0.90))
        else:
            _beam_uv(f, uvl, 1 if wing else 0, TI, 0.25)
    write_piece(ob, bm)
    bm.free()
    return check_piece(ob, snap_planes=[(0, T_WEST), (0, T_EAST), (1, T_NORTH)], flat_tri_ok=True)


def _beam_uv(face, uvl, axis, per_metre, u_start):
    """set_beam_uv with the grain along any horizontal axis (0 = x, 1 = y)."""
    ku, kv = per_metre
    vs = [l.vert for l in face.loops]
    e_a, e_b = vs[1].co - vs[0].co, vs[-1].co - vs[0].co
    al, ac = (e_a, e_b) if abs(e_a[axis]) >= abs(e_b[axis]) else (e_b, e_a)
    dv, du = al.normalized(), ac.normalized()
    for l in face.loops:
        rel = l.vert.co.copy()
        l[uvl].uv = (u_start + rel.dot(du) * ku, rel.dot(dv) * kv)


# ---- L corner ---------------------------------------------------------------------
# Main roof comes in from the west (x = -4 .. the corner bay 0..4), the wing
# leaves to the north (to y = 8.4), and ONE diagonal mitre through the corner
# bay joins them: a hip on the outside corner, a valley on the inside. Here a
# profile point meets ITSELF on the mitre (no mirror needed): point (y_p, z)
# lands at x = 4.4 - y_p, y = y_p, which is exactly where a run turned 90 deg
# at the wing puts it -- so no ridge special case and no triangles. Any of the
# four corner directions is this piece rotated.
L_WEST, L_NORTH = -4.0, 8.4


def build_roof_l(ob, run_ob, seed=9, W=4.8):
    """Rebuild `ob` as the L corner from `run_ob`'s end loop and materials."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    loop, mi = boundary_loop(run_ob.data, 0, 0.0)
    y_off = origin_shift(run_ob.name)[1]
    pts = [(round(p.y + y_off, 5), round(p.z, 5)) for p in loop]
    n = len(pts)
    bm = bmesh.new()
    cache = {}

    def V(x, y, z):
        k = (round(x, 4), round(y, 4), round(z, 4))
        if k not in cache:
            cache[k] = bm.verts.new(k)
        return cache[k]
    xm = lambda p: 4.4 - p[0]                                   # the mitre / wing x of a profile point
    main_cols = lambda p: [V(L_WEST, p[0], p[1]), V(-2.0, p[0], p[1]), V(xm(p), p[0], p[1])]
    wing_cols = lambda p: [V(xm(p), p[0], p[1]), V(xm(p), 6.4, p[1]), V(xm(p), L_NORTH, p[1])]
    kinds, wing_faces = {}, set()
    kind_of = {0: "roof", 1: "timber", 2: "plaster"}
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        A, B = main_cols(a), main_cols(b)
        for j in range(2):
            kinds[bm.faces.new((A[j], A[j + 1], B[j + 1], B[j]))] = kind_of[mi[i]]
        A, B = wing_cols(a), wing_cols(b)
        for j in range(2):
            f = bm.faces.new((A[j], B[j], B[j + 1], A[j + 1]))
            kinds[f] = kind_of[mi[i]]
            wing_faces.add(f)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    top = max(bm.faces, key=lambda f: f.calc_center_median().z)
    if top.normal.z < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])

    # the run's irregularity on its stations (x=-2 main, y=6.4 wing) and its sag
    # per 4 m module; open ends and the mitre stay exact
    for v in bm.verts:
        wing = abs(v.co.y - 6.4) < 1e-4
        main = abs(v.co.x + 2.0) < 1e-4
        if v.co.z <= 0.2 or not (wing or main):
            continue
        yp = v.co.y if main else 4.4 - v.co.x
        ym = min(yp, W - yp)
        rnd = random.Random(hash((2.0, round(v.co.z, 3), round(ym, 3), seed)))
        sgn = 0.0 if abs(yp - W / 2) < 1e-4 else (1.0 if yp < W / 2 else -1.0)
        d = (rnd.random() * 2 - 1) * 0.012 * sgn
        if main:
            v.co.y += d
        else:
            v.co.x -= d                                        # wing profile runs along -x
        v.co.z += (rnd.random() * 2 - 1) * 0.014
    for v in bm.verts:
        if v.co.z > 0.5:
            if abs(v.co.x + 2.0) < 1e-4:
                v.co.z -= 0.025
            elif abs(v.co.y - 6.4) < 1e-4:
                v.co.z -= 0.025
    bm.normal_update()

    ob.data.materials.clear()
    for m in run_ob.data.materials:
        ob.data.materials.append(m)
    slot = {"roof": 0, "timber": 1, "plaster": 2}
    uvl = bm.loops.layers.uv.get("Float2") or bm.loops.layers.uv.new("Float2")
    TI = (300 / 256, 300 / 512)
    for f in bm.faces:
        k = kinds.get(f, "timber")
        f.material_index = slot[k]
        wing = f in wing_faces
        if k == "roof":
            for l in f.loops:
                c = l.vert.co
                l[uvl].uv = (((c.y - L_NORTH) if wing else c.x) * 0.5,
                             roof_slope_uv(4.4 - c.x if wing else c.y, c.z, W=W))
        elif k == "plaster":
            set_window_uv(f, uvl, (1.5, 1.0), (0.12, 0.88, 0.43, 0.90))
        else:
            _beam_uv(f, uvl, 1 if wing else 0, TI, 0.25)
    write_piece(ob, bm)
    bm.free()
    return check_piece(ob, snap_planes=[(0, L_WEST), (1, L_NORTH)], flat_tri_ok=True)
