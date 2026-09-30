# Floor tile: 4 m x 4 m timber floor for the ground floor (parterre) and every storey.
# Needs kit_lib.py exec'd first.
#
# Frame: x 0..4 along the planks, y 0..4 across, top of the planks at z = 0, joists
# hang down to z = -0.31. Place at (x0, y0, z): the tile occupies x0..x0+4, y0..y0+4
# and z-0.31..z. Open snap loops at x=0 and x=4 (identical), so tiles weld along x;
# the two y edges are closed (the walls cover them), i.e. one tile fills the 4 m
# house depth and a longer house is a row of tiles.
import bpy, bmesh, math
from mathutils import Vector

PLANK = 0.25          # board width
GROOVE = 0.02         # gap between boards (half of it at each tile edge)
RISE = 0.03           # planks stand this proud of the groove floor
DECK = 0.06           # plank layer thickness (top of planks to underside of the deck)
JOIST_DROP = 0.25     # joists hang this far below the deck
JOIST_W = 0.16        # joists: 4 of them, centred at x = 0.5, 1.5, 2.5, 3.5
# stairwell opening (KIT_FLOOR_STAIRWELL_*): between the first and last joist, from
# the edge of board 11 to the back wall; the joists crossing it end on a header
# beam along y = HEADER_Y..y0. stair.py's KIT_STAIR_A tops out at x = 3.42.
STAIRWELL = (0.58, 3.42, 2.99, 4.0)
HEADER_Y = 2.83


def build_floor_tile(ob, mats, zen_coll=None, seed=41, closed_x0=False, hole=None):
    """closed_x0=True makes the END tile: its x=0 side is closed with a rim (so a floor
    made of two END tiles, one rotated 180, is watertight); x=4 stays an open snap loop.
    hole=(x0, x1, y0, 4.0) cuts a stairwell opening against the y=4 wall (x0/x1 on
    joist faces, y0 on a board edge): its sides are closed down to the joists, the
    cut joists sit on a header beam, and the tile's y=4 rim is left out over it."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    if zen_coll is not None:
        for o in [o for o in bpy.data.objects if o.name == ob.name + "_ZEN"]:
            bpy.data.meshes.remove(o.data)
    bm = bmesh.new()
    # ---- top sheet: planks and grooves at the groove floor level ---------------
    ylines = [0.0]
    for i in range(16):
        ylines += [PLANK * i + GROOVE / 2, PLANK * i + PLANK - GROOVE / 2]
    ylines.append(4.0)
    ylines = sorted(set(round(y, 5) for y in ylines))
    rid_top = []
    for j in range(len(ylines) - 1):
        ym = (ylines[j] + ylines[j + 1]) / 2
        i = int(ym // PLANK)
        inplank = GROOVE / 2 < (ym - PLANK * i) < PLANK - GROOVE / 2
        rid_top.append(("plank", i) if inplank else ("groove",))
    if hole:
        # only the boards from the one ending at hy0 up are cut at hx0/hx1; the groove
        # under that board takes the step from 2 to 4 columns (a flat 2 cm strip,
        # triangulated) so the rest of the floor keeps its full-length boards
        hx0, hx1, hy0, hy1 = hole
        yhi = round(hy0 - (PLANK - GROOVE), 5)                   # bottom edge of that board
        ylo = round(yhi - GROOVE, 5)
        jlo, jhi = ylines.index(ylo), ylines.index(yhi)
        faces_t, VT, _, _ = tensor_partition(bm, [0.0, 4.0], ylines[:jlo + 1], [rid_top[:jlo]], -(RISE),
                                             protect_z=ylines[:jlo + 1])
        in_hole_y = lambda ym: hy0 < ym < hy1
        yu = ylines[jhi:]
        rid_u = [[None if (i == 1 and in_hole_y((yu[j] + yu[j + 1]) / 2)) else r
                  for j, r in enumerate(rid_top[jhi:])] for i in range(3)]
        fu, VU, _, _ = tensor_partition(bm, [0.0, hx0, hx1, 4.0], yu, rid_u, -(RISE), protect_z=yu)
        faces_t += fu
        VT.update(VU)
        L0, L1 = (VT[(round(x, 5), ylo)] for x in (0.0, 4.0))
        H0, Ha, Hb, H1 = (VT[(round(x, 5), yhi)] for x in (0.0, hx0, hx1, 4.0))
        faces_t += [(bm.faces.new(q), ("groove",)) for q in ((L0, Ha, H0), (L0, L1, Hb, Ha), (L1, H1, Hb))]
    else:
        faces_t, VT, _, _ = tensor_partition(bm, [0.0, 4.0], ylines, [rid_top], -(RISE), protect_z=ylines)
    for v in VT.values():                                    # (x, const, y) -> (x, y, const)
        x, c, y = v.co
        v.co = (x, y, c)
    # ---- bottom deck: joists and gaps ------------------------------------------
    jc = [0.5, 1.5, 2.5, 3.5]
    xb = [0.0]
    for c in jc:
        xb += [c - JOIST_W / 2, c + JOIST_W / 2]
    xb.append(4.0)
    rid_b = []
    for i in range(len(xb) - 1):
        xm = (xb[i] + xb[i + 1]) / 2
        rid_b.append(("joist",) if any(abs(xm - c) < JOIST_W / 2 for c in jc) else ("deck", i))
    if hole:
        # rows: under the boards / header beam / opening; the opening rows repeat the
        # board lines so its side rims are plain quads (no fan to a long deck edge)
        yb = [0.0, HEADER_Y] + [y for y in ylines if y >= hy0]
        rid_bh = []
        for i, r in enumerate(rid_b):
            xm = (xb[i] + xb[i + 1]) / 2
            inside = hx0 < xm < hx1
            col = []
            for j in range(len(yb) - 1):
                ym = (yb[j] + yb[j + 1]) / 2
                if ym < HEADER_Y:
                    col.append(r)
                elif ym < hy0:
                    col.append(("joist",) if inside else r)
                else:
                    col.append(None if inside else r)
            rid_bh.append(col)
        faces_b, VB, _, _ = tensor_partition(bm, xb, yb, rid_bh, -DECK, protect_x=xb,
                                             protect_z=[y for y in yb if y >= hy0])
    else:
        faces_b, VB, _, _ = tensor_partition(bm, xb, [0.0, 4.0], [[r] for r in rid_b], -DECK, protect_x=xb)
    for v in VB.values():
        x, c, y = v.co
        v.co = (x, y, c)
    # ---- close the two y edges (top sheet -> deck), hidden behind the walls ---------
    spans = [(0.0, 4.0)] if not hole else [(0.0, hole[0]), (hole[1], 4.0)]
    for yv in (0.0, 4.0):
        for a, b in (spans if yv == 4.0 else [(0.0, 4.0)]):
            sel = lambda D: sorted([v for v in D.values() if abs(v.co.y - yv) < 1e-5
                                    and a - 1e-5 <= v.co.x <= b + 1e-5], key=lambda v: v.co.x)
            _stitch(bm, sel(VT), sel(VB), 0)
    if hole:                                                  # opening rims: boards -> deck
        on = lambda v, ax, val, lo, hi: abs(v.co[ax] - val) < 1e-5 and lo - 1e-5 <= v.co[1 - ax] <= hi + 1e-5
        for ax, val, lo, hi in ((1, hy0, hx0, hx1), (0, hx0, hy0, hy1), (0, hx1, hy0, hy1)):
            key = 1 - ax
            tch = sorted([v for v in VT.values() if on(v, ax, val, lo, hi)], key=lambda v: v.co[key])
            bch = sorted([v for v in VB.values() if on(v, ax, val, lo, hi)], key=lambda v: v.co[key])
            _stitch(bm, tch, bch, key)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    # ---- relief: planks up, joists down ------------------------------------------
    planks = [f for f, r in faces_t if r[0] == "plank"]
    ptag = {}
    caps_p, sides_p = extrude_faces(bm, planks, RISE, along=Vector((0, 0, 1)), with_sides=True)
    joists = [f for f, r in faces_b if r[0] == "joist"]
    caps_j, sides_j = extrude_faces(bm, joists, JOIST_DROP, along=Vector((0, 0, -1)), with_sides=True)
    capset_p = set(caps_p)
    plank_of = {f: int(f.calc_center_median().y // PLANK) for f in caps_p}
    # hand-made irregularity (identical at x=0 and x=4 so tiles weld)
    bm.verts.ensure_lookup_table()
    pv = {v for f in caps_p for v in f.verts}
    # mirror-symmetric about y=2 (and periodic in x): the SAME tile welds to itself
    # after a 180 degree turn, which is how the two END tiles meet
    import random
    for v in pv:
        ym = min(v.co.y, 4.0 - v.co.y)
        rnd = random.Random(hash((round(v.co.x % 4.0, 3), round(ym, 3), seed)))
        sgn = 0.0 if abs(v.co.y - 2.0) < 1e-4 else (1.0 if v.co.y < 2.0 else -1.0)
        v.co.y += (rnd.random() * 2 - 1) * 0.002 * sgn
        v.co.z += (rnd.random() * 2 - 1) * 0.003
    if closed_x0:                                            # rim: close x=0 (hidden behind the wall)
        t0 = sorted([v for v in VT.values() if abs(v.co.x) < 1e-5], key=lambda v: v.co.y)
        b0 = sorted([v for v in VB.values() if abs(v.co.x) < 1e-5], key=lambda v: v.co.y)
        _stitch(bm, t0, b0, 1)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    kill = [f for f in bm.faces if all(abs(v.co.x - 4) < 1e-4 for v in f.verts)
            or (not closed_x0 and all(abs(v.co.x) < 1e-4 for v in f.verts))]
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    bm.normal_update()
    # ---- materials + UVs -------------------------------------------------------------
    ob.data.materials.clear()
    ob.data.materials.append(mats["floor"])
    ob.data.materials.append(mats["timber"])
    uvl = bm.loops.layers.uv.get("Float2") or bm.loops.layers.uv.new("Float2")
    joist_faces = set(caps_j) | set(sides_j) | set(joists)
    header = {f for f in joist_faces if f.is_valid and hole
              and HEADER_Y - 1e-4 <= f.calc_center_median().y <= hole[2] + 1e-4
              and hole[0] + 1e-4 < f.calc_center_median().x < hole[1] - 1e-4}
    TI = (300 / 256, 300 / 512)
    for f in bm.faces:
        c = f.calc_center_median()
        is_joist = f in joist_faces or (c.z < -DECK - 0.01)
        if is_joist and f in header:                          # header beam: grain along x
            f.material_index = 1
            for loop in f.loops:
                p = loop.vert.co
                across = p.y if abs(f.normal.z) > 0.5 else p.z
                loop[uvl].uv = (0.3 + across * TI[0], p.x * TI[1])
            continue
        if is_joist:
            f.material_index = 1
            for loop in f.loops:
                p = loop.vert.co
                if abs(f.normal.x) > 0.5:
                    loop[uvl].uv = (0.3 + p.z * TI[0], p.y * TI[1])
                else:
                    loop[uvl].uv = (0.3 + (p.x % 1.0) * TI[0] * 0.3, p.y * TI[1])
            continue
        f.material_index = 0
        i = plank_of.get(f)
        if i is not None:                                      # plank top: one texture plank per board
            row = i % 4
            y0 = PLANK * i + GROOVE / 2
            for loop in f.loops:
                p = loop.vert.co
                loop[uvl].uv = (p.x * 0.5, row * 0.25 + 0.01 + (p.y - y0))
        else:
            set_wrap_uv(f, uvl, (0.5, 0.5), (0.0, 0.0))
    write_piece(ob, bm)
    bm.free()
    res = check_piece(ob, snap_planes=[(0, 4.0)] if closed_x0 else [(0, 0.0), (0, 4.0)], flat_tri_ok=True)
    if zen_coll is not None:
        make_export_copy(ob, zen_coll)
    return res


# ---- ground floor: the same tile on a stone base, origin at ground level ----------
FOOT = 0.46           # stone footing top = door threshold (wall_bay.FOOT)
BASE_Z0 = 0.006       # the wall's inside face starts here (its open bottom rim)
BASE_CUTS = (0.0, 0.15, 3.85, 4.0)   # the inside-face columns every wall bay shares (end posts)


def add_ground_base(ob, stone_mat):
    """Turn a built floor tile (build_floor_tile) into its ground-floor variant:
    the tile itself is untouched, only lifted by FOOT so the planks sit on the
    threshold while the origin stays on the ground; a stone base skirt is added
    under every closed side (y=0, y=4, and x=0 on an END tile), from BASE_Z0 up
    to the joist bottoms. The skirt lies in the wall's inside plane with its
    vertices on the wall's own inside-face bottom row (x = BASE_CUTS,
    z = BASE_Z0), so a joined house merges them by distance. It is its own
    island (touching, not stitched, like the chimney on the roof): stitching it
    to the deck edge would give that edge three faces."""
    me = ob.data
    closed_x0 = any(p.center.x < 1e-4 and abs(p.normal.x) > 0.9 for p in me.polygons)
    bm = bmesh.new()
    bm.from_mesh(me)
    for v in bm.verts:
        v.co.z += FOOT
    top = FOOT - DECK - JOIST_DROP                                  # joist bottoms
    col = {}

    def vert(x, y, z):
        k = (round(x, 4), round(y, 4), round(z, 4))
        if k not in col:
            col[k] = bm.verts.new(k)
        return col[k]
    sides = [(lambda s: (s, 0.0), (0, 1)), (lambda s: (s, 4.0), (0, -1))]
    if closed_x0:
        sides.append((lambda s: (0.0, s), (1, 0)))
    if len(me.materials) < 3 or me.materials[2] != stone_mat:
        me.materials.append(stone_mat)
    uvl = bm.loops.layers.uv.get("Float2") or bm.loops.layers.uv.new("Float2")
    new = []
    for at, inward in sides:
        for a, b in zip(BASE_CUTS, BASE_CUTS[1:]):
            q = [vert(*at(a), BASE_Z0), vert(*at(b), BASE_Z0), vert(*at(b), top), vert(*at(a), top)]
            f = bm.faces.new(q)
            f.normal_update()
            if f.normal.to_2d().dot(Vector(inward)) < 0:
                f.normal_flip()
            f.material_index = 2
            for loop in f.loops:
                p = loop.vert.co
                loop[uvl].uv = ((p.x + p.y) * 0.5, p.z * 0.5)
            new.append(f)
    write_piece(ob, bm)
    bm.free()
    return len(new)


# ---- simple floors (2026-09-30): closed low-poly slabs replacing the plank tiles ------
SLAB = 0.20           # upper floor slab thickness (top of the floor at z = 0)


def build_floor_slab(ob, top_mat, side_mat, z_top=0.0, z_bot=-SLAB, hole=None, uv_size=2.0):
    """A closed box 4 x 4 m: top z_top, bottom z_bot, no open or non-manifold edges.
    hole=(x0, x1, y0, 4.0) cuts a stairwell notch against the y=4 side (see STAIRWELL);
    the top is then 3 quads around it, otherwise 1. Material slot 0 = top and bottom
    (planks), slot 1 = the sides. UVs: planks along x on top/bottom, wrap on the sides."""
    bm = bmesh.new()
    if hole:
        x0, x1, y0, _ = hole
        outline = [(0, 0), (4, 0), (4, 4), (x1, 4), (x1, y0), (x0, y0), (x0, 4), (0, 4)]
        quads = [(0, 1, 4, 5), (0, 5, 6, 7), (1, 2, 3, 4)]          # front strip, left, right
    else:
        outline = [(0, 0), (4, 0), (4, 4), (0, 4)]
        quads = [(0, 1, 2, 3)]
    top = [bm.verts.new((x, y, z_top)) for x, y in outline]
    bot = [bm.verts.new((x, y, z_bot)) for x, y in outline]
    faces = []
    for q in quads:
        faces.append((bm.faces.new([top[i] for i in q]), 0))
        faces.append((bm.faces.new([bot[i] for i in reversed(q)]), 0))
    n = len(outline)
    for i in range(n):
        j = (i + 1) % n
        faces.append((bm.faces.new((bot[i], bot[j], top[j], top[i])), 1))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ob.data.materials.clear()
    ob.data.materials.append(top_mat)
    ob.data.materials.append(side_mat)
    uvl = bm.loops.layers.uv.get("Float2") or bm.loops.layers.uv.new("Float2")
    for f, mi in faces:
        f.material_index = mi
        if mi == 0:
            for l in f.loops:
                l[uvl].uv = (l.vert.co.x / uv_size, l.vert.co.y)       # 4 boards per metre, like the old tile
        else:
            set_wrap_uv(f, uvl, (0.5, 0.5))
    for uv in [l for l in ob.data.uv_layers if l.name != "Float2"]:
        ob.data.uv_layers.remove(uv)
    write_piece(ob, bm)
    bm.free()
    return check_piece(ob, snap_planes=[])
