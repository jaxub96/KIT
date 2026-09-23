# Parametric 4 m timber-frame wall bay builder (ground floor and upper floor).
#
#   exec(open(KIT_LIB).read()); exec(open(WALL_BAY).read())
#   build_wall_bay(ob, dict(openings=[dict(kind="window", x0=.5, x1=1.5, z0=1.0, z1=2.2)]),
#                  MATS, zen_collection)
#   build_wall_bay(ob, dict(storey="upper", openings=[...]), MATS, zen)
#
# Needs kit_lib.py already exec'd. Rules encoded here (see SKILL.md):
#  * lean flat surfaces: planar_partition -> vertices only at region corners and
#    on the snap-plane rows every bay of the storey must share (so any two bays
#    weld with Merge by Distance)
#  * ONE extrusion for every raised region, relief by vertex depth, inset chamfer
#  * grooves (4 cm) only where stone meets timber; wood-to-wood is welded
#  * a plank-shaped sill/threshold gets the plank's material on every face
#  * end posts are half width (0.15) so two bays butt into one post
import bpy, bmesh, math

FOOT = 0.46          # stone footing top (ground floor); groove to 0.50
EAVE0 = 2.70         # eave beam z0
SOLE = 0.15          # upper floor sole plate height
DEPTHS = {"stone": 0.12, "timber": 0.09, "eave": 0.16, "sill": 0.20,
          "shutter": 0.05, "ornament": 0.035}
# Rows every bay of a storey carries on its two snap planes (identical end loops).
# LIP: the eave cornice (ground/upper top) and the sole plate (upper bottom)
# are different 3D shapes, so only their flat back corner used to coincide
# across a storey stack. Both stop LIP short of the true z=0/3 row, leaving
# a thin flat, unrelieved strip AT the row itself -- identical top and
# bottom, so the whole seam welds, not just its two corners.
LIP = 0.02
ZS_END = {"ground": [0.0, 0.46, 0.50, 0.65, 1.50, 1.62, 2.70, 3.00 - LIP, 3.00],
          "upper": [0.0, LIP, 0.15, 1.50, 1.62, 2.70, 3.00 - LIP, 3.00]}
# Openings are designed on those rows, so no row exists just for an opening:
#   window (both storeys): opening 1.62-2.70 (sill = the mid rail, which the
#     window's own sill member re-textures locally; lintel = the eave beam) --
#     this sits in the UPPER portion of either storey's 3 m height, not down
#     by the footing/sole plate, so the wall reads as "solid base, window
#     above" the way a real timber-frame front does.
#   door         : opening .46-2.7 (stone footing top up to the eave beam)
WIN_Z = {"ground": (1.62, 2.70), "upper": (1.62, 2.70)}
SILL0 = 1.50   # existing shared row directly below a window's z0 -- the
               # sill member spans SILL0->z0 (both already END rows for
               # every storey, see ZS_END below), not the whole area under
               # the window down to the post base, so it reads as a ledge
               # riding the mid rail, not a floor-to-window timber panel.
DOOR_Z = (0.46, 2.70)


def choose_bounds(lines, lo, hi, lmin, lmax):
    """Pick mirror bounds from existing grid lines so spans are between lmin
    and lmax where possible. If none falls in [lmin, lmax] the next line
    beyond lmax is used (a slightly stretched span beats a compressed one)."""
    b, cur = [lo], lo
    cand = sorted(set(round(c, 3) for c in lines) | {hi})
    while cur < hi - 1e-6:
        inr = [c for c in cand if cur + lmin - 1e-6 <= c <= cur + lmax + 1e-6]
        if inr:
            n = inr[-1]
        else:
            beyond = [c for c in cand if c > cur + lmax + 1e-6]
            n = beyond[0] if beyond else hi
        if hi - n < lmin * 0.6 and n != hi:
            n = hi
        b.append(n)
        cur = n
    return b


def wall_members(spec):
    """(x0, x1, z0, z1, orient, kind) for every timber member; sills first so
    they win over the rail/sole plate they sit on. spec["sparse"]=True drops
    the mid rail (a lighter-framed bay for a plainer house/street front) --
    the row it sits on (1.50/1.62) is still in ZS_END, so the bay still
    welds to every other bay of its storey, it just reads as flat plaster
    there instead of a beam."""
    upper = spec.get("storey") == "upper"
    z_post = SOLE if upper else 0.50
    base = [(0.00, 0.15, z_post, EAVE0, "V", "timber"), (3.85, 4.00, z_post, EAVE0, "V", "timber"),
            (0.00, 4.00, EAVE0, 3.00 - LIP, "H", "eave"),
            (0.0, 4.0, LIP, SOLE, "H", "timber") if upper else (0.0, 4.0, 0.50, 0.65, "H", "timber")]
    if not spec.get("sparse", False):
        base.insert(2, (0.0, 4.0, 1.50, 1.62, "H", "timber"))          # mid rail, unless sparse
    first = []
    for o in spec.get("openings", []):
        x0, x1 = o["x0"], o["x1"]
        trim = o.get("trim", "timber")   # jamb material override, e.g. "ornament"
        if o["kind"] == "window":
            z0, z1 = WIN_Z["upper" if upper else "ground"]
            o["z0"], o["z1"] = z0, z1
            jw = 0.12
            first.append((x0 - jw, x1 + jw, SILL0, z0, "H", "sill"))
            base += [(x0 - jw, x0, z0, z1, "V", trim), (x1, x1 + jw, z0, z1, "V", trim)]
        else:
            o["z0"], o["z1"] = DOOR_Z
            jw = 0.15
            base += [(x0 - jw, x0, z_post, DOOR_Z[1], "V", "timber"), (x1, x1 + jw, z_post, DOOR_Z[1], "V", "timber")]
    for xc in spec.get("studs", []):
        base.append((xc - 0.08, xc + 0.08, 0.65 if not upper else SOLE, EAVE0, "V", "timber"))
    base += spec.get("extra_members", [])   # e.g. shutters/ornament trim -- (x0,x1,z0,z1,orient,kind)
    return first + base


def build_wall_bay(ob, spec, mats, zen_coll=None, seed=1):
    """Rebuild `ob`'s mesh from `spec`. mats = {"plaster","timber","stone"}
    material objects. Returns the check_piece() report."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    if zen_coll is not None:
        for o in [o for o in bpy.data.objects if o.name == ob.name + "_ZEN"]:
            bpy.data.meshes.remove(o.data)
    upper = spec.get("storey") == "upper"
    ops = spec.get("openings", [])
    members = wall_members(spec)
    members = wall_members(spec)                 # also fixes every opening's z0/z1
    rects = [(o["x0"], o["x1"], o["z0"], o["z1"]) for o in ops]
    ends = ZS_END["upper" if upper else "ground"]

    # ---- grid: only lines that carry geometry -------------------------------
    xl, zl = [0, 4, 0.15, 3.85], [0, 3, EAVE0] + ends
    if not upper:
        zl += [FOOT, 0.5]
    for (a, b, c, d, _, _) in members:
        xl += [a, b]
        zl += [c, d]
    for o in ops:
        xl += [o["x0"], o["x1"]]
        zl += [o["z0"], o["z1"]]
    xs, zs = lines_from(xl), lines_from(zl)
    PL_B = {0: choose_bounds(xs, 0, 4, 1.2, 2.0), 2: choose_bounds(zs, 0, 3, 0.9, 1.3)}
    seg = lambda v, b: max(k for k in range(len(b) - 1) if b[k] <= v + 1e-9)

    def member_at(x, z, m=0.0):
        for k, mem in enumerate(members):
            if mem[0] - m < x < mem[1] + m and mem[2] - m < z < mem[3] + m:
                return k, mem
        return None, None

    def tag(x, z):
        if EAVE0 < z < 3.00 - LIP - 1e-9:   # the flat LIP row (above this) is unrelieved
            return "eave"
        if not upper:
            if z < FOOT:
                return "stone"
            if z < 0.5:
                return None
        k, mem = member_at(x, z)
        if mem is None:
            return None
        return mem[5]                    # already the final kind name (timber/eave/sill/...)

    inside = lambda x, z: any(r[0] < x < r[1] and r[2] < z < r[3] for r in rects)
    nx, nz = len(xs) - 1, len(zs) - 1
    rid = [[None] * nz for _ in range(nx)]
    for i in range(nx):
        for k in range(nz):
            cx, cz = (xs[i] + xs[i + 1]) / 2, (zs[k] + zs[k + 1]) / 2
            if inside(cx, cz):
                continue
            col = sum(cx > lx for lx in (0.15, 3.85))   # never merge across the end-post columns
            t = tag(cx, cz)
            if t is None:
                rid[i][k] = ("plaster", seg(cx, PL_B[0]), seg(cz, PL_B[2]), col)
            elif t == "stone":
                rid[i][k] = ("stone", col)
            else:
                rid[i][k] = (t, member_at(cx, cz)[0], col)
    bm = bmesh.new()
    r = slab_planar(bm, xs, zs, rid, rects, (0.0, 0.15, 3.85, 4.0), zs, thickness=WALL_T, split_x=(0.15, 3.85))
    plaster = {f for f, q in r["front"] if q[0] == "plaster"}
    plaster |= set(r["back"]) | set(r["reveal"]) | set(r["side"])

    raised = [f for f, q in r["front"] if q[0] != "plaster"]
    caps, _ = extrude_faces(bm, raised, 0.09, with_sides=True)
    cap_tag = {f: tag(f.calc_center_median().x, f.calc_center_median().z) for f in caps}
    capset = set(caps)
    for v in {v for f in caps for v in f.verts}:
        v.co.y = -max(DEPTHS[cap_tag[f]] for f in v.link_faces if f in capset)
    inset(bm, caps, 0.028, depth=0.03)

    def region_of(face):
        if face in capset:
            return cap_tag[face]
        for e in face.edges:
            for g in e.link_faces:
                if g in capset:
                    return cap_tag[g]
        return None

    extra_kinds = tuple(spec.get("extra_kinds", ()))   # e.g. ("shutter", "ornament")
    kind = {}
    for f in bm.faces:
        if f in plaster:
            kind[f] = "plaster"
        else:
            special = region_of(f)
            kind[f] = special if special in ("stone",) + extra_kinds else "timber"

    def in_rect(c, rc, m=0.02):
        return rc[0] - m <= c.x <= rc[1] + m and rc[2] - m <= c.z <= rc[3] + m

    for f in r["reveal"]:                       # sill / threshold run through the wall
        if f.is_valid and f.normal.z > 0.9:
            c = f.calc_center_median()
            for o in ops:
                if in_rect(c, (o["x0"], o["x1"], o["z0"], o["z1"])):
                    kind[f] = "timber" if o["kind"] == "window" else "stone"

    # ---- hand-made irregularity -------------------------------------------
    snap = [(0, 0.0), (0, 4.0), (2, 0.0)]
    jk = snap + [(2, 3.0)]
    bm.verts.ensure_lookup_table()
    st_v, ti_v = [], []
    for v in [v for v in bm.verts if v.co.y < -0.005]:
        (st_v if "stone" in {kind[f] for f in v.link_faces} else ti_v).append(v)

    def at_end(v):
        return abs(v.co.x) < 1e-4 or abs(v.co.x - 4.0) < 1e-4
    # verts on the two snap planes use a piece-independent seed so every bay
    # ends in the SAME loop; interior verts use the piece seed for variety
    jitter(bm, [v for v in st_v if at_end(v)], (0.02, 0.03, 0.02), seed=2, keep_planes=jk, period_x=4.0)
    jitter(bm, [v for v in st_v if not at_end(v)], (0.02, 0.03, 0.02), seed=seed + 2, keep_planes=jk, period_x=4.0)
    jitter(bm, [v for v in ti_v if at_end(v)], (0.008, 0.012, 0.008), seed=4, keep_planes=jk, period_x=4.0)
    jitter(bm, [v for v in ti_v if not at_end(v)], (0.008, 0.012, 0.008), seed=seed + 4, keep_planes=jk, period_x=4.0)
    for v in ti_v:
        if 0.5 < v.co.z < EAVE0:
            v.co.y -= 0.012 * math.sin(math.pi * (v.co.z - 0.5) / 2.2)

    def on_edge(v, rc, e=1e-4):
        x0, x1, z0, z1 = rc
        return (x0 - e <= v.co.x <= x1 + e and z0 - e <= v.co.z <= z1 + e and
                (abs(v.co.x - x0) < e or abs(v.co.x - x1) < e or
                 abs(v.co.z - z0) < e or abs(v.co.z - z1) < e))

    openv = [v for v in bm.verts if v.co.y > -0.001 and any(on_edge(v, rc) for rc in rects)]
    jitter(bm, openv, (0.006, 0, 0.006), seed=seed + 8, keep_planes=jk, share_y=True)
    for v in ti_v:                              # the eave beam sags a little
        if v.co.z > 2.6:
            v.co.z -= 0.03 * math.sin(math.pi * v.co.x / 4.0)

    # protect_x (0.15/3.85, the end-post columns) keeps a vertex column alive
    # all the way up through the eave band and down through the sole band,
    # even where the region either side is uniform -- those columns are
    # needed lower down (the post itself) but are pure leftovers at z=0 and
    # z=3.00. Left exactly on those planes they sit at the SAME world
    # position as the identical leftover in the bay stacked above/below (the
    # same end-post line, same world x), so Merge by Distance welds them
    # into one vertex with 3-4 linked faces -- non-manifold. Nudge every
    # such INTERIOR vertex (not the true x=0/4 snap edge) off the plane, in
    # opposite directions top vs bottom, so it never lands within weld
    # distance of the piece above or below.
    # Tried making upper's own top match the roof run's matching soffit
    # strip exactly (by skipping this nudge there): it welds the two, but
    # at every bay-to-bay and corner column FOUR surfaces actually converge
    # on that one edge (wall bay 1's right cap, wall bay 2's left cap, roof
    # run 1's right cap, roof run 2's left cap) -- a manifold edge can only
    # ever border 2, so gaining the wall-to-roof weld there broke the
    # (required) bay-to-bay weld instead, trading opens for real overlaps.
    # Keep the unconditional nudge; the wall-to-roof joint stays a flush
    # touch, not a weld (see the roof_gable.py comment on the now-matching
    # LIP-width soffit strip -- it helps every OTHER seam, just not this
    # specific column).
    for v in bm.verts:
        if 1e-4 < v.co.x < 4.0 - 1e-4:
            if abs(v.co.z) < 1e-4:
                v.co.z += 0.006
            elif abs(v.co.z - 3.0) < 1e-4:
                v.co.z -= 0.006
    # The flat back-of-wall top/bottom corner (x=0 or 4, y=WALL_T) is a real
    # snap-edge point, but it is ALSO exactly where two bays meet sideways
    # AND where a storey stacks on the one below/above -- four pieces'
    # copies of this one corner land on the same world edge (the front
    # corner doesn't: its "raised" branch sits at a different y per storey,
    # eave vs sole timber, so only the flat back corner collides). Split
    # ground-top from upper-bottom the same way, in z only (y stays put so
    # the sideways bay-to-bay weld is untouched).
    for v in bm.verts:
        if (abs(v.co.x) < 1e-4 or abs(v.co.x - 4.0) < 1e-4) and abs(v.co.y - WALL_T) < 1e-3:
            if abs(v.co.z) < 1e-4:
                v.co.z += 0.006
            elif abs(v.co.z - 3.0) < 1e-4:
                v.co.z -= 0.006
    bm.normal_update()

    kill = [f for f in bm.faces if all(abs(v.co.x) < 1e-4 for v in f.verts)
            or all(abs(v.co.x - 4) < 1e-4 for v in f.verts)]
    for f in kill:
        kind.pop(f, None)
    bmesh.ops.delete(bm, geom=kill, context='FACES')

    # ---- materials + UVs (~300 px/m) ----------------------------------------
    ob.data.materials.clear()
    slot = {}
    for k in ("plaster", "timber", "stone") + extra_kinds:
        ob.data.materials.append(mats[k])
        slot[k] = len(ob.data.materials) - 1
    uvl = bm.loops.layers.uv.get("Float2") or bm.loops.layers.uv.new("Float2")
    PL_WIN, PL_SIZE = (0.12, 0.88, 0.43, 0.90), (1.5, 1.0)
    TI = (300 / 256, 300 / 512)
    extra_uv = spec.get("extra_uv", {})    # {kind: fn(face, uv_layer, member)}
    for f in bm.faces:
        k = kind[f]
        f.material_index = slot[k]
        c = f.calc_center_median()
        if k == "plaster":
            set_window_uv(f, uvl, PL_SIZE, PL_WIN, bounds=PL_B)
        elif k == "stone":
            set_wrap_uv(f, uvl, (0.566, 0.566), (0.0, 0.10))
        elif k in extra_uv:
            idx, mem = member_at(c.x, c.z, m=0.05)
            extra_uv[k](f, uvl, mem)
        else:
            idx, mem = member_at(c.x, c.z, m=0.05)
            if mem is None:
                idx, mem = 0, (0, 0, 0, 0, "H", "timber")
            u0 = 0.12 + 0.13 * (idx % 6)
            if mem[4] == "H":
                set_beam_uv(f, uvl, "H", TI, u0, mem[2])
            else:
                set_beam_uv(f, uvl, "V", TI, u0, mem[0])

    write_piece(ob, bm)
    bm.free()
    res = check_piece(ob, snap_planes=snap, flat_tri_ok=True)
    if zen_coll is not None:
        make_export_copy(ob, zen_coll)
    return res
