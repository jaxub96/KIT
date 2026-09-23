# Maya family (KIT_MAYA_*): stone-and-plaster houses with flat roofs, in the
# style of HOUSE.001 (village_2.blend) -- rough plaster body, rubble plinth,
# ashlar string course / window surrounds / arched door ring, parapet top.
#
#   exec(open(KIT_LIB).read()); exec(open(WELD_PIECES).read()); exec(open(MAYA_BAY).read())
#   build_maya_bay(ob, dict(storey="ground", openings=[MW(1.5, 2.5)]), maya_mats())
#
# Same weld contract as the Gothic set (see SKILL.md):
#  * every bay of a storey carries the SAME rows (MROWS) on its two open ends,
#    so any bay welds to any other; corners are mitre sweeps of that end loop
#  * the storey seam is open: the string course is split across it (ground top
#    2.85-3.0, upper / parapet bottom 0-0.10), both halves meet at BAND_D in
#    front, and every bay carries the MSEAM_COLS vertices on that front chain
#  * one extrusion for every raised region, relief by vertex depth, a chamfer
#    inset per material (stone vs ashlar crease), jitter from vertices only
#  * cracks are notches INSIDE one plaster cell (inset ring + recessed floor),
#    never knife lines across the wall -- 9 quads per crack, no tris, no fans
import bpy, bmesh, math, random

MT = 0.3                  # Maya wall thickness
PLINTH = 0.40             # rubble plinth top (ground storey)
BAND_LO = 2.85            # string course bottom (top of every storey)
BAND_UP = 0.10            # string course top on the storey / parapet above
BAND_D = 0.07             # string course projection = seam front depth
SW = 0.14                 # ashlar surround width (window jambs + head)
DSW = 0.15                # door jamb / voussoir ring width
WIN_Z = (1.00, 2.20)      # window opening
SILL = (0.88, 1.00)       # projecting sill
SILL_X = SW               # sill as wide as the surround (no extra full-height columns)
DOOR_SPRING, DOOR_R = 1.90, 0.60
DEPTHS = {"stone": 0.06, "band": BAND_D, "trim": 0.05, "vous": 0.06, "sill": 0.10, "key": 0.09}
KEY_W = 0.09              # keystone half width
KEY_TOP = 2.42            # keystone rises above the window head (2.34)
NICHE_D = 0.12            # blind niche recess
# rows every bay of a storey carries (window / door rows included, so no row
# exists only in one bay and every end loop is identical)
MROWS = {"ground": [0.0, PLINTH, SILL[0], WIN_Z[0], DOOR_SPRING, WIN_Z[1], WIN_Z[1] + SW, KEY_TOP, BAND_LO, 3.0],
         "upper": [0.0, BAND_UP, SILL[0], WIN_Z[0], DOOR_SPRING, WIN_Z[1], WIN_Z[1] + SW, KEY_TOP, BAND_LO, 3.0]}
N_ARCH = 7                # arch segments (voussoirs); odd, so the crown one is the keystone

MW = lambda a, b, key=False: dict(kind="window", x0=a, x1=b, key=key)
MD = lambda a, b: dict(kind="door", x0=a, x1=b)
MN = lambda a, b: dict(kind="niche", x0=a, x1=b)    # blind window: surround + sill, recessed relief panel


def _arch_cols(x0, x1):
    xc, r = (x0 + x1) / 2, (x1 - x0) / 2
    th = [math.pi * (1 - k / N_ARCH) for k in range(N_ARCH + 1)]
    return xc, r, th, [round(xc + r * math.cos(t), 3) for t in th]   # on the 1 mm grid lines_from uses


def _opening_cols(o):
    x0, x1 = o["x0"], o["x1"]
    if o["kind"] in ("window", "niche"):
        xc = (x0 + x1) / 2
        key = [round(xc - KEY_W, 3), round(xc + KEY_W, 3)] if o.get("key", o["kind"] == "niche") else []
        return [x0 - SILL_X, x0 - SW, x0, x1, x1 + SW, x1 + SILL_X] + key
    return [x0 - DSW, x1 + DSW] + _arch_cols(x0, x1)[3]


# the standard openings of the set; every bay carries all their columns on the
# open storey-seam chain (inserted at the end, like wall_bay.SEAM_COLS)
STD_OPENINGS = [[MW(1.5, 2.5, True)], [MW(0.6, 1.4), MW(2.6, 3.4)], [MD(1.4, 2.6)]]
SPOUT_X = (1.85, 2.15)    # parapet rain spout columns (they run down the parapet to its seam)
MSEAM_COLS = sorted({round(c, 4) for ops in STD_OPENINGS for o in ops for c in _opening_cols(o)} | set(SPOUT_X) | {0.25, 3.75})   # + parapet frieze ends


def maya_mats(plaster="NW_Seq_Maya_Wall_09", trim="NW_Seq_Maya_Wall_11", stone="NW_Seq_Maya_NatureStone_01_XL",
              deck="NW_Misc_Maya_Ground_01"):
    return {"plaster": ensure_material(plaster), "trim": ensure_material(trim),
            "stone": ensure_material(stone), "deck": ensure_material(deck),
            "relief": ensure_material("NW_Seq_Maya_Ornament_Red_02"), "frieze": ensure_material("NW_Seq_Maya_Ornament_Red_05"),
            "planks": ensure_material("NW_City_InsideFloor_11"), "ceiling": ensure_material("NW_City_Roof_Inside_01"),
            "beam": ensure_material("NW_Ship_Hull_01"), "step": ensure_material(trim)}


# texel density ~256 px/m on the 512 textures, repeats divide the 4 m bay
UVK = {"plaster": (0.5, 0.5), "trim": (0.5, 0.5), "stone": (0.25, 0.25), "deck": (0.5, 0.5),
       "planks": (0.5, 0.5), "ceiling": (0.5, 1.0), "beam": (1.0, 2.0), "step": (0.5, 0.5)}


def _uv(f, uvl, kind):
    set_wrap_uv(f, uvl, UVK[kind], (0.0, 0.0))


def maya_members(spec):
    upper = spec.get("storey") == "upper"
    out = []                       # (x0, x1, z0, z1, kind); earlier entries win
    for o in spec.get("openings", []):
        x0, x1 = o["x0"], o["x1"]
        if o["kind"] in ("window", "niche"):
            xc = (x0 + x1) / 2
            if o.get("key", o["kind"] == "niche"):
                out.append((round(xc - KEY_W, 3), round(xc + KEY_W, 3), WIN_Z[1], KEY_TOP, "key"))
            out += [(x0 - SILL_X, x1 + SILL_X, SILL[0], SILL[1], "sill"),
                    (x0 - SW, x0, WIN_Z[0], WIN_Z[1] + SW, "trim"), (x1, x1 + SW, WIN_Z[0], WIN_Z[1] + SW, "trim"),
                    (x0, x1, WIN_Z[1], WIN_Z[1] + SW, "trim")]
        else:
            z_j = BAND_UP if upper else PLINTH              # the jambs stand ON the plinth
            out += [(x0 - DSW, x0, z_j, DOOR_SPRING, "trim"), (x1, x1 + DSW, z_j, DOOR_SPRING, "trim"),
                    (x0 - DSW, x0, DOOR_SPRING, WIN_Z[1], "vous"), (x1, x1 + DSW, DOOR_SPRING, WIN_Z[1], "vous")]
            xc, r, th, cols = _arch_cols(x0, x1)
            for k in range(N_ARCH):
                out.append((cols[k], cols[k + 1], DOOR_SPRING, WIN_Z[1], "key" if k == N_ARCH // 2 else "vous%d" % k))
    out.append((0.0, 4.0, BAND_LO, 3.0, "band"))
    out.append((0.0, 4.0, 0.0, BAND_UP, "band") if upper else (0.0, 4.0, 0.0, PLINTH, "stone"))
    return out


def build_maya_bay(ob, spec, mats, seed=1):
    """Rebuild ob's mesh as a 4 m Maya bay (legacy frame: front y=0, back y=MT,
    x 0..4, z 0..3). spec: storey ground|upper, openings [MW/MD], cracks
    [(cx, cz, w, h, angle_deg)]. Returns check_piece()."""
    upper = spec.get("storey") == "upper"
    ops = spec.get("openings", [])
    mem = maya_members(spec)
    rects = []
    for o in [o for o in ops if o["kind"] != "niche"]:
        rects.append((o["x0"], o["x1"], 0.0 if o["kind"] == "door" else WIN_Z[0],
                      DOOR_SPRING if o["kind"] == "door" else WIN_Z[1]))
    rows = MROWS["upper" if upper else "ground"]
    xl = [0.0, 4.0]
    for m in mem:
        xl += [m[0], m[1]]
    for o in ops:
        xl += _opening_cols(o)
    xs, zs = lines_from(xl), lines_from(rows)

    def member_at(x, z):
        for k, m in enumerate(mem):
            if m[0] < x < m[1] and m[2] < z < m[3]:
                return k, m
        return None, None
    inside = lambda x, z: any(r[0] < x < r[1] and r[2] < z < r[3] for r in rects)
    nx, nz = len(xs) - 1, len(zs) - 1
    rid = [[None] * nz for _ in range(nx)]
    for i in range(nx):
        for k in range(nz):
            cx, cz = (xs[i] + xs[i + 1]) / 2, (zs[k] + zs[k + 1]) / 2
            if inside(cx, cz):
                continue
            idx, m = member_at(cx, cz)
            niche = [o for o in ops if o["kind"] == "niche" and o["x0"] < cx < o["x1"] and WIN_Z[0] < cz < WIN_Z[1]]
            rid[i][k] = ("niche",) if niche else ("plaster",) if m is None else (m[4], idx)
    bm = bmesh.new()
    r = slab_planar(bm, xs, zs, rid, rects, (0.0, 4.0), zs, thickness=MT)
    fkind = {f: (q[0] if q[0] == "plaster" else q[0]) for f, q in r["front"]}
    plaster = {f for f, q in r["front"] if q[0] == "plaster"} | set(r["back"]) | set(r["reveal"]) | set(r["side"])
    niche_f = [f for f, q in r["front"] if q[0] == "niche"]

    # ---- the arch: pull the spring-row columns onto the intrados ------------
    for o in ops:
        if o["kind"] != "door":
            continue
        xc, rr, th, cols = _arch_cols(o["x0"], o["x1"])
        ro = rr + DSW
        for k in range(1, N_ARCH):
            for v in bm.verts:
                if abs(v.co.x - cols[k]) < 1e-4 and abs(v.co.z - DOOR_SPRING) < 1e-4:
                    v.co.z = DOOR_SPRING + rr * math.sin(th[k])
                elif abs(v.co.x - cols[k]) < 1e-4 and abs(v.co.z - WIN_Z[1]) < 1e-4 and v.co.y < MT - 1e-4:
                    v.co.x, v.co.z = xc + ro * math.cos(th[k]), DOOR_SPRING + ro * math.sin(th[k])
        # the back face keeps its own spring-row columns: follow the intrados too
    bm.normal_update()

    raised = [f for f, q in r["front"] if q[0] not in ("plaster", "niche")]
    caps, sides = extrude_faces(bm, raised, 0.05, with_sides=True)
    # blind niche: the same cells pushed INTO the wall (its sides share the
    # surround's extrusion edges, 2 faces each), relief panel on the back
    relief = []
    if niche_f:
        relief, nsides = extrude_faces(bm, niche_f, -NICHE_D, with_sides=True)
        plaster |= set(nsides)
    cz = {}
    for f in caps:
        c = f.calc_center_median()
        _, m = member_at(c.x, c.z)
        cz[f] = "vous" if m and m[4].startswith("vous") else (m[4] if m else "trim")
    for f in relief:
        cz.pop(f, None)
    capset = set(caps)
    for v in {v for f in caps for v in f.verts}:
        v.co.y = -max(DEPTHS[cz[f]] for f in v.link_faces if f in capset)
    for v in {v for f in relief for v in f.verts}:
        v.co.y = NICHE_D
    for grp in ([f for f in caps if cz[f] == "stone"], [f for f in caps if cz[f] != "stone"]):
        inset_open_ends(bm, grp, 0.022, 0.018, planes=[(0, 0.0), (0, 4.0)])

    def region_of(face):
        if face in capset:
            return cz[face]
        for e in face.edges:
            for g in e.link_faces:
                if g in capset:
                    return cz[g]
        return None
    kind = {}
    relset = set(relief)
    for f in bm.faces:
        if f in relset:
            kind[f] = "relief"
        elif f in plaster:
            kind[f] = "plaster"
        else:
            t = region_of(f)
            kind[f] = "stone" if t == "stone" else "trim"
    # a door's threshold would be a lone sheet on the ground plane sharing its two
    # side edges with the wall bottoms (3 faces each): the floor / ground closes it
    bm.normal_update()
    sill0 = [f for f in bm.faces if f.normal.z > 0.9 and all(abs(v.co.z) < 1e-4 for v in f.verts)]
    bmesh.ops.delete(bm, geom=sill0, context='FACES')

    # ---- cracks: a notch inside one plaster cell ----------------------------
    for (ccx, ccz, cw, ch, ang) in spec.get("cracks", []):
        cell = [f for f in bm.faces if kind.get(f) == "plaster" and f.normal.y < -0.9 and f.calc_center_median().y < 1e-4
                and min(v.co.x for v in f.verts) < ccx < max(v.co.x for v in f.verts)
                and min(v.co.z for v in f.verts) < ccz < max(v.co.z for v in f.verts)]
        if not cell:
            continue
        f = cell[0]
        ring = bmesh.ops.inset_individual(bm, faces=[f], thickness=0.0, depth=0.0)["faces"]
        # place the inner quad as a rotated, irregular diamond around (ccx, ccz)
        a = math.radians(ang)
        ca, sa = math.cos(a), math.sin(a)
        rnd = random.Random(hash((round(ccx, 3), round(ccz, 3), seed)))
        loc = [(-cw / 2, 0), (0, -ch / 2), (cw / 2, 0), (0, ch / 2)]
        vs = sorted(f.verts, key=lambda v: math.atan2(v.co.z - ccz, v.co.x - ccx))
        pts = sorted([(ccx + (px * ca - pz * sa) * (0.8 + 0.4 * rnd.random()),
                       ccz + (px * sa + pz * ca) * (0.8 + 0.4 * rnd.random())) for px, pz in loc],
                     key=lambda p: math.atan2(p[1] - ccz, p[0] - ccx))
        for v, (px, pz) in zip(vs, pts):
            v.co.x, v.co.z, v.co.y = px, pz, 0.0
        for g in ring:
            kind[g] = "plaster"
        rim = bmesh.ops.inset_individual(bm, faces=[f], thickness=0.02, depth=-0.04)["faces"]
        for g in rim:
            kind[g] = "plaster"
        kind[f] = "stone"
    bm.normal_update()

    # ---- irregularity: vertices only, ends and seams unmoved ---------------
    seam_zs = (0.0, 3.0) if upper else (3.0,)
    on_seam = lambda z: any(abs(z - s) < 1e-4 for s in seam_zs)
    seam_v = {v for v in bm.verts if v.co.y < -0.005 and on_seam(v.co.z)}
    for v in seam_v:
        v.co.y = -BAND_D
    bmesh.ops.dissolve_degenerate(bm, dist=1e-5, edges=bm.edges[:])
    keep = [(0, 0.0), (0, 4.0), (2, 0.0), (2, 3.0)]
    st = [v for v in bm.verts if v.co.y < -0.005 and v not in seam_v and "stone" in {kind.get(f) for f in v.link_faces}]
    tr = [v for v in bm.verts if v.co.y < -0.005 and v not in seam_v and v not in st]
    at_end = lambda v: abs(v.co.x) < 1e-4 or abs(v.co.x - 4.0) < 1e-4
    jitter(bm, [v for v in st if at_end(v)], (0.015, 0.02, 0.015), seed=2, keep_planes=keep, period_x=4.0)
    jitter(bm, [v for v in st if not at_end(v)], (0.015, 0.02, 0.015), seed=seed + 2, keep_planes=keep, period_x=4.0)
    jitter(bm, [v for v in tr if not at_end(v)], (0.004, 0.006, 0.004), seed=seed + 4, keep_planes=keep, period_x=4.0)
    bm.normal_update()

    # ---- open ends and open storey seams ------------------------------------
    kill = [f for f in bm.faces if all(abs(v.co.x) < 1e-4 for v in f.verts)
            or all(abs(v.co.x - 4) < 1e-4 for v in f.verts)
            or any(all(abs(v.co.z - s) < 1e-4 for v in f.verts) for s in seam_zs)]
    for f in kill:
        kind.pop(f, None)
    bmesh.ops.delete(bm, geom=kill, context='FACES')

    ob.data.materials.clear()
    slot = {}
    for k in ("plaster", "trim", "stone") + (("relief",) if relief else ()):
        ob.data.materials.append(mats[k])
        slot[k] = len(ob.data.materials) - 1
    uvl = bm.loops.layers.uv.get("Float2") or bm.loops.layers.uv.new("Float2")
    for f in bm.faces:
        k = kind.get(f, "trim")
        f.material_index = slot[k]
        if k == "relief":                              # the whole carving, once, on the niche back
            o = [o for o in ops if o["kind"] == "niche" and o["x0"] - 1e-3 <= f.calc_center_median().x <= o["x1"] + 1e-3][0]
            for l in f.loops:
                l[uvl].uv = ((l.vert.co.x - o["x0"]) / (o["x1"] - o["x0"]), 0.04 + 0.92 * (l.vert.co.z - WIN_Z[0]) / (WIN_Z[1] - WIN_Z[0]))
        else:
            _uv(f, uvl, k)

    # every bay carries every standard opening column on the front seam chain
    grown = set()
    for sz in seam_zs:
        on_chain = lambda v: abs(v.co.z - sz) < 1e-4 and abs(v.co.y + BAND_D) < 1e-3
        for c in sorted({0.0, 4.0} | set(MSEAM_COLS)):
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
    return check_piece(ob, snap_planes=[(0, 0.0), (0, 4.0)] + [(2, s) for s in seam_zs], flat_tri_ok=True)


def maya_corner(ob, bay_ob, mats, cap_top=False):
    """Mitre sweep of bay_ob's end loop (weld_pieces.build_corner_from_bay),
    then this family's materials / UVs on it (plaster, trim, stone)."""
    res = build_corner_from_bay(ob, bay_ob, {0: "plaster", 1: "timber", 2: "stone"},
                                {"plaster": mats["plaster"], "timber": mats["trim"], "stone": mats["stone"]},
                                T=MT, cap_top=cap_top)
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    uvl = bm.loops.layers.uv.get("Float2")
    kinds = {0: "plaster", 1: "trim", 2: "stone"}
    for f in bm.faces:
        _uv(f, uvl, kinds[f.material_index])
    write_piece(ob, bm)
    bm.free()
    return res


PARAPET_ROWS = [0.0, BAND_UP, 0.24, 0.30, 0.42, 0.84, 1.0]   # band | cornice | plaster | spout row | frieze | coping
PARAPET_D = {"band": BAND_D, "cornice": 0.15, "coping": 0.05}
FRIEZE_X = (0.25, 3.75)   # the carved frieze panel stops short of the open ends (end loops stay plain)
FRIEZE_D = 0.03
SPOUT_L = 0.70            # rain spout projection


def build_maya_parapet(ob, mats, spout=False, frieze=False, seed=5):
    """Parapet run on top of the top storey: string-course half (seam), cornice,
    plaster parapet wall, coping with a closed top. Bottom open (storey seam).
    Every variant has the same rows and end loop, so they all weld to each
    other and to the parapet corner. spout: a rain spout (stone channel grown
    out of the wall, trough inset into its top). frieze: a recessed carved panel."""
    zs = PARAPET_ROWS
    xs = lines_from([0.0, 4.0] + (list(SPOUT_X) if spout else []) + (list(FRIEZE_X) if frieze else []))
    row_kind = ["band", "cornice", "plaster", "plaster", "plaster", "coping"]
    rid = []
    for i in range(len(xs) - 1):
        cx = (xs[i] + xs[i + 1]) / 2
        col = []
        for k, rk in enumerate(row_kind):
            if spout and k == 3 and SPOUT_X[0] < cx < SPOUT_X[1]:
                col.append(("spout",))
            elif frieze and k == 4 and FRIEZE_X[0] < cx < FRIEZE_X[1]:
                col.append(("frieze",))
            else:
                col.append((rk,))
        rid.append(col)
    bm = bmesh.new()
    r = slab_planar(bm, xs, zs, rid, [], (0.0, 4.0), zs, thickness=MT)
    raised = [f for f, q in r["front"] if q[0] in ("band", "cornice", "coping")]
    caps, _ = extrude_faces(bm, raised, 0.05, with_sides=True)
    ck = {f: ("band" if f.calc_center_median().z < BAND_UP else "cornice" if f.calc_center_median().z < 0.5 else "coping")
          for f in caps}
    capset = set(caps)
    for v in {v for f in caps for v in f.verts}:
        v.co.y = -max(PARAPET_D[ck[f]] for f in v.link_faces if f in capset)
    for v in bm.verts:                               # the cornice leans out (cyma-ish slope)
        if abs(v.co.z - 0.24) < 1e-4 and v.co.y < -0.01:
            v.co.y = -0.17
    inset_open_ends(bm, caps, 0.02, 0.015, planes=[(0, 0.0), (0, 4.0)])
    for v in bm.verts:
        if v.co.y < -0.005 and abs(v.co.z) < 1e-4:
            v.co.y = -BAND_D
    bmesh.ops.dissolve_degenerate(bm, dist=1e-5, edges=bm.edges[:])
    kind = {}
    frz = [f for f, q in r["front"] if q[0] == "frieze" and f.is_valid]
    if frz:
        fcap, fsides = extrude_faces(bm, frz, -FRIEZE_D, with_sides=True)
        for f in fcap:
            kind[f] = "frieze"
        for f in fsides:
            kind[f] = "trim"
    spf = [f for f, q in r["front"] if q[0] == "spout" and f.is_valid]
    if spf:
        scap, ssides = extrude_faces(bm, spf, SPOUT_L, with_sides=True)
        for v in {v for f in scap for v in f.verts}:
            v.co.z -= 0.07                           # tips down, the water runs off
        top = [f for f in ssides if f.normal.z > 0.5]
        ring = inset(bm, top, 0.035, -0.045)         # the trough: quad ring + sunk floor
        for f in scap + ssides + ring:
            kind[f] = "trim"
    kill = [f for f in bm.faces if all(abs(v.co.x) < 1e-4 for v in f.verts)
            or all(abs(v.co.x - 4) < 1e-4 for v in f.verts) or all(abs(v.co.z) < 1e-4 for v in f.verts)]
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    bm.normal_update()
    ob.data.materials.clear()
    slots = ("plaster", "trim", "stone") + (("frieze",) if frz else ())
    for k in slots:
        ob.data.materials.append(mats[k])
    uvl = bm.loops.layers.uv.get("Float2") or bm.loops.layers.uv.new("Float2")
    for f in bm.faces:
        c = f.calc_center_median()
        k = kind.get(f)
        if k is None:
            k = "plaster" if (0.24 + 0.01 < c.z < 0.84 - 0.01 and c.y > -0.03) else "trim"
            if c.y > MT - 0.01 and f.normal.y > 0.9 and 0.02 < c.z < 0.84:
                k = "plaster"                           # roof side of the parapet
        f.material_index = slots.index(k)
        if k == "frieze":                              # carved band, 0.8 m per repeat, full height
            for l in f.loops:
                l[uvl].uv = (l.vert.co.x / 0.8, (l.vert.co.z - 0.42) / 0.42)
        else:
            _uv(f, uvl, k)
    grown = set()
    on_chain = lambda v: abs(v.co.z) < 1e-4 and abs(v.co.y + BAND_D) < 1e-3
    for c in MSEAM_COLS:
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
    return check_piece(ob, snap_planes=[(0, 0.0), (0, 4.0), (2, 0.0)], flat_tri_ok=True)


def _uv_axis(f, uvl, along, per_m, across_per_m):
    """planks / beams / boards: grain along world axis `along` (0=x, 1=y)."""
    n = f.normal
    for l in f.loops:
        c = l.vert.co
        if abs(n.z) > 0.5:
            a, b = c[along], c[1 - along]
        else:
            a, b = c[along] if abs(n[along]) < 0.5 else c[1 - along], c.z
        l[uvl].uv = (a * per_m, b * across_per_m)


def build_maya_floor(ob, mats, upper=False, ztop=2.98, top="planks"):
    """Room floor tile, 4 x 4 m, origin = inner room corner, OPEN on all four
    sides so neighbouring tiles weld along their edges and the edge against a
    wall is simply hidden. Ground: stone flags, top z=0.05. Upper: plank floor
    top at 2.98 (2 cm under the storey seam, so its edge never lands on the
    walls' open seam chain), boarded ceiling at 2.78 carried by four timber
    joists grown down out of it (open ends: joists run on into the next tile)."""
    bm = bmesh.new()
    if not upper:
        vs = [bm.verts.new((x, y, 0.05)) for x, y in ((0, 0), (4, 0), (4, 4), (0, 4))]
        f = bm.faces.new(vs)
        kinds = {f: "deck"}
    else:
        zbot, jd = ztop - 0.20, 0.18
        ys = [0.0]
        for yc in (0.5, 1.5, 2.5, 3.5):
            ys += [yc - 0.08, yc + 0.08]
        ys.append(4.0)
        topf = bm.faces.new([bm.verts.new(p) for p in ((0, 0, ztop), (4, 0, ztop), (4, 4, ztop), (0, 4, ztop))])
        kinds = {topf: top}
        bot = []
        V = {}
        for x in (0.0, 4.0):
            for y in ys:
                V[(x, y)] = bm.verts.new((x, y, zbot))
        for a_, b_ in zip(ys, ys[1:]):
            bot.append(bm.faces.new((V[(0.0, a_)], V[(0.0, b_)], V[(4.0, b_)], V[(4.0, a_)])))
        bm.normal_update()
        for f in bot:
            kinds[f] = "ceiling"
        joist = [f for f in bot if any(abs(f.calc_center_median().y - yc) < 0.01 for yc in (0.5, 1.5, 2.5, 3.5))]
        caps, sides = extrude_faces(bm, joist, jd, with_sides=True)
        for f in caps + sides:
            kinds[f] = "beam"
        endcaps = [f for f in bm.faces if all(abs(v.co.x) < 1e-4 for v in f.verts) or all(abs(v.co.x - 4) < 1e-4 for v in f.verts)]
        bmesh.ops.delete(bm, geom=endcaps, context='FACES_ONLY')
        bmesh.ops.delete(bm, geom=[e for e in bm.edges if not e.link_faces], context='EDGES')
    bm.normal_update()
    ob.data.materials.clear()
    slots = ("deck",) if not upper else (top, "ceiling", "beam")
    for k in slots:
        ob.data.materials.append(mats[k])
    uvl = bm.loops.layers.uv.get("Float2") or bm.loops.layers.uv.new("Float2")
    for f in bm.faces:
        if not f.is_valid:
            continue
        k = kinds.get(f, "beam")
        f.material_index = slots.index(k)
        if k == "deck":
            _uv(f, uvl, "deck")
        elif k == "planks":
            _uv_axis(f, uvl, 0, 0.5, 0.5)
        elif k == "ceiling":
            _uv_axis(f, uvl, 1, 0.5, 0.5)
        else:
            _uv_axis(f, uvl, 0, 0.5, 2.0)
    write_piece(ob, bm)
    bm.free()
    return check_piece(ob, snap_planes=[(0, 0.0), (0, 4.0), (1, 0.0), (1, 4.0)], flat_tri_ok=True)


def build_maya_step(ob, mats):
    """Stone step in front of a door bay: a closed block, placed with the door
    bay's own matrix (legacy frame: in front of the wall, x 1.15..2.85)."""
    bm = bmesh.new()
    ret = bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x = 1.15 if v.co.x < 0 else 2.85
        v.co.y = -0.42 if v.co.y < 0 else 0.0
        v.co.z = 0.0 if v.co.z < 0 else 0.16
    # a worn tread: its front top edge a little lower than the back
    for v in bm.verts:
        if v.co.z > 0.1 and v.co.y < -0.1:
            v.co.z -= 0.015
    bm.normal_update()
    back = [f for f in bm.faces if f.normal.y > 0.9]
    bottom = [f for f in bm.faces if f.normal.z < -0.9]
    bmesh.ops.delete(bm, geom=back + bottom, context='FACES_ONLY')     # against the wall / on the ground
    bmesh.ops.delete(bm, geom=[e for e in bm.edges if not e.link_faces], context='EDGES')
    ob.data.materials.clear()
    ob.data.materials.append(mats["step"])
    uvl = bm.loops.layers.uv.get("Float2") or bm.loops.layers.uv.new("Float2")
    for f in bm.faces:
        _uv(f, uvl, "step")
    write_piece(ob, bm)
    bm.free()
    return check_piece(ob, snap_planes=[(1, 0.0), (2, 0.0)], flat_tri_ok=True)


def build_maya_deck(ob, mats):
    """Flat roof = a floor tile of the top storey: flagstone top at 3.12 (inside
    the parapet, clear of its seam at 3.0), beamed ceiling below. Place it with
    the top storey's matrix, like the walls."""
    return build_maya_floor(ob, mats, upper=True, ztop=3.12, top="deck")


# The set: name -> (builder spec, seed)
MAYA_BAYS = {
    "KIT_MAYA_WALL_PLAIN_A": (dict(storey="ground"), 3),
    "KIT_MAYA_WALL_WINDOW_A": (dict(storey="ground", openings=[MW(1.5, 2.5, True)]), 1),
    "KIT_MAYA_WALL_WINDOW_TWIN_A": (dict(storey="ground", openings=[MW(0.6, 1.4), MW(2.6, 3.4)]), 4),
    "KIT_MAYA_WALL_DOOR_A": (dict(storey="ground", openings=[MD(1.4, 2.6)]), 1),
    "KIT_MAYA_WALL_PLAIN_CRACKED_A": (dict(storey="ground", cracks=[(0.9, 1.9, 0.42, 0.2, 25), (2.9, 0.65, 0.36, 0.18, -35)]), 8),
    "KIT_MAYA_WALL_WINDOW_CRACKED_A": (dict(storey="ground", openings=[MW(1.5, 2.5)], cracks=[(3.3, 2.55, 0.38, 0.2, 30)]), 9),
    "KIT_MAYA_WALL_UPPER_PLAIN_A": (dict(storey="upper"), 7),
    "KIT_MAYA_WALL_UPPER_WINDOW_A": (dict(storey="upper", openings=[MW(1.5, 2.5, True)]), 2),
    "KIT_MAYA_WALL_UPPER_WINDOW_TWIN_A": (dict(storey="upper", openings=[MW(0.6, 1.4), MW(2.6, 3.4)]), 5),
    "KIT_MAYA_WALL_UPPER_CRACKED_A": (dict(storey="upper", openings=[MW(1.5, 2.5)], cracks=[(0.7, 2.5, 0.4, 0.18, -20)]), 6),
    "KIT_MAYA_WALL_NICHE_A": (dict(storey="ground", openings=[MN(1.5, 2.5)]), 11),
    "KIT_MAYA_WALL_UPPER_NICHE_A": (dict(storey="upper", openings=[MN(1.5, 2.5)]), 12),
}
MAYA_PARAPETS = {"KIT_MAYA_PARAPET_A": {}, "KIT_MAYA_PARAPET_SPOUT_A": dict(spout=True),
                 "KIT_MAYA_PARAPET_FRIEZE_A": dict(frieze=True)}
MAYA_CORNERS = {"KIT_MAYA_WALL_CORNER_A": ("KIT_MAYA_WALL_PLAIN_A", False),
                "KIT_MAYA_WALL_CORNER_UPPER_A": ("KIT_MAYA_WALL_UPPER_PLAIN_A", False),
                "KIT_MAYA_PARAPET_CORNER_A": ("KIT_MAYA_PARAPET_A", True)}
